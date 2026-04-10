# InfraAgent — Product Requirements Document

**Version:** 2.0  
**Date:** April 2026  
**Status:** Draft  
**Classification:** Internal — Microsoft Hackathon  
**Target Cloud:** Microsoft Azure  
**IaC Languages:** Terraform (HCL) & Bicep  
**AI Platform:** Azure AI Foundry Agent Service  
**Hackathon Timeline:** 3 weeks (build + demo)  

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | April 2026 | Added ModelRouter as default model selection strategy. Knowledge wiki defined as separate repo consumed via git submodule. Added Azure subscription discovery step. Added IaC validation pipeline (fmt/validate/lint). Added AVM-first module strategy. Defined generated code file structure conventions. Expanded plan-failure rework loop with data flow. Added secret handling patterns. Added set-diff analysis for plan review. Defined architecture diagram generation approach. |
| 1.0 | April 2026 | Initial draft. |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision](#3-product-vision)
4. [Users and Personas](#4-users-and-personas)
5. [User Journeys](#5-user-journeys)
6. [Agent Architecture](#6-agent-architecture)
7. [Feature Requirements](#7-feature-requirements)
8. [Knowledge Wiki and Domain Skills](#8-knowledge-wiki-and-domain-skills)
9. [MCP Server Integration](#9-mcp-server-integration)
10. [Clean Architecture](#10-clean-architecture)
11. [Technology Stack](#11-technology-stack)
12. [Hackathon MVP Scope](#12-hackathon-mvp-scope)
13. [Success Metrics](#13-success-metrics)
14. [Risks and Mitigations](#14-risks-and-mitigations)
15. [Competitive Differentiation](#15-competitive-differentiation)
16. [Out of Scope (Future Phases)](#16-out-of-scope-future-phases)
17. [Glossary](#17-glossary)

---

## 1. Executive Summary

InfraAgent is a multi-agent platform that converts natural language infrastructure requests into production-ready, standards-compliant Infrastructure as Code (Terraform HCL and Bicep). Built on Azure AI Foundry Agent Service, it orchestrates seven specialized agents through a maker-checker pipeline with human-in-the-loop approval gates, automated security scanning, GitHub PR workflows, and CI/CD-triggered deployment. All agents use the Azure AI Foundry **ModelRouter** for automatic model selection — agents declare task intent and complexity profiles rather than hardcoded model names, enabling cost-optimal routing across the model catalog.

InfraAgent takes inspiration from the proven TerraBot prototype (conversational Terraform generation with MCP-grounded code) into a full-featured multi-agent enterprise platform with four major additions:

- **A Consulting Agent** that runs architecture design sessions, recommending patterns from a curated knowledge wiki before any code is generated. The consulting agent also performs **Azure subscription discovery**, connecting to the target subscription to inventory existing resources, VNets, and naming patterns before code generation begins.
- **A Self-Service Catalog** where engineers browse and deploy pre-validated templates without touching the full agent pipeline.
- **A Knowledge Feedback Loop** where successfully deployed custom code is generalized into reusable templates by a Template Curation Agent, growing the catalog organically.
- **An IaC Validation Pipeline** that runs deterministic toolchain validation (fmt, init, validate, lint for Terraform; build, format, lint for Bicep) before any human review, catching compilation and structural errors before they reach the PR stage.

The platform follows clean architecture (hexagonal / ports-and-adapters) principles, ensuring business logic is fully decoupled from framework, LLM provider, and IaC tool concerns. This makes InfraAgent survivable across the inevitable framework transitions ahead.

**Hackathon Goal:** Demonstrate 3 user paths end-to-end: (1) an engineer asks for a 3-tier web app via the chat interface, the consulting agent gathers requirements, code is generated in Bicep or Terraform, a PR is created, and deployment succeeds via GitHub Actions; (2) an engineer selects a pre-validated template from the self-service catalog, fills in parameters, and deploys it through the same PR/deploy pipeline; (3) an engineer AKS cluster via the chat interface, the consulting agent gathers requirements, code is generated in Bicep or Terraform, a PR is created, plan fails, code is regenerated, PR is recreated, and deployment succeeds via GitHub Actions.

---

## 2. Problem Statement

Every cloud engagement hits the same bottleneck: IaC authoring requires deep cloud expertise, governance is not enforced by default, and Day 2 operations remain largely manual with limited visibility. Reference architectures and proven patterns exist across the organization but are not searchable or shared, so teams rebuild from scratch, producing code that is rarely reused, inconsistently structured, and siloed within individual engagements.

### 2.1 Key Challenges

| Challenge | Impact | How InfraAgent Solves It |
|-----------|--------|--------------------------|
| IaC authoring requires deep expertise | Senior engineers spend 40%+ time on IaC maintenance | Natural language to production-ready code via LLM + MCP grounding |
| Code and patterns are siloed per project | No reuse, no shared asset discoverability | Knowledge wiki + self-service catalog with growing template library |
| No enforced governance | Inconsistent naming, tagging, compliance failures | Standards agent enforces org policy on every generation |
| Misconfigurations caught late | Costly rework at plan/apply stage | Security agent runs tfsec/Checkov before human review |
| Terraform expertise concentrated in few engineers | Bottleneck for all infrastructure changes | Any engineer can self-serve via chat or catalog |
| No Bicep support in existing tooling | Microsoft-native teams lack AI-assisted IaC | Dual IaC support via Terraform MCP + Bicep MCP servers |

---

## 3. Product Vision

InfraAgent is a platform where any engineer, regardless of Terraform or Bicep expertise, can go from an infrastructure idea to a deployed, standards-compliant, security-scanned, PR-approved Azure environment in minutes rather than days. The platform learns from every successful deployment, building an ever-growing library of reusable patterns that accelerate future work.

### 3.1 Core Principles

- **Infrastructure as Code:** All infrastructure is defined, versioned, and deployed via Terraform or Bicep. No manual portal deployments.
- **Docs as Code:** Architecture diagrams are auto-generated from IaC source, never manually drawn. IaC is the single source of truth.
- **Human in the Lead:** No auto-deploy without explicit human approval. Engineers retain full control over what gets deployed.
- **MCP-Grounded Generation:** All code generation uses live registry documentation via MCP servers. Never relies on stale LLM training data.
- **Clean Architecture:** Business logic (policies, validations, standards) lives in deterministic code. LLMs propose; deterministic code validates.
- **Knowledge Flywheel:** Every successful custom deployment is a candidate for the template library. The platform gets smarter with use.

---

## 4. Users and Personas

| Persona | Role | Primary Use Case | InfraAgent Path |
|---------|------|------------------|-----------------|
| Application Engineer | Builds apps, needs infrastructure | Wants a database, a web app, or a full environment | Chat (consulting agent) or Catalog (self-service) |
| Cloud / Platform Engineer | Owns infrastructure, enforces standards | Automates IaC workflows, reviews and approves deployments | Approver at human gates H1, H2, H3 |
| Solutions Architect | Designs cloud architectures | Validates architecture patterns, approves templates for wiki | Uses consulting agent, curates knowledge wiki |
| Delivery / Team Lead | Oversees project delivery | Tracks deployment status, ensures compliance | Views deployment dashboard, reviews PR summaries |

### 4.1 Hackathon Scope: Role Model

For the hackathon MVP, a single user can perform all roles. The approval gates (H1: code review, H2: plan review, H3: template approval) are presented to the same user. Multi-user RBAC is a post-hackathon feature.

---

## 5. User Journeys

### 5.1 Journey A: Chat Path (Consulting Agent → Custom Pipeline)

The user does not know exactly what to build. They use the chat interface and the Consulting Agent guides them through an architecture design session.

1. User opens InfraAgent and selects the Chat interface.
2. Consulting Agent greets the user, asks about their infrastructure need, and runs a structured requirements-gathering session (probing questions, trade-off analysis, pattern recommendations).
3. **Subscription Discovery:** Consulting Agent connects to the target Azure subscription via Azure MCP Server and inventories existing resource groups, VNets, subnets, deployed resources, naming patterns, and available quotas. Findings are surfaced to the user ("I can see you already have a VNet `vnet-prod-westeurope` with subnets...") and passed as constraints to downstream agents.
4. Consulting Agent checks the Knowledge Wiki for matching templates. If a match is found, it recommends the template and the user can shortcut to the Catalog Path (Journey B, step 3).
5. If no template matches, the Consulting Agent produces a structured requirements handoff document (similar to a `.terraform-planning-files/INFRA.{goal}.md` planning file) and routes to the Custom Pipeline. The user selects Terraform or Bicep as their IaC language.
6. CodeGen Agent generates production-ready IaC code, grounded by the Terraform MCP Server or Bicep MCP Server. The agent prefers Azure Verified Modules (AVM) over raw resource declarations where available.
7. **IaC Validation Pipeline:** The generated code passes through a deterministic (non-LLM) validation toolchain before any agent or human review. For Terraform: `terraform fmt` → `terraform init` → `terraform validate`. For Bicep: `bicep build` → `bicep format` → `bicep lint`. Compilation or validation failures are fed back to CodeGen for rework.
8. Standards Agent validates naming conventions, tagging rules, and structural policies. Violations are fed back to CodeGen for rework (max 3 iterations across validation + standards + security combined).
9. Security Agent runs static analysis (tfsec/Checkov for Terraform, equivalent for Bicep). Findings are fed back to CodeGen for rework.
10. **Human Gate H1:** The user reviews the generated code and auto-generated architecture diagram.
11. PR Workflow Agent creates a GitHub branch and opens a Pull Request with structured diffs.
12. GitHub Actions runs `terraform plan` / `bicep what-if`. The plan output is surfaced to the user. For Terraform, the Set Diff Analyzer optionally filters false-positive diffs from Set-type attribute reordering so the human reviewer sees only real changes.
13. **Human Gate H2:** The user reviews the plan output and approves deployment.
14. Deploy Agent triggers `terraform apply` / `az deployment create`. Monitors progress and handles rollback on failure.
15. Template Curation Agent (post-deploy): Analyzes the deployed code, checks novelty against existing wiki templates, generalizes parameters, and proposes a new template via PR to the knowledge wiki repo.
16. **Human Gate H3:** A platform engineer reviews and approves the template PR. The new template is now available in the self-service catalog.

### 5.2 Journey B: Catalog Path (Self-Service Template Deployment)

The user knows what they want. They browse the self-service catalog and deploy a pre-validated template.

1. User opens InfraAgent and selects the Self-Service Catalog.
2. User searches by keyword (e.g., "AKS cluster", "3-tier web app") and browses matching templates with descriptions, complexity ratings, and Azure services used.
3. User selects a template and fills in deployment-specific parameters (e.g., VM size, node count, region). Organizational parameters (naming, subscription, environment, tags) are enforced automatically by the Standards Agent working with the CodeGen Agent.
4. **Subscription Discovery (lightweight):** The system connects to the target subscription via Azure MCP to verify the target resource group, check for naming conflicts, and validate that requested SKUs and regions are available. Conflicts are surfaced before proceeding.
5. The hydrated template passes through the IaC Validation Pipeline: `terraform fmt` + `terraform init` + `terraform validate` (Terraform) or `bicep build` + `bicep format` (Bicep). Standards and Security agents are skipped (templates are pre-validated).
6. **Human Gate H1:** The user reviews the parameterized code and architecture diagram.
7. Steps 11–14 from Journey A (PR → Plan → H2 → Deploy) are identical.

The catalog path is significantly faster because it bypasses the full agent pipeline (no consulting, no iterative codegen/standards/security loops). Templates have already been validated and approved via H3.

---

## 6. Agent Architecture

InfraAgent uses eight agents coordinated by an orchestrator. Each agent is a Foundry Hosted Agent with its own model configuration, system instructions, and MCP tool bindings. The orchestrator manages agent lifecycle, routes requests, shares context, and enforces the maker-checker pipeline.

### 6.1 Agent Inventory

All agents use the **Azure AI Foundry ModelRouter** for model selection. Rather than hardcoding specific models, each agent declares a task profile (complexity, latency sensitivity, token budget). ModelRouter routes requests to the optimal model in the Foundry model catalog based on cost, capability, and availability. This eliminates manual model assignment and enables automatic upgrades as new models are onboarded.

| Agent | ModelRouter Profile | Tools / MCP Servers | Role |
|-------|---------------------|---------------------|------|
| Orchestrator | `orchestration` — routing and coordination, moderate complexity | All agent references | Routes requests, manages lifecycle, shares context, enforces pipeline sequence |
| Consulting Agent | `complex-reasoning` — multi-turn architecture design, high complexity | Azure MCP, Knowledge Wiki RAG, Domain Skills | Runs architecture design sessions, performs subscription discovery, recommends patterns, routes to catalog or custom path |
| CodeGen Agent | `code-generation` — structured code output, high complexity | Terraform MCP, Bicep MCP, Azure MCP, Memory | Generates production-ready Terraform HCL or Bicep code from requirements |
| Standards Agent | `analysis` — policy validation, moderate complexity | Policy RAG (Azure AI Search), GitHub MCP | Validates naming, tagging, structural policies; feeds violations back to CodeGen |
| Security Agent | `fast-analysis` — structured scan result interpretation, low complexity | tfsec, Checkov (function tools) | Static security analysis; feeds findings back to CodeGen |
| PR Workflow Agent | `fast-lightweight` — template-driven operations, low complexity | GitHub MCP, Octokit | Creates branches, commits files, opens PRs with structured descriptions |
| Deploy Agent | `complex-reasoning` — error interpretation and rollback decisions | Terraform CLI / Azure CLI (function tools), Azure MCP | Runs plan/apply, monitors progress, interprets plan failures, handles rollback |
| Template Curation Agent | `complex-reasoning` — code analysis and generalization | Knowledge Wiki repo, GitHub MCP | Analyzes deployed code, generalizes to reusable template, proposes wiki PR |

#### 6.1.1 ModelRouter Configuration

ModelRouter is configured at the Foundry project level. Each profile maps to a set of candidate models with priority ordering. For the hackathon MVP, the following default mappings apply (ModelRouter may override based on availability and cost):

| Profile | Primary Candidate | Fallback Candidates | Notes |
|---------|-------------------|---------------------|-------|
| `complex-reasoning` | GPT-4o | GPT-4.1 | Used for agents requiring deep reasoning or multi-step analysis |
| `code-generation` | GPT-4o | Claude 3.5 Sonnet (via Foundry catalog) | Optimized for structured code output |
| `analysis` | GPT-4o-mini | GPT-4o | Sufficient for structured policy checks |
| `fast-lightweight` | GPT-4o-mini | Phi-4 | Template-driven, low token usage |
| `orchestration` | GPT-4o | GPT-4o-mini | Routing decisions, moderate complexity |

ModelRouter automatically handles retries across candidates if the primary model is unavailable or rate-limited.

### 6.2 Orchestration Pattern

InfraAgent uses a hybrid orchestration pattern combining sequential pipeline (CodeGen → IaC Validation → Standards → Security → PR → Deploy) with handoff routing (Consulting Agent routes to catalog path or custom path). The Microsoft Agent Framework provides the graph-based workflow API for explicit multi-agent coordination, checkpointing for durable long-running workflows, and request-response for human-in-the-loop gates.

#### 6.2.1 Maker-Checker Loops

- **Loop 1 (Code Quality):** CodeGen → **IaC Validation Pipeline** → Standards → Security. The validation pipeline is the first checker — it runs deterministic toolchain validation (fmt/validate/lint) before any LLM-based review. If any checker finds violations, structured feedback is sent to CodeGen for rework. Maximum **3 iterations total** across all checkers before escalation to human with the current best output plus remaining errors.

  Loop 1 feedback format: Each checker produces a structured error report containing `{ checker: string, severity: "error" | "warning", resource: string, file: string, line: number, message: string, remediation: string }`. CodeGen receives the full list and addresses errors in priority order (validation errors first, then standards, then security).

- **Loop 2 (Plan-Failure Rework):** Plan → Human Review → Apply. If `terraform plan` / `bicep what-if` fails, the **full plan error output** (stderr + exit code) is fed back to CodeGen along with the original requirements context and the current code. CodeGen analyzes the error (e.g., "SKU not available in region", "quota exceeded", "resource already exists"), makes targeted fixes, and the code re-enters the validation pipeline (Loop 1) before a new PR is created. Maximum **2 iterations** of Loop 2. If the plan still fails after 2 rework cycles, the error is escalated to the human with the plan output and CodeGen's analysis of what went wrong.

  Plan failure categories and handling:
  
  | Failure Category | Example | CodeGen Action |
  |-----------------|---------|----------------|
  | Resource conflict | "Resource group already exists" | Use existing resource via `data` source or adjust naming |
  | SKU/region unavailability | "VM size not available in westeurope" | Query Azure MCP for alternative SKUs/regions, propose to user |
  | Quota exceeded | "Exceeded vCPU quota" | Surface to user — requires manual quota increase |
  | Authentication/permission | "Authorization failed" | Surface to user — cannot be fixed in code |
  | Provider version mismatch | "Unsupported attribute" | Update provider version pin, re-validate |
  | Module input error | "Invalid value for variable" | Fix variable value or type based on module docs via MCP |

#### 6.2.2 Human Gates

| Gate | What is Reviewed | Who Approves | Blocking? |
|------|-----------------|--------------|-----------|
| H1 — Code + Diagram | Generated IaC code + architecture diagram | Requesting engineer | Yes — no PR without approval |
| H2 — Plan Review | terraform plan / bicep what-if output | Requesting engineer (or platform engineer) | Yes — no apply without approval |
| H3 — Template Approval | New template proposed for knowledge wiki | Platform engineer / solutions architect | Yes — no wiki addition without approval |

---

## 7. Feature Requirements

### 7.1 P0 — Must Have (Hackathon MVP)

These features must be working in the hackathon demo.

#### 7.1.1 Consulting Agent

- Structured multi-turn conversation for requirements gathering (context discovery, current landscape, constraints).
- **Project type classification:** Assesses the request as Demo/Learning, Production Application, Enterprise Solution, or Regulated Workload. Classification determines the depth of requirements gathering and the WAF (Well-Architected Framework) pillars applied to code generation (Demo: minimal; Production: cost, reliability, security, operational excellence; Enterprise: comprehensive).
- Pluggable domain skills loaded from the knowledge wiki repo (git submodule). Each skill is a markdown file with phase-specific questions, pattern catalogs, and readiness checklists.
- Recommends architecture patterns from the knowledge wiki. If a matching template exists, offers to shortcut to catalog path.
- **Azure Subscription Discovery:** Connects to the target Azure subscription via Azure MCP Server to:
  - List existing resource groups and their resources.
  - Map existing VNet/subnet topology and address spaces (to avoid CIDR conflicts).
  - Identify naming patterns already in use (to align new resources with existing conventions).
  - Check quotas and region availability for requested resource types and SKUs.
  - Detect existing Terraform state backends (Azure Storage accounts with state lock containers).
  - Surface findings to the user conversationally and pass them as structured constraints to CodeGen.
- Produces a structured **requirements handoff document** (analogous to a `.terraform-planning-files/INFRA.{goal}.md` planning file) that CodeGen consumes. This ensures the handoff from consulting to code generation is deterministic and auditable.

#### 7.1.2 Self-Service Catalog

- Keyword search across templates in the knowledge wiki.
- Template detail view showing description, Azure services used, complexity rating, and configurable parameters.
- Parameter form with template-specific inputs (VM size, node count, region, etc.). Org-level parameters (naming, tags) are auto-enforced.
- One-click deploy that hydrates the template, validates it, and enters the shared deployment pipeline (PR → Plan → Deploy).

#### 7.1.3 CodeGen Agent

- Generates Terraform HCL or Bicep based on user choice.
- Grounded by Terraform MCP Server (35 tools: provider schemas, module docs, policy references) and Bicep MCP Server (10 tools: resource schemas, AVM metadata, diagnostics, best practices).
- Produces modular, production-ready code with version-pinned providers, no placeholders, no hardcoded secrets.
- Supports iterative refinement via feedback from the IaC Validation Pipeline, Standards Agent, and Security Agent.
- Consumes the structured requirements handoff document from the Consulting Agent, including subscription discovery constraints (existing resources, VNet topology, naming patterns).

##### 7.1.3.1 AVM-First Module Strategy

The CodeGen Agent **must prefer Azure Verified Modules (AVM)** over raw resource declarations for any resource where an AVM module exists. AVM modules are pre-validated, WAF-aligned, and maintained by Microsoft, reducing code volume and maintenance burden.

- **Terraform:** Use `source = "Azure/avm-res-{service}-{resource}/azurerm"` with version pinning via `version = "~> x.y"`. Resolve latest versions via Terraform MCP Server or the Terraform Registry API endpoint `https://registry.terraform.io/v1/modules/Azure/{module}/azurerm/versions`.
- **Bicep:** Use `br/public:avm/res/{service}/{resource}:{version}` module references. Resolve latest versions via MCR endpoint `https://mcr.microsoft.com/v2/bicep/avm/res/{service}/{resource}/tags/list`.
- If no AVM module exists for a resource, use raw `azurerm_` resources (Terraform) or native Bicep resource declarations with the latest stable API version. The Standards Agent flags raw resources and recommends checking for AVM availability.
- Enable AVM telemetry: `enable_telemetry = true` (Terraform) unless the user explicitly opts out.

##### 7.1.3.2 Generated Code File Structure

CodeGen must produce a consistent file structure that the Standards Agent can validate:

**Terraform output:**

```
{project}/
├── main.tf                  # Core resources (or split by function: main.networking.tf, main.compute.tf)
├── variables.tf             # Input variables (alphabetized, typed, described)
├── outputs.tf               # Outputs (alphabetized, described, sensitive marked)
├── terraform.tf             # Provider configuration + required_providers with version pins
├── locals.tf                # Local values for complex expressions and common tags
└── environments/
    ├── dev.tfvars            # Development environment overrides
    └── prod.tfvars           # Production environment overrides
```

**Bicep output:**

```
{project}/
├── main.bicep               # Orchestration — module calls and parameter passing
├── main.bicepparam           # Parameter file — environment-specific values
└── modules/
    ├── network.bicep         # VNet, Subnet
    ├── compute.bicep         # App Service, VMs, AKS
    ├── data.bicep            # SQL, Cosmos, Storage
    ├── security.bicep        # Key Vault, RBAC assignments
    └── monitoring.bicep      # Log Analytics, App Insights
```

Variables and parameters must include explicit `type` declarations and comprehensive `description` / `@sys.description()` decorators. Variables are alphabetized within their file.

##### 7.1.3.3 Secret Handling Patterns

Generated code must follow zero-secret-in-code principles:

- **Prefer Managed Identities** over passwords, keys, or service principals wherever possible. When a resource has `identity { type = "SystemAssigned" }`, always generate accompanying RBAC role assignments.
- **Terraform:** Use `sensitive = true` on variables and outputs containing secrets. For Terraform v1.11+, use `ephemeral` resources and write-only attributes to avoid secrets persisting in state. Store secrets in Azure Key Vault via `azurerm_key_vault_secret`.
- **Bicep:** Use `@secure()` decorator on parameters containing secrets. Never place secret values in `.bicepparam` files — provide at deployment time or use Key Vault references.
- **Never** generate default passwords, hardcode connection strings, or embed API keys in IaC code.
- **Always** generate Key Vault resources when the architecture requires secrets, with `enableRbacAuthorization: true`, `enablePurgeProtection: true`, and `enableSoftDelete: true`.

#### 7.1.4 IaC Validation Pipeline

The validation pipeline is a **deterministic, non-LLM step** that runs between CodeGen output and the Standards Agent. It validates that generated code compiles, parses, and conforms to formatting standards before any policy or security review. This is not an agent — it is a function tool chain invoked directly by the Orchestrator.

**Terraform validation chain:**

| Step | Tool | Blocking? | On Failure |
|------|------|-----------|------------|
| 1 | `terraform fmt -check` | No | Auto-fix with `terraform fmt` (no CodeGen rework needed) |
| 2 | `terraform init` | Yes | Feed error to CodeGen (likely bad module source or version pin) |
| 3 | `terraform validate` | Yes | Feed structured errors to CodeGen for rework |
| 4 | `tflint` (stretch) | No | Warnings are informational, attached to H1 review |

**Bicep validation chain:**

| Step | Tool | Blocking? | On Failure |
|------|------|-----------|------------|
| 1 | `bicep build --stdout --no-restore` | Yes | Feed compilation errors to CodeGen for rework |
| 2 | `bicep format` | No | Auto-format (non-blocking) |
| 3 | `bicep lint` | Conditional | Errors → feed to CodeGen. Warnings triaged: BCP081 (type not defined) ignored if API version confirmed; BCP035 (missing property) checked against MS Docs; BCP187 (SKU/kind unverified) ignored |

**Catalog path behavior:** Hydrated templates run only Steps 1–3 (Terraform) or Steps 1–2 (Bicep). tflint/lint are skipped because templates are pre-validated.

**Rework integration:** Validation failures feed back to CodeGen as part of Loop 1 (Section 6.2.1). The shared retry counter across validation, standards, and security is 3 iterations total.

#### 7.1.5 Standards Agent

- Validates generated code against organizational naming conventions, required tags, and structural policies.
- Policies loaded from a policy repository (GitHub repo `/standards/` directory) via Policy RAG (Azure AI Search).
- Produces structured violation reports with resource name, violated policy, and expected value.
- Works with CodeGen agent to auto-enforce naming and tagging on catalog template deployments.
- **AVM compliance check:** Flags raw `azurerm_` resources (Terraform) or native Bicep resource declarations when an equivalent AVM module exists. Recommends the AVM module source and latest version.
- **Dependency correctness:** Detects redundant `depends_on` declarations where the dependency is already implicit through resource references. Recommends removal to keep code clean and avoid false dependency chains.
- **File structure validation:** Verifies that generated code follows the file structure conventions defined in Section 7.1.3.2.

#### 7.1.6 Security Agent

- Runs tfsec and/or Checkov static analysis on generated Terraform code.
- For Bicep: runs `bicep build` diagnostics via the Bicep MCP Server plus equivalent security checks.
- Produces structured finding reports with severity, resource, and remediation guidance.

#### 7.1.7 PR Workflow Agent

- Creates a feature branch and commits all generated IaC files.
- Opens a Pull Request with a structured description (resources created, standards applied, security scan results).
- Commits the auto-generated architecture diagram (SVG) to `/docs/architecture/` in the repo.
- Connects to GitHub Actions via GitHub MCP Server to monitor CI/CD pipeline status.

#### 7.1.8 Deploy Agent

- Triggers `terraform plan` or `bicep what-if` via GitHub Actions CI/CD.
- **Set Diff Analysis (Terraform):** Before surfacing plan output to the user, optionally runs the Set Diff Analyzer to filter false-positive diffs caused by AzureRM Set-type attribute reordering (e.g., Application Gateway backend pools, NSG security rules). The analyzer categorizes changes as: 🟢 order-only (safe to ignore), 🟡 actual Set changes (review content), 🔴 resource replacement (check downtime impact). This reduces noise in the H2 review.
- Surfaces plan output to the user for Human Gate H2 review.
- On approval, triggers `terraform apply` or `az deployment create`.
- Monitors deployment progress and reports status in real-time.
- On plan failure, extracts the full error output (stderr + exit code), categorizes the failure (see Section 6.2.1 plan failure table), and routes back to CodeGen for rework (Loop 2).

#### 7.1.9 Architecture Diagram Generation

- Auto-generates visual architecture diagrams from generated IaC code (IaC is the source of truth — diagrams are never manually drawn).
- **Generation approach:** The CodeGen Agent produces a Mermaid diagram definition alongside the IaC code. The Mermaid definition is rendered to SVG by the frontend for interactive viewing (zoom/pan) and committed to the repository as a static SVG in `/docs/architecture/`. For complex multi-resource architectures, the diagram shows resource groups, networking topology (VNets, subnets, private endpoints), compute resources, data services, and their relationships.
- Downloadable as SVG/PNG.
- Committed to the repository alongside the IaC code in the PR.

#### 7.1.10 Human Gates (H1, H2)

- H1: Code + diagram review UI before PR creation.
- H2: Plan output review UI before deployment.
- Clear approve/reject actions with feedback mechanism.

#### 7.1.11 Presentation Layer

- React / Next.js frontend with two entry points: Chat interface and Self-Service Catalog.
- File explorer for browsing generated IaC files with syntax highlighting.
- Architecture diagram viewer with zoom/pan/export.
- Deployment pipeline status tracker (PR → Plan → Deploy stages).

### 7.2 P1 — Should Have (Stretch for Hackathon)

- Template Curation Agent: Post-deploy analysis, novelty check, parameter generalization, wiki PR.
- Human Gate H3: Template approval workflow for knowledge wiki contributions.
- Knowledge wiki feedback loop: Approved templates appear in the self-service catalog automatically.
- Conversation memory: Persist chat history across sessions via Azure PostgreSQL / Cosmos DB.
- IaC language toggle: User switches between Terraform and Bicep mid-conversation; CodeGen agent adapts.
- Cost estimation: Integrate Infracost (Terraform) or Azure Pricing Calculator API for cost preview before deployment.
- Terraform state awareness (read-only): Connect to existing remote state backends (Azure Storage, HCP Terraform) to detect already-managed resources and avoid conflicts during code generation.
- Set Diff Analyzer integration: Filter false-positive diffs in Terraform plan output before H2 review.

### 7.3 P2 — Nice to Have (Post-Hackathon)

- Multi-user RBAC: Different roles for requester, approver, template curator.
- Entra ID authentication with SSO/SAML for enterprise.
- Multi-cloud support: AWS and GCP providers via Terraform MCP.
- Terraform state awareness (write): Incremental changes to existing state, import of unmanaged resources.
- Diff view for iterative changes: Side-by-side comparison when code is modified.
- Compliance reporting: Map each resource to the organizational standards it satisfies.
- GitHub Copilot Extension: Surface InfraAgent as `@infraagent` in VS Code / GitHub.
- Copilot Studio integration: Surface InfraAgent in Teams/M365.
- Test generation: Auto-generate Terratest (Go) or `.tftest.hcl` test cases alongside IaC code for module validation.
- Idempotency verification: Run a second `terraform plan` after apply to confirm zero-diff (no configuration drift introduced by the deployment itself).

---

## 8. Knowledge Wiki and Domain Skills

### 8.1 Knowledge Wiki Structure

The knowledge wiki is a **separate GitHub repository** that serves as the single source of truth for reusable IaC templates, architecture patterns, and domain expertise. It is consumed by InfraAgent as a **git submodule**, enabling independent versioning, separate access control, and clean separation of concerns between the platform codebase and the knowledge content.

#### 8.1.1 Repository Layout

**`templates/`** — Each template is a directory containing a complete, deployable IaC module (or set of modules for multi-resource architectures).

- `templates/aks-cluster/terraform/` — main.tf, variables.tf, outputs.tf
- `templates/aks-cluster/bicep/` — main.bicep, parameters.json
- `templates/aks-cluster/metadata.yaml` — Name, description, Azure services, complexity, parameters schema, tags
- `templates/3-tier-web-app/terraform/` — Multiple modules (app-service/, sql-database/, vnet/) composing a full architecture
- `templates/3-tier-web-app/bicep/` — Equivalent Bicep modules

**`skills/`** — Pluggable domain skills that guide the Consulting Agent behavior.

**`standards/`** — Organizational policy files (naming.md, tagging.md, policies.md).

**`patterns/`** — Architecture decision records (ADRs) and reference architecture documentation.

#### 8.1.2 Git Submodule Integration

The knowledge wiki repo is referenced in the InfraAgent repo as a git submodule at the path `knowledge-wiki/`:

```
infraagent/
├── src/                          # InfraAgent platform code
├── knowledge-wiki/               # Git submodule → wiki repo
│   ├── templates/
│   ├── skills/
│   ├── standards/
│   └── patterns/
├── .gitmodules                   # Submodule configuration
└── ...
```

**Versioning strategy:**

- The submodule reference is pinned to a specific commit (not a branch). This ensures that InfraAgent always runs against a known, tested version of the wiki content.
- Updates to the wiki are pulled into InfraAgent by updating the submodule reference: `git submodule update --remote knowledge-wiki` followed by a commit that bumps the pinned commit hash.
- The wiki repo has its own release tags (e.g., `v1.0.0`, `v1.1.0`). InfraAgent pins to release tags for production and may track `main` for development.

**Runtime access:**

- The Consulting Agent, CodeGen Agent, and Self-Service Catalog read from the submodule path at runtime. Templates are loaded from `knowledge-wiki/templates/`, skills from `knowledge-wiki/skills/`, and policies from `knowledge-wiki/standards/`.
- The Template Curation Agent proposes new templates via PRs to the **wiki repo** (not the InfraAgent repo). Once merged via H3 approval, the InfraAgent repo's submodule reference is updated to include the new template.

**CI implications:**

- InfraAgent CI/CD pipelines must run `git submodule update --init --recursive` during checkout.
- Wiki repo has its own CI pipeline that validates template syntax (`terraform validate` / `bicep build`), checks metadata schema, and runs linting on all templates before merge.

### 8.2 Template Metadata Schema

Every template includes a `metadata.yaml` file that enables catalog search, parameter forms, and consulting agent recommendations:

| Field | Type | Description |
|-------|------|-------------|
| name | string | Human-readable template name |
| description | string | What this template deploys and why |
| azure_services | string[] | Azure services used (e.g., AKS, App Service, SQL Database) |
| complexity | enum | simple \| moderate \| complex |
| iac_languages | string[] | Available IaC languages: [terraform, bicep] |
| parameters | object[] | Configurable parameters with name, type, default, description, validation rules |
| tags | string[] | Searchable keywords for catalog discovery |
| version | string | Semantic version of the template |
| author | string | Creator (engineer name or Template Curation Agent) |
| approved_by | string | Platform engineer who approved via H3 |
| created_at | date | Date template was added to the wiki |

### 8.3 Domain Skills

Domain skills are pluggable markdown files that inject domain-specific knowledge into the Consulting Agent. Each skill defines phase-specific questions, architecture patterns, component catalogs, and readiness checklists. The Consulting Agent loads the relevant skill based on the user's stated use case.

Example: A "foundry-ads-session" skill teaches the Consulting Agent how to run an Azure AI Foundry architecture design session. An "aks-deployment" skill would teach it AKS-specific questions (node pool sizing, CNI selection, ingress controller choice). Skills are version-controlled in the knowledge wiki and can be authored by solutions architects.

Skill files follow a standard structure: metadata header (name, description, version, domain), phase-specific question banks, pattern selection logic, component catalogs, readiness checklists, and references to deep-dive documents.

---

## 9. MCP Server Integration

InfraAgent uses four MCP servers as the grounding layer for all code generation and Azure operations. Agents connect to MCP servers natively via the Foundry Agent Service MCP tool type.

| MCP Server | Source | Tools | Used By | Purpose |
|------------|--------|-------|---------|---------|
| Terraform MCP Server | hashicorp/terraform-mcp-server | 35 (registry, modules, policies, workspaces) | CodeGen Agent | Live Terraform Registry schemas; eliminates hallucinated resource arguments |
| Bicep MCP Server | Azure/bicep (built-in) | 10 (schemas, AVM, diagnostics, best practices) | CodeGen Agent | Live Azure resource schemas; Bicep compilation and validation |
| Azure MCP Server | microsoft/mcp | 40+ (resource mgmt, Key Vault, AKS, etc.) | Consulting Agent, CodeGen Agent, Deploy Agent | Subscription context, resource queries, quota checks, deployment ops |
| GitHub MCP Server | github/github-mcp-server | PR, branch, workflow tools | PR Workflow Agent, Deploy Agent | PR creation, CI/CD pipeline triggering and monitoring |

The Foundry MCP Server at `mcp.ai.azure.com` provides a managed hosting surface for MCP servers, eliminating the need for self-hosted MCP processes. Custom MCP servers (e.g., for tfsec/Checkov) can be hosted on Azure Functions using the MCP binding extensions.

---

## 10. Clean Architecture

InfraAgent follows hexagonal architecture (ports and adapters) to ensure business logic is fully decoupled from framework, LLM provider, and IaC tool dependencies. This is a non-negotiable design constraint.

### 10.1 Layer Separation

| Layer | Contains | Depends On | Never Depends On |
|-------|----------|-----------|-----------------|
| Domain | Deployment policies, resource validators, naming rules, cost estimators, policy constraints | Nothing (pure business logic) | Any framework, LLM, or external service |
| Application | Use cases: PlanInfrastructure, ValidatePolicy, GenerateCode, DeployResources | Domain layer only | Specific LLM provider, IaC tool, or git service |
| Tool / Anti-Corruption | Translates LLM string I/O to rich domain objects. Tools accept simple params, call services, return strings | Application layer | LLM internals, framework specifics |
| Infrastructure | LLM adapters (Azure OpenAI, Anthropic), IaC adapters (Terraform CLI, Bicep CLI), Git adapters, MCP clients | Port interfaces defined in Application layer | Domain logic |
| Presentation | React/Next.js frontend, API routes, WebSocket handlers | Application layer via API | Domain or infrastructure details |

### 10.2 Key Port Interfaces

Port interfaces define the contracts between layers. Changing an LLM provider, IaC tool, or git service means implementing a new adapter without touching any other layer.

- **ILLMCompletionPort:** Abstracts over model providers. Methods: `complete()`, `complete_with_tools()`. The **default adapter is ModelRouter**, which routes requests to optimal models based on task profiles. Direct-model adapters (Azure OpenAI, Anthropic Claude) are available as fallbacks or for testing.
- **IInfraProviderPort:** Abstracts over Terraform and Bicep. Methods: `validate()`, `plan()`, `apply()`, `get_state()`, `fmt()`, `lint()`. The validation pipeline (Section 7.1.4) is implemented through this port.
- **ISourceControlPort:** Abstracts over GitHub (and future Azure DevOps). Methods: `create_branch()`, `commit_files()`, `create_pr()`, `get_pipeline_status()`.
- **IPolicyEnginePort:** Abstracts over policy evaluation. Methods: `validate_naming()`, `validate_tags()`, `validate_security()`, `check_avm_availability()`.
- **ITemplateRegistryPort:** Abstracts over the knowledge wiki (git submodule). Methods: `search()`, `get_template()`, `hydrate()`, `publish()`.
- **ISubscriptionDiscoveryPort:** Abstracts over Azure subscription queries. Methods: `list_resource_groups()`, `list_resources()`, `get_vnet_topology()`, `check_quotas()`, `detect_naming_patterns()`.
- **IObservabilityPort:** Abstracts over telemetry. Methods: `trace()`, `metric()`, `log()`. Wraps OpenTelemetry.

### 10.3 Why This Matters

The existing TerraBot codebase entangles business logic (naming conventions, policy enforcement) with infrastructure concerns (Anthropic SDK, Express routes, MCP client). Switching to Azure OpenAI or adding Bicep support would require invasive changes across the entire codebase. InfraAgent avoids this by placing all business rules in the domain layer, all LLM/tool interactions behind port interfaces, and all framework-specific code in the infrastructure layer. ModelRouter as the default `ILLMCompletionPort` adapter means agents never reference specific models — they declare intent, and the platform handles model selection, failover, and cost optimization transparently.

---

## 11. Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| AI Platform | Azure AI Foundry Agent Service | Managed agent runtime with native MCP support, model catalog, tracing |
| Model Selection | Azure AI Foundry ModelRouter | Automatic model routing across the model catalog. Agents declare task profiles, ModelRouter selects optimal model based on cost, capability, and availability. Eliminates hardcoded model assignments. |
| Agent Framework | Microsoft Agent Framework (Python) | Graph-based workflows, checkpointing, human-in-the-loop, handoff pattern |
| Backend | Python (FastAPI or Flask) | Foundry SDK is Python-first; Agent Framework is Python-native |
| Frontend | React 18 + Next.js + TypeScript | Existing competency; Tailwind CSS + shadcn/ui for rapid UI development |
| IaC Grounding | Terraform MCP Server + Bicep MCP Server | Live registry schemas; zero hallucinated resource arguments |
| Azure Operations | Azure MCP Server | Resource queries, subscription discovery, deployment operations |
| Source Control | GitHub + GitHub MCP Server | PR workflows, CI/CD via GitHub Actions |
| Knowledge Wiki | Separate GitHub repo (git submodule in InfraAgent) | Independent versioning, separate CI, clean separation of platform code and knowledge content |
| Database | Azure PostgreSQL (or Cosmos DB) | Conversation history, deployment tracking, user settings |
| Vector Search | Azure AI Search | Policy RAG for standards enforcement; template search for catalog |
| Security Scanning | tfsec, Checkov (via Azure Functions) | Static analysis of generated IaC code |
| IaC Validation | Terraform CLI, Bicep CLI, tflint | Deterministic validation pipeline (fmt, init, validate, lint) before agent review |
| Observability | Azure Monitor + App Insights + OpenTelemetry | Tracing, metrics, evaluation scores |
| Identity | Microsoft Entra ID + RBAC | User auth, managed identity for service-to-service |
| Secrets | Azure Key Vault | GitHub PATs, API tokens, Azure credentials |
| IaC for InfraAgent itself | Bicep | InfraAgent's own infrastructure is deployed via Bicep (meta-point for hackathon) |

---

## 12. Hackathon MVP Scope

With 3 weeks and 5 engineers, the following scope defines what must be working for the demo versus what can be shown as architecture / design only.

### 12.1 Demo Script

**Demo 1 — Chat Path (3–4 minutes):** An application engineer opens the chat interface and says: "I need a 3-tier web app with an App Service frontend, a SQL Database backend, and a VNet with proper subnets." The Consulting Agent asks 2–3 clarifying questions (environment, region, sizing). The engineer answers. The Consulting Agent connects to the target Azure subscription, discovers existing resource groups and VNets, and surfaces them ("I can see you already have `rg-prod-westeurope` with a VNet..."). The Consulting Agent checks the knowledge wiki — no exact match. It routes to the custom pipeline. The engineer chooses Bicep. CodeGen generates modular Bicep code using AVM modules. The IaC Validation Pipeline runs `bicep build` + `bicep format` — passes. Standards validates naming/tags, Security scans — both pass. The engineer reviews code + Mermaid architecture diagram (H1), approves. A PR is created. GitHub Actions runs `bicep what-if`. The engineer reviews the plan (H2), approves. Deployment succeeds.

**Demo 2 — Catalog Path (1–2 minutes):** The same or different engineer opens the Self-Service Catalog, searches for "AKS cluster", selects a pre-validated template, fills in node count and VM size, clicks deploy. Subscription discovery checks for naming conflicts and quota availability. The template is hydrated with org naming/tags, the validation pipeline runs `terraform validate` on the hydrated code, a PR is created, plan runs, the engineer approves, deployment succeeds.

**Demo 3 — Plan Failure + Rework (2–3 minutes):** An engineer requests an AKS cluster via the chat interface. CodeGen generates Terraform code. Validation pipeline passes. Standards and Security pass. The engineer approves at H1. A PR is created. GitHub Actions runs `terraform plan` — plan **fails** (e.g., "VM size Standard_D4s_v3 not available in westeurope"). The Deploy Agent categorizes the failure, feeds the plan error output back to CodeGen. CodeGen queries Azure MCP for available SKUs in the region, updates the VM size, re-runs the validation pipeline, and a new PR is created. Plan succeeds. The engineer approves at H2. Deployment succeeds.

### 12.2 Team Allocation (Suggested)

| Engineer | Focus Area | Key Deliverables |
|----------|-----------|-----------------|
| Engineer 1 | Agent Backend + Foundry | Agent definitions, orchestrator workflow, MCP connections, ModelRouter profiles, agent framework setup |
| Engineer 2 | CodeGen + Validation + Standards + Security | Code generation logic (AVM-first), IaC validation pipeline (fmt/validate/lint), standards validation, security scanning integration |
| Engineer 3 | Frontend | Chat UI, catalog UI, file explorer, Mermaid diagram viewer, deployment tracker, subscription discovery display |
| Engineer 4 | GitHub + Deploy Pipeline | PR workflow, GitHub Actions integration, deploy agent, plan/apply flow, plan-failure rework loop |
| Engineer 5 | Knowledge Wiki + Infrastructure | Wiki repo setup (separate repo + submodule), template authoring, domain skills, Bicep IaC for InfraAgent itself, demo environment |

### 12.3 Week-by-Week Plan

| Week | Milestone | Deliverables |
|------|-----------|-------------|
| Week 1 | Foundation | Azure AI Foundry project provisioned with ModelRouter configured. Agent definitions created with task profiles. Frontend scaffolded with chat + catalog views. Knowledge wiki repo created (separate repo) with 2–3 starter AVM-based templates. Git submodule wired into InfraAgent repo. GitHub Actions workflow templates. Clean architecture skeleton in Python with port interfaces defined. IaC validation pipeline shell (fmt/validate/lint) working locally. |
| Week 2 | Integration | End-to-end chat path working (consulting → subscription discovery → codegen → validation pipeline → standards → PR). Catalog path working (template select → hydrate → validate → PR). Human gates H1/H2 functional. Mermaid architecture diagram generation from IaC code. MCP servers connected. Plan-failure → CodeGen rework loop functional. |
| Week 3 | Polish + Demo | Demo script rehearsed (all 3 demos). Edge cases handled (plan failure rework, SKU unavailability). UI polished. Deployment to a real Azure subscription verified. Subscription discovery surfaces real resources in demo. Pitch deck updated. Recording backup prepared. |

---

## 13. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Time from request to PR | < 3 minutes (chat path), < 1 minute (catalog path) | End-to-end latency from first user message to open PR |
| IaC validity rate | > 95% | Percentage of generated code passing the IaC Validation Pipeline (terraform validate / bicep build) on first attempt |
| Validation pipeline pass rate (post-rework) | 100% | All code reaching H1 must pass fmt + validate + lint (ensured by Loop 1 retries) |
| Standards compliance | 100% | All output adheres to org naming/tagging rules on first generation |
| Security scan pass rate | > 90% (no critical/high findings) | Percentage of generated code passing tfsec/Checkov with zero critical/high findings |
| AVM module usage | > 80% | Percentage of generated resources using AVM modules (when available) vs raw resource declarations |
| Diagram accuracy | 100% | Diagram reflects every resource in the generated IaC code |
| Subscription discovery success | 100% | Consulting Agent successfully connects to target subscription and surfaces existing resources |
| Demo completion | All 3 paths end-to-end | Chat path, catalog path, and plan-failure rework path all result in a successful Azure deployment |
| Template catalog size | >= 3 templates | Number of pre-validated templates available in the self-service catalog at demo time |

---

## 14. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| LLM generates invalid IaC | High | Medium | MCP grounding + IaC Validation Pipeline (fmt/validate/lint) + maker-checker loop (max 3 retries) catches compilation errors before human review |
| Foundry Agent Service limitations hit during build | High | Medium | Fallback: use Foundry hosted agents with custom orchestration code rather than workflow agents |
| ModelRouter selects suboptimal model for task | Medium | Medium | Task profiles are tuned during hackathon. Fallback candidates defined per profile. Manual override available per agent if needed. |
| MCP server unavailability | Medium | Low | Graceful degradation: fall back to plain LLM chat with cached schemas. Flag output as ungrounded. |
| 3-week timeline too tight for both paths | High | Medium | Prioritize chat path (Demo 1). Catalog can be a curated static list with simplified deployment for MVP. |
| Partial terraform apply failure | Critical | Low | Deploy agent monitors apply, captures partial state. Rollback guidance provided to human. State file is customer-owned. |
| GitHub Actions rate limits | Medium | Low | Exponential backoff on API calls. Batch file commits into single tree commit. |
| Bicep MCP Server maturity (experimental) | Medium | Medium | Terraform path is the primary demo. Bicep shown as second language option. Bicep validation falls back to CLI-based `bicep build` + `bicep lint` when MCP tools are insufficient. |
| Team unfamiliar with Agent Framework | Medium | Medium | Week 1 includes ramp-up. Simpler handoff pattern used instead of complex magentic orchestration. |
| Azure subscription discovery returns stale data | Medium | Low | All discovery data is point-in-time via Azure MCP. Surface timestamps to user. Plan step (`terraform plan` / `bicep what-if`) is the authoritative check against live state. |
| Knowledge wiki submodule version drift | Low | Medium | Pin submodule to release tags. CI pipeline validates submodule checkout. Alert when wiki repo has new releases not yet pulled into InfraAgent. |
| AVM module version lag | Low | Medium | CodeGen resolves latest AVM versions via MCP/Registry API at generation time. Standards Agent flags outdated version pins. |

---

## 15. Competitive Differentiation

InfraAgent is the only platform combining all of the following capabilities:

| Capability | InfraAgent | Terraform Cloud | GitHub Copilot | Spacelift / env0 | Pulumi AI |
|-----------|-----------|----------------|---------------|-----------------|-----------|
| NL → IaC generation | ✓ (Terraform + Bicep) | Preview (Infragraph) | Partial | ✗ | ✓ (Pulumi only) |
| Live registry grounding via MCP | ✓ (TF + Bicep MCP) | Preview (TF MCP beta) | ✗ | ✗ | Pulumi MCP |
| Automatic model selection (ModelRouter) | ✓ | ✗ | ✗ | ✗ | ✗ |
| Multi-agent orchestration | ✓ (8 agents) | ✗ | ✗ | ✗ | ✗ |
| Consulting agent (SA pair) | ✓ | ✗ | ✗ | ✗ | ✗ |
| Azure subscription discovery | ✓ (pre-deploy inventory) | ✗ | ✗ | ✗ | ✗ |
| Self-service catalog | ✓ | ✗ | ✗ | ✗ | ✗ |
| Knowledge feedback loop | ✓ | ✗ | ✗ | ✗ | ✗ |
| IaC validation pipeline | ✓ (fmt/validate/lint) | ✗ | ✗ | ✗ | ✗ |
| AVM-first module strategy | ✓ | ✗ | ✗ | ✗ | ✗ |
| Policy enforcement agent | ✓ | Sentinel | ✗ | OPA | CrossGuard |
| Security scanning agent | ✓ (tfsec + Checkov) | RunTasks | ✗ | Partial | ✗ |
| Plan diff analysis (false-positive filtering) | ✓ (Set Diff Analyzer) | ✗ | ✗ | ✗ | ✗ |
| Human-in-the-lead gates | ✓ (H1, H2, H3) | Manual | Manual | Manual | ✗ |
| MCP server reusability | ✓ (reusable tool layer) | Preview | ✗ | ✗ | Pulumi MCP |

---

## 16. Out of Scope (Future Phases)

- Multi-cloud support (AWS, GCP) — architecture supports it via `IInfraProviderPort` abstraction.
- Azure DevOps integration — architecture supports it via `ISourceControlPort` abstraction.
- Terraform import automation — importing existing unmanaged Azure resources.
- Enterprise compliance reporting (SOC2, HIPAA, PCI-DSS).
- Multi-tenant SaaS deployment — InfraAgent as a hosted service.
- Real-time collaboration — multiple users in the same session.
- Drift detection — monitoring deployed resources for configuration drift.
- Automated rollback — auto-reverting failed deployments without human intervention.

---

## 17. Glossary

| Term | Definition |
|------|-----------|
| IaC | Infrastructure as Code. Managing infrastructure through machine-readable configuration files. |
| HCL | HashiCorp Configuration Language. The declarative language used by Terraform. |
| Bicep | A domain-specific language for deploying Azure resources. Compiles to ARM templates. |
| MCP | Model Context Protocol. A standard for connecting AI models to external tools and data sources. |
| AVM | Azure Verified Modules. Microsoft-maintained Terraform/Bicep modules for Azure resources, aligned with the Well-Architected Framework. |
| ModelRouter | Azure AI Foundry's automatic model selection service. Routes agent requests to optimal models based on task profile, cost, and availability. |
| Foundry | Azure AI Foundry. Microsoft's unified AI platform for building, deploying, and managing AI applications. |
| Agent Service | The managed agent runtime within Azure AI Foundry for hosting and orchestrating AI agents. |
| PR | Pull Request. A proposed code change submitted for review before merging. |
| H1 / H2 / H3 | Human approval gates in the InfraAgent pipeline (code review, plan review, template approval). |
| Maker-Checker | A pattern where one agent generates output and another validates it, with iterative feedback. |
| Domain Skill | A pluggable markdown file that injects domain-specific expertise into the Consulting Agent. |
| Knowledge Wiki | A separate GitHub repository containing reusable IaC templates, architecture patterns, and domain skills. Consumed by InfraAgent as a git submodule. |
| Template Curation Agent | An agent that analyzes deployed custom code and proposes it as a reusable template. |
| CAF | Cloud Adoption Framework. Microsoft's methodology for cloud architecture and governance. |
| WAF | Well-Architected Framework. Microsoft's set of guiding tenets for improving workload quality (cost, reliability, security, performance, operational excellence). |
| tfsec | A static analysis tool for Terraform that detects security misconfigurations. |
| Checkov | A policy-as-code tool that scans IaC for security and compliance violations. |
| tflint | A Terraform linter that enforces style and best-practice rules beyond what `terraform validate` catches. |
| IaC Validation Pipeline | A deterministic (non-LLM) toolchain step that runs fmt, init, validate, and lint on generated code before agent or human review. |
| Subscription Discovery | The process of connecting to a live Azure subscription to inventory existing resources, VNets, quotas, and naming patterns before code generation. |
| Set Diff Analyzer | A tool that filters false-positive diffs in Terraform plan output caused by AzureRM Set-type attribute reordering. |
| Git Submodule | A Git mechanism for embedding one repository inside another at a specific commit, enabling independent versioning. |

---

*End of Document*
