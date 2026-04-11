# Architecture Overview

> InfraAgent is a multi-agent pipeline that converts natural-language infrastructure requests into audited, PR-ready IaC (Bicep or Terraform). It runs on Azure AI Foundry Agent Service with the Microsoft Agent Framework.

## System Diagram

```mermaid
graph TB
    User([User]) -->|natural language| ChatUI[Chat UI]
    User -->|browse templates| CatalogUI[Self-Service Catalog]

    ChatUI -->|POST /api/chat| API[FastAPI Backend]
    CatalogUI -->|GET /api/catalog| API
    CatalogUI -->|POST /api/catalog/:name/deploy| API

    subgraph ChatPipeline["Chat Path — OrchestratorPipeline"]
        direction TB
        Consulting[Consulting Agent] -->|subscription discovery| Discovery[Azure Subscription Discovery]
        Discovery -->|RequirementsHandoff| CodeGen[CodeGen Agent]

        subgraph Loop1["Review Loop (max 3×)"]
            CodeGen -->|GeneratedFile[]| IaCValid[IaC Validation Pipeline\nfmt → validate → lint]
            IaCValid -->|pass| Standards[Standards Agent]
            IaCValid -->|fail + errors| CodeGen
            Standards -->|ValidationFinding[]| Security[Security Agent]
            Security -->|ValidationFinding[]| Check{Errors?}
            Check -->|Yes + feedback| CodeGen
        end

        Check -->|No errors| Diagram[Diagram Generation\nMermaid from IaC]
        Diagram --> H1[Human Gate H1:\nCode + Diagram Review]
        H1 -->|Approved| PR[PR Workflow Agent]
        PR -->|branch + commit + PR| GitHub[(GitHub)]

        PR --> Plan[Plan / What-If\nDeploy Agent]

        subgraph Loop2["Plan-Failure Rework (max 2×)"]
            Plan -->|plan failed + fixable| CodeGen
        end

        Plan -->|plan succeeded| H2[Human Gate H2:\nPlan Review]
        H2 -->|Approved| Deploy[Deploy Agent\napply / deploy]
    end

    subgraph CatalogPipeline["Catalog Path — Template Fast-Path"]
        direction TB
        Hydrate[Template Hydrate\n+ Org Standards] --> CatValid[IaC Validation Pipeline]
        CatValid --> CatH1[Human Gate H1]
        CatH1 --> CatPR[PR Workflow Agent]
        CatPR --> CatPlan[Plan / What-If]
        CatPlan --> CatH2[Human Gate H2]
        CatH2 --> CatDeploy[Deploy Agent]
    end

    API --> ChatPipeline
    API --> CatalogPipeline

    Deploy -->|post-deploy| Curation[Template Curation Agent]
    Curation -->|PR to wiki repo| WikiRepo[(Knowledge Wiki Repo)]
    Curation --> H3[Human Gate H3:\nTemplate Approval]
```

## Two Pipeline Paths

InfraAgent supports two user journeys:

**Chat Path (Journey A):** The user does not know exactly what to build. The Consulting Agent guides them through architecture design, discovers existing Azure resources, and routes to the full agent pipeline (CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy).

**Catalog Path (Journey B):** The user knows what they want. They browse pre-validated templates, fill in parameters, and deploy through a simplified pipeline (Hydrate → IaC Validation → H1 → PR → Plan → H2 → Deploy). Standards and Security checks are skipped because templates are pre-validated.

## Pipeline Stages

Each pipeline run tracks its progress through `PipelineState.stage`:

