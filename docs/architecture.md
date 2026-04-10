# Architecture Overview

> InfraAgent is a multi-agent pipeline that converts natural-language infrastructure requests into audited, PR-ready IaC (Bicep or Terraform). It runs on Azure AI Foundry Agent Service with the Microsoft Agent Framework.

## System Diagram

```mermaid
graph TB
    User([User]) -->|natural language| ChatUI[Chat UI]
    ChatUI -->|POST /api/chat| API[FastAPI Backend]

    subgraph Pipeline["OrchestratorPipeline (pipeline.py)"]
        direction TB
        Consulting[Consulting Agent] -->|RequirementsHandoff| CodeGen[CodeGen Agent]

        subgraph Loop1["Review Loop (max 3×)"]
            CodeGen -->|GeneratedFile[]| Standards[Standards Agent]
            CodeGen -->|GeneratedFile[]| Security[Security Agent]
            Standards -->|ValidationFinding[]| Check{Errors?}
            Security -->|ValidationFinding[]| Check
            Check -->|Yes + feedback| CodeGen
        end

        Check -->|No errors| H1[Human Gate H1: Code Review]
        H1 -->|Approved| PR[PR Workflow]
        PR -->|branch + commit + PR| GitHub[(GitHub)]

        PR --> Plan[Plan / What-If]
        Plan --> H2[Human Gate H2: Plan Review]
        H2 -->|Approved| Deploy[Deploy Agent]
    end

    API --> Pipeline
```

## Pipeline Stages

Each pipeline run tracks its progress through `PipelineState.stage`:

| Stage | Description |
|---|---|
| `consulting` | Gathering requirements via conversational chat |
| `codegen` | Generating Bicep/Terraform from `RequirementsHandoff` |
| `standards` | Checking naming, tagging, and structural policies |
| `security` | Scanning for vulnerabilities (public exposure, encryption, secrets) |
| `human_review_code` | **H1** — human approves generated code before PR |
| `pr_created` | Branch + commit + PR created on GitHub |
| `plan` | `bicep what-if` or `terraform plan` execution |
| `human_review_plan` | **H2** — human approves plan before deployment |
| `deploying` | `bicep deploy` or `terraform apply` in progress |
| `deployed` | Successfully deployed |
| `failed` | Pipeline error (see `PipelineState.error`) |

## Clean Architecture (Ports & Adapters)

```mermaid
block-beta
  columns 1
  block:api["API Layer\nroutes.py · dependencies.py"]
  end
  block:services["Application / Services\npipeline.py (OrchestratorPipeline)"]
  end
  block:domain["Domain Core\nmodels.py (PipelineState, RequirementsHandoff…)\nports.py (ICodeGenPort, ISourceControlPort…)"]
  end
  block:adapters["Adapters\nagents/codegen.py → ICodeGenPort\nagents/reviewers.py → IStandardsPort, ISecurityPort\nadapters/github_adapter.py → ISourceControlPort"]
  end
  api --> services
  services --> domain
  domain --> adapters
```

**Key principle**: Domain models and port interfaces have zero external dependencies. Adapters can be swapped (e.g., replace `GitHubAdapter` with `AzureDevOpsAdapter`) without touching the pipeline or domain.

### Port Interfaces

| Port | Adapter | Purpose |
|---|---|---|
| `ICodeGenPort` | `CodeGenAgent` | Generates IaC from requirements |
| `IStandardsPort` | `StandardsAgent` | Checks naming/tagging/structure policies |
| `ISecurityPort` | `SecurityAgent` | Static security analysis |
| `ISourceControlPort` | `GitHubAdapter` | Branch, commit, PR management |
| `IDeployPort` | *(not yet implemented)* | Plan/apply operations |
| `IValidationPort` | *(not yet implemented)* | Deterministic IaC validation (fmt/build/lint) |
| `ISubscriptionDiscoveryPort` | *(not yet implemented)* | Azure subscription resource discovery |

## Agent Architecture

All agents are **Foundry-hosted agents** created via `factory.py`:

1. Each agent has a markdown **system prompt** in `backend/src/agents/prompts/`
2. `create_agent()` loads the prompt and calls `client.agents.create_agent()`
3. Agents communicate via structured JSON blocks extracted from their responses
4. Agents are stateless per-run; conversation history is thread-scoped in Foundry

### Agent Roster

| Agent | Input | Output | Role |
|---|---|---|---|
| **Consulting** | User message (natural language) | `RequirementsHandoff` JSON | Gathers requirements, asks clarifying questions |
| **CodeGen** | `RequirementsHandoff` + optional feedback | `CodeGenOutput` JSON (files + diagram) | Generates Bicep/Terraform using AVM-first strategy |
| **Standards** | `GeneratedFile[]` | `ValidationFinding[]` | Checks naming, tagging, modularity |
| **Security** | `GeneratedFile[]` | `ValidationFinding[]` | Checks public exposure, encryption, secrets |

## ModelRouter

Agents declare task intent, not specific model names. Azure AI Foundry **ModelRouter** automatically selects the optimal model from the project's model catalog based on task complexity and cost profile.

Configuration is at the Foundry project level — code references `MODEL_DEPLOYMENT_NAME` from environment config, which can point to a ModelRouter endpoint.

## Maker-Checker Loops

**Loop 1 (Code Quality)**: CodeGen → Standards + Security → check for errors → retry with feedback (max 3 iterations). Only `Severity.ERROR` findings trigger a retry; warnings and info are passed through.

**Loop 2 (Plan Verification)** *(future)*: Plan → analyze errors → CodeGen rework → re-validate → re-plan (max 2 iterations).

## Human Gates

| Gate | When | MVP Behavior |
|---|---|---|
| **H1** | After review loop passes, before PR creation | Auto-approved (logged) |
| **H2** | After plan succeeds, before deployment | Auto-approved (logged) |

In production, these would pause the pipeline and wait for explicit approval via the API or UI.

## Technology Stack

| Layer | Technology |
|---|---|
| **AI Platform** | Azure AI Foundry Agent Service |
| **Agent Framework** | Microsoft Agent Framework (`agent-framework` Python package) |
| **Backend** | Python 3.11+ · FastAPI · uvicorn |
| **Dependencies** | uv (pyproject.toml) |
| **IaC** | Bicep (primary) · Terraform (secondary) |
| **Source Control** | GitHub REST API v3 |
| **Authentication** | Azure Identity (`DefaultAzureCredential`) |
| **MCP Servers** | Bicep MCP · Terraform MCP · Azure MCP |

## Key Domain Models

See `backend/src/core/models.py` for full definitions:

- **`InfraRequest`** — Initial user request (message + IaC language preference)
- **`RequirementsHandoff`** — Structured handoff from Consulting → CodeGen (project name, resources, constraints, region)
- **`CodeGenOutput`** — Generated files + Mermaid diagram + explanation
- **`ValidationFinding`** — Individual finding with severity, resource, file, message, remediation
- **`PipelineState`** — Full pipeline run state (stage, iteration counts, outputs, PR URL, error)