| Stage | Description |
|---|---|
| `consulting` | Gathering requirements via conversational chat |
| `discovering_subscription` | Connecting to Azure subscription to inventory resource groups, VNets, naming patterns, quotas |
| `codegen` | Generating Bicep/Terraform from `RequirementsHandoff` (AVM-first strategy) |
| `validating_iac` | Deterministic CLI validation — Terraform: `fmt` → `init` → `validate` → `tflint`; Bicep: `build` → `format` → `lint` |
| `standards` | Checking naming, tagging, structure, AVM compliance, dependency correctness |
| `security` | Scanning for vulnerabilities (public exposure, encryption, secrets, NSG rules) |
| `human_review_code` | **H1** — human approves generated code + architecture diagram before PR |
| `pr_created` | Branch + commit + PR created on GitHub |
| `plan` | `bicep what-if` or `terraform plan` execution |
| `reworking_plan_failure` | Plan failed — error categorized, CodeGen reworking code (Loop 2, max 2×) |
| `human_review_plan` | **H2** — human approves plan before deployment |
| `deploying` | `bicep deploy` or `terraform apply` in progress |
| `deployed` | Successfully deployed |
| `failed` | Pipeline error (see `PipelineState.error`) |
| `cancelled` | Pipeline cancelled by user |

## Clean Architecture (Ports & Adapters)

```mermaid
block-beta
  columns 1
  block:presentation["Presentation Layer\nReact/Next.js Frontend · Chat UI · Catalog UI · File Explorer · Diagram Viewer"]
  end
  block:api["API Gateway Layer\nFastAPI · routes.py · dependencies.py · WebSocket handlers"]
  end
  block:services["Application / Services Layer\npipeline.py (OrchestratorPipeline) · Use Cases (Consult, Generate, Deploy)"]
  end
  block:domain["Domain Core\nmodels.py (PipelineState, RequirementsHandoff, DeploymentRequest…)\nports.py (ICodeGenPort, ISourceControlPort, ISubscriptionDiscoveryPort…)\npolicies/ (NamingPolicy, TaggingPolicy, SecurityPolicy)"]
  end
  block:adapters["Infrastructure / Adapters\nagents/ (codegen.py, reviewers.py, consulting.py, pr_workflow.py, deploy.py)\nadapters/ (github_adapter.py, terraform_adapter.py, bicep_adapter.py, subscription_discovery_adapter.py)\nmcp/ (config.py, tool_adapter.py)"]
  end
  presentation --> api
  api --> services
  services --> domain
  domain --> adapters
```

**Key principle**: Domain models and port interfaces have zero external dependencies. Adapters can be swapped (e.g., replace `GitHubAdapter` with `AzureDevOpsAdapter`, or `AzureOpenAIAdapter` with `AnthropicAdapter`) without touching the pipeline or domain.

### Port Interfaces

| Port | Adapter | Purpose |
|---|---|---|
| `ILLMCompletionPort` | `AzureOpenAIAdapter` (with ModelRouter) | LLM inference with task profile–based model selection |
| `ICodeGenPort` | `CodeGenAgent` | Generates IaC from requirements (AVM-first, secret-safe) |
| `IStandardsPort` | `StandardsAgent` | Checks naming/tagging/structure/AVM compliance policies |
| `ISecurityPort` | `SecurityAgent` | Static security analysis (tfsec, Checkov) |
| `ISourceControlPort` | `GitHubAdapter` | Branch, commit, PR management |
| `IDeployPort` | `BicepDeployAdapter` / `TerraformDeployAdapter` | `what-if`/`plan` and `deploy`/`apply` operations |
| `IValidationPort` | `IaCValidationAdapter` | Deterministic IaC validation (`fmt`/`validate`/`lint`) |
| `ISubscriptionDiscoveryPort` | `AzureSubscriptionDiscoveryAdapter` | Azure subscription resource, VNet, quota, and naming-pattern discovery |
| `IPolicyEnginePort` | `PolicyAdapter` | Policy evaluation (naming, tags, security rules) |
| `ITemplateRegistryPort` | `TemplateRegistryAdapter` | Knowledge wiki template search, retrieval, hydration, publishing |
| `IObservabilityPort` | `OpenTelemetryAdapter` | Tracing, metrics, logging via OpenTelemetry → App Insights |

## Agent Architecture

All agents are **Foundry-hosted agents** created via `factory.py`:

1. Each agent has a markdown **system prompt** in `backend/src/agents/prompts/`
2. `create_agent()` loads the prompt and calls `client.agents.create_agent()` with a ModelRouter task profile
3. Agents communicate via structured JSON blocks extracted from their responses
4. Agents are stateless per-run; conversation history is thread-scoped in Foundry

### Agent Roster

| Agent | ModelRouter Profile | MCP Servers | Input | Output | Role |
|---|---|---|---|---|---|
| **Orchestrator** | `orchestration` | None (agent handoff) | Pipeline context | Routing decisions | Manages agent lifecycle, enforces pipeline sequence |
| **Consulting** | `complex-reasoning` | Azure MCP | User message | `RequirementsHandoff` JSON | Gathers requirements, subscription discovery, project type classification |
| **CodeGen** | `code-generation` | Terraform MCP, Bicep MCP, Azure MCP | `RequirementsHandoff` + feedback | `CodeGenOutput` JSON (files + diagram) | Generates IaC using AVM-first strategy |
| **Standards** | `analysis` | GitHub MCP | `GeneratedFile[]` | `ValidationFinding[]` | Checks naming, tagging, modularity, AVM compliance |
| **Security** | `fast-lightweight` | None (function tools) | `GeneratedFile[]` | `ValidationFinding[]` | Checks public exposure, encryption, secrets |
| **PR Workflow** | `fast-lightweight` | GitHub MCP | Files + metadata | PR URL, branch, SHA | Creates branches, commits, PRs with structured descriptions |
| **Deploy** | `complex-reasoning` | GitHub MCP, Azure MCP | PR reference | Plan/apply output | Runs plan/apply, error interpretation, rollback |
| **Template Curation** | `complex-reasoning` | GitHub MCP | Deployed code | Template PR | Generalizes deployed code into reusable templates |

### IaC Validation Pipeline (Non-Agent)

The IaC Validation Pipeline is **not an agent** — it is a deterministic function tool chain invoked by the Orchestrator between CodeGen and Standards. It catches compilation and structural errors before they consume LLM tokens or reach human review.

| Language | Steps | On Failure |
|---|---|---|
| Terraform | `fmt -check` → `init` → `validate` → `tflint` | Errors fed back to CodeGen (Loop 1) |
| Bicep | `build` → `format` → `lint` | Errors fed back to CodeGen (Loop 1) |

## ModelRouter

Agents declare task intent via profiles, not specific model names. Azure AI Foundry **ModelRouter** automatically selects the optimal model from the project's model catalog based on task complexity and cost profile.

| Profile | Primary Candidate | Fallback | Notes |
|---|---|---|---|
| `complex-reasoning` | GPT-4o | GPT-4.1 | Deep reasoning, multi-step analysis |
| `code-generation` | GPT-4o | Claude 3.5 Sonnet | Structured code output |
| `analysis` | GPT-4o-mini | GPT-4o | Policy checks |
| `fast-lightweight` | GPT-4o-mini | Phi-4 | Template-driven, low token |
| `orchestration` | GPT-4o | GPT-4o-mini | Routing decisions |

Configuration is at the Foundry project level — code references `MODEL_DEPLOYMENT_NAME` from environment config, which can point to a ModelRouter endpoint.

## Maker-Checker Loops

**Loop 1 (Code Quality)**: CodeGen → IaC Validation Pipeline → Standards + Security → check for errors → retry with feedback (max 3 iterations total across all checkers). Only `Severity.ERROR` findings trigger a retry; warnings and info are passed through.

Each checker produces structured errors: `{ checker, severity, resource, file, line, message, remediation }`. CodeGen receives the full list and addresses errors in priority order (validation errors first, then standards, then security).

**Loop 2 (Plan-Failure Rework)**: Plan → on failure, categorize the error → if fixable in code, feed back to CodeGen → re-enter Loop 1 → new PR → re-plan (max 2 iterations). Non-fixable errors (quota exceeded, auth failure) are escalated to the user at H2.

Plan failure categories:

| Category | Example | Fixable? |
|---|---|---|
| `resource_conflict` | "Resource group already exists" | Yes — use `data` source or adjust naming |
| `sku_unavailable` | "VM size not available in westeurope" | Yes — query Azure MCP for alternatives |
| `quota_exceeded` | "Exceeded vCPU quota" | No — requires manual quota increase |
| `auth_failure` | "Authorization failed" | No — cannot be fixed in code |
| `provider_mismatch` | "Unsupported attribute" | Yes — update provider version pin |
| `module_error` | "Invalid value for variable" | Yes — fix variable value/type via MCP |

## Human Gates

| Gate | When | What is Reviewed | API Endpoint |
|---|---|---|---|
| **H1** | After review loop passes | Generated IaC code + architecture diagram | `POST /api/pipeline/approve/h1` |
| **H2** | After plan succeeds | `terraform plan` / `bicep what-if` output | `POST /api/pipeline/approve/h2` |
| **H3** (P1) | After template curation | New template proposed for knowledge wiki | `POST /api/pipeline/approve/h3` |

The pipeline pauses at each gate. The frontend surfaces an approval UI that calls the corresponding endpoint. Both gates accept an optional `comment` field.

## Knowledge Wiki Architecture

The knowledge wiki is a **separate GitHub repository** consumed by InfraAgent as a **git submodule** at `knowledge-wiki/`. This enables independent versioning, separate CI, and clean separation of platform code from knowledge content.

```
infraagent/
├── src/                          # InfraAgent platform code
├── knowledge-wiki/               # Git submodule → wiki repo
│   ├── templates/                # Pre-validated IaC templates
│   ├── skills/                   # Domain skill files for Consulting Agent
│   ├── standards/                # Org policy files (naming, tagging)
│   └── patterns/                 # Architecture decision records
├── .gitmodules
└── ...
```

The submodule is pinned to a specific commit (release tag for production, `main` for development). The wiki repo has its own CI pipeline that validates template syntax and metadata schema.

The Template Curation Agent proposes new templates via PRs to the **wiki repo** (not the InfraAgent repo). Once approved via H3, the InfraAgent submodule reference is updated.

## Technology Stack

| Layer | Technology |
|---|---|
| **AI Platform** | Azure AI Foundry Agent Service |
| **Model Selection** | Azure AI Foundry ModelRouter |
| **Agent Framework** | Microsoft Agent Framework (`agent-framework` Python package) |
| **Backend** | Python 3.11+ · FastAPI · uvicorn |
| **Frontend** | Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS · shadcn/ui |
| **IaC Grounding** | Terraform MCP Server + Bicep MCP Server (live registry schemas) |
| **Azure Operations** | Azure MCP Server (resource queries, subscription discovery) |
| **Source Control** | GitHub REST API v3 + GitHub MCP Server |
| **Knowledge Wiki** | Separate GitHub repo (git submodule) |
| **Database** | Azure PostgreSQL (conversations, deployments, settings) |
| **Vector Search** | Azure AI Search (Policy RAG, template search) |
| **Security Scanning** | tfsec, Checkov (via Azure Functions) |
| **IaC Validation** | Terraform CLI, Bicep CLI, tflint |
| **Observability** | Azure Monitor + App Insights + OpenTelemetry |
| **Authentication** | Azure Identity (`DefaultAzureCredential`) · Entra ID (future) |
| **Secrets** | Azure Key Vault |
| **MCP Servers** | Bicep MCP · Terraform MCP · Azure MCP · GitHub MCP |

## Key Domain Models

See `backend/src/core/models.py` for full definitions:

- **`InfraRequest`** — Initial user request (message + IaC language preference)
- **`RequirementsHandoff`** — Structured handoff from Consulting → CodeGen (project name, project type, resources, constraints, region, subscription context)
- **`CodeGenOutput`** — Generated files + Mermaid diagram + explanation
- **`ValidationFinding`** — Individual finding with severity, resource, file, message, remediation
- **`PlanFailureAnalysis`** — Categorized plan failure (category, error message, fixable flag, suggested fix)
- **`PipelineState`** — Full pipeline run state (stage, iteration counts, plan rework iterations, outputs, PR URL, diagram, subscription context, error)
- **`SubscriptionContext`** — Discovery results (resource groups, VNets, naming patterns, quotas, state backends)
- **`TemplateMetadata`** — Catalog template metadata (name, services, complexity, parameters, version)