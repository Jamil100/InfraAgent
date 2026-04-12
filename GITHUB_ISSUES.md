# InfraAgent — GitHub Issues Backlog v2

**Timeline:** 3 weeks (April 2026)
**Team:** 5 engineers
**Priority Legend:** P0 = Must Have (MVP), P1 = Should Have (Stretch), P2 = Nice to Have (Post-Hackathon)
**Size Legend:** XS (< 2h), S (2-4h), M (4-8h), L (1-2 days), XL (2-3 days)

**Engineer Tracks:**
- **E1** — Agent Backend + Foundry + Orchestration
- **E2** — CodeGen + Validation + Standards + Security
- **E3** — Frontend
- **E4** — GitHub + Deploy Pipeline + API
- **E5** — Knowledge Wiki + Infrastructure + Templates

---

## Definition of Done (All Issues)

Every issue is considered complete when:
- [ ] All acceptance criteria are met
- [ ] Type hints on all function signatures
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `mypy` passes (no type errors)
- [ ] Unit tests written and passing (domain: 100% coverage; application: use case tests with mocked ports)
- [ ] PR reviewed by at least one other engineer
- [ ] No hardcoded secrets, API keys, or credentials in code

---

## Milestones

| Milestone | Week | Gate Criteria |
|-----------|------|---------------|
| **M1: Foundation Complete** | End of Week 1 | Repo structured. All domain models + ports defined. All adapters scaffolded. Frontend scaffolded with routing. Wiki repo created with 3 templates. Azure infra provisioned. DB running locally. `pytest tests/unit/` passes. Backend starts (`/health` returns OK). Frontend loads landing page. |
| **M2: Integration Complete** | End of Week 2 | All use cases working. All agents registered in Foundry. Both orchestrator workflows functional. All API endpoints serving. All frontend views rendering. Chat path works locally (mocked plan/apply). Catalog path works locally. MCP servers connected. |
| **M3: Demo Ready** | End of Week 3 | All 3 demos pass against real Azure subscription. UI polished. Subscription discovery surfaces real resources. Demo script runs cleanly 3 times in a row. Recording backup prepared. |

---

## EPIC 1: Project Setup & Infrastructure Foundation

---

### Issue #1 — Initialize monorepo with clean architecture project structure

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1) | **Assignee:** E1
**Labels:** `setup`, `backend`, `foundation`
**Blocks:** #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16

**Description:**
Create the InfraAgent monorepo with the full clean architecture directory structure defined in TechSpec Section 11. This is the skeleton that all other work builds on.

**Acceptance Criteria:**
- [ ] Repository initialized with `src/domain/`, `src/application/`, `src/infrastructure/`, `src/api/`, `src/prompts/`, `frontend/`, `infra/`, `tests/`, `.github/workflows/`
- [ ] `pyproject.toml` configured with Python 3.12, dependencies (fastapi, uvicorn, azure-ai-projects, azure-identity, sqlalchemy[asyncio], asyncpg, pydantic, ruff, mypy, pytest, pytest-asyncio, httpx)
- [ ] `ruff` and `mypy` configured per TechSpec Section 16.1
- [ ] `Dockerfile` and `docker-compose.yml` scaffolded (backend + postgres)
- [ ] `.gitignore` for Python, Node, Terraform, Bicep artifacts
- [ ] Empty `__init__.py` files in all Python packages
- [ ] `README.md` with project overview and setup instructions
- [ ] `.env.example` with all environment variables documented

**Tech Details:**
- Follow the project structure from TechSpec Section 11 exactly
- Use `pyproject.toml` with `[project.optional-dependencies] dev = [...]` for dev deps
- Python 3.12+ required (Foundry SDK dependency)

---

### Issue #2 — Define domain layer models and enums

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E2
**Labels:** `domain`, `backend`, `foundation`
**Depends on:** #1
**Blocks:** #10, #14, #15, #16, #17

**Description:**
Implement all domain models, enums, and dataclasses from TechSpec Section 3.1. These are pure Python dataclasses with zero external dependencies — the core of the clean architecture.

**Acceptance Criteria:**
- [ ] `src/domain/models/deployment.py` — `DeploymentStage` (all 14 stages: CONSULTING, DISCOVERING_SUBSCRIPTION, GENERATING, VALIDATING_IAC, VALIDATING_STANDARDS, SCANNING_SECURITY, AWAITING_CODE_REVIEW, CREATING_PR, RUNNING_PLAN, REWORKING_PLAN_FAILURE, AWAITING_PLAN_REVIEW, DEPLOYING, DEPLOYED, FAILED, CANCELLED), `ProjectType` (DEMO, PRODUCTION, ENTERPRISE, REGULATED), `IaCLanguage`, `DeploymentPath`, `GeneratedFile`, `DeploymentRequest`, `Conversation` enums and dataclasses
- [ ] `src/domain/models/template.py` — `TemplateMetadata`, `HydratedTemplate` dataclasses
- [ ] All enums match PRD Section 6 and TechSpec Section 3.1 exactly
- [ ] Zero imports from `azure`, `openai`, `fastapi`, or any third-party package
- [ ] Unit tests in `tests/unit/domain/test_models.py`

**Tech Details:**
- Use Python `dataclasses` and `enum.Enum` (no Pydantic in domain layer)
- Ref: TechSpec Section 3.1

---

### Issue #3 — Implement domain policies (naming, tagging, security)

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 2-3) | **Assignee:** E2
**Labels:** `domain`, `backend`, `foundation`
**Depends on:** #1
**Blocks:** #23, #24, #28

**Description:**
Implement deterministic business rule validators for naming conventions, required tags, and security policy checks as pure functions in the domain layer.

**Acceptance Criteria:**
- [ ] `src/domain/policies/naming_policy.py` — `NamingRule` dataclass, `DEFAULT_NAMING_RULES` list (rg, vnet, snet, vm, storage, nsg patterns), `validate_resource_name()` pure function
- [ ] `src/domain/policies/tagging_policy.py` — `TagRule` dataclass, `DEFAULT_REQUIRED_TAGS` list (environment, owner, cost-center, application, created-by), `validate_tags()` pure function
- [ ] `src/domain/policies/security_policy.py` — `SECURITY_RULES` list (SEC-001 through SEC-007)
- [ ] `src/domain/services/standards_service.py` — `StandardsViolation`, `StandardsResult`, `validate_standards()` function that orchestrates naming + tagging checks
- [ ] 100% unit test coverage in `tests/unit/domain/`
- [ ] All functions are pure — no I/O, no LLM calls, no external dependencies

**Tech Details:**
- Naming patterns use regex (e.g., `^rg-\w+-\w+-\w+$`)
- Tags with enforcement "required" must be present; "auto" are system-injected
- Ref: TechSpec Section 3.2, 3.3

---

### Issue #4 — Define all port interfaces (application layer contracts)

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E1
**Labels:** `architecture`, `backend`, `foundation`
**Depends on:** #1
**Blocks:** #10, #11, #12, #13, #14, #15, #16, #17, #28, #29

**Description:**
Define all abstract port interfaces in the application layer. These are the contracts between layers — changing an LLM provider, IaC tool, or git service means implementing a new adapter without touching business logic.

**Acceptance Criteria:**
- [ ] `src/application/ports/llm_port.py` — `LLMMessage`, `LLMResponse`, `ToolDefinition`, `TaskProfile` dataclasses + `ILLMCompletionPort` ABC with `complete()` and `complete_with_tools()` methods (ModelRouter-aware via TaskProfile)
- [ ] `src/application/ports/infra_provider_port.py` — `ValidationResult`, `PlanResult`, `ApplyResult` dataclasses + `IInfraProviderPort` ABC with `format_check()`, `validate()`, `lint()`, `plan()`, `apply()`, `get_language()`
- [ ] `src/application/ports/source_control_port.py` — `PRResult`, `PipelineStatus` dataclasses + `ISourceControlPort` ABC with `create_branch()`, `commit_files()`, `create_pr()`, `get_pipeline_status()`, `trigger_workflow()`
- [ ] `src/application/ports/policy_engine_port.py` — `PolicyViolation`, `PolicyResult` dataclasses + `IPolicyEnginePort` ABC with `validate_naming()`, `validate_tags()`, `validate_security()`, `check_avm_availability()`
- [ ] `src/application/ports/template_registry_port.py` — `ITemplateRegistryPort` ABC with `search()`, `get_template()`, `hydrate()`, `publish()`
- [ ] `src/application/ports/subscription_discovery_port.py` — `DiscoveredResource`, `DiscoveredVNet`, `SubscriptionContext` dataclasses + `ISubscriptionDiscoveryPort` ABC with `discover()`, `check_sku_availability()`, `check_quota()`
- [ ] `src/application/ports/observability_port.py` — `IObservabilityPort` ABC with `start_span()`, `record_metric()`, `log()`
- [ ] All ports use `async` methods and Python ABCs
- [ ] No implementation details — only contracts

**Tech Details:**
- `TaskProfile` has `profile` field for ModelRouter: "complex-reasoning", "code-generation", "analysis", "fast-lightweight", "orchestration"
- `LLMResponse` includes `model_used: str | None` to track which model ModelRouter selected
- Ref: TechSpec Section 2.1 for all port definitions

---

### Issue #5 — Implement IaC parser for HCL/Bicep resource extraction

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 3-4) | **Assignee:** E2
**Labels:** `domain`, `backend`, `foundation`
**Depends on:** #1, #2
**Blocks:** #23, #24

**Description:**
Implement `src/domain/services/iac_parser.py` — a domain service that parses raw HCL (Terraform) and Bicep text into structured resource models. This is required by the Standards Agent to validate naming, tagging, and structural policies against the generated code.

**Acceptance Criteria:**
- [ ] `parse_terraform_resources(hcl_content: str) -> list[dict]` — Extracts resource type, name, tags, and key attributes from HCL resource blocks. Returns `[{"type": "azurerm_resource_group", "name": "rg-prod-web-eastus", "tags": {...}, "file": "main.tf", "line": 5}]`
- [ ] `parse_bicep_resources(bicep_content: str) -> list[dict]` — Extracts resource type, name, tags, and key attributes from Bicep resource declarations. Returns same structure.
- [ ] Handles multi-file parsing: accepts list of `GeneratedFile` and returns aggregated resource list
- [ ] Detects AVM module usage vs raw resource declarations (for AVM compliance check)
- [ ] Detects explicit `depends_on` declarations (for dependency correctness check)
- [ ] Detects `sensitive = true` on variables/outputs (Terraform) and `@secure()` decorators (Bicep)
- [ ] Pure domain function — no external dependencies (regex + string parsing only)
- [ ] Unit tests with sample HCL and Bicep files covering: single resources, modules, nested blocks, AVM modules, sensitive variables

**Tech Details:**
- HCL parsing: regex-based extraction of `resource "type" "name" { ... }` blocks
- Bicep parsing: regex-based extraction of `resource name 'Microsoft.Type/resource@version' = { ... }` blocks
- Does not need to be a full HCL/Bicep parser — focus on extracting resource type, name, tags, and module sources
- This is consumed by `validate_standards()` in the Standards service

---

### Issue #6 — Provision Azure infrastructure via Bicep (InfraAgent self-deployment)

**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 1-4) | **Assignee:** E5
**Labels:** `infrastructure`, `bicep`, `azure`
**Blocks:** #20, #21, #30

**Description:**
Create Bicep modules to deploy all Azure resources InfraAgent needs. This is dogfooding — InfraAgent's own infra is IaC.

**Acceptance Criteria:**
- [ ] `infra/main.bicep` — Root orchestration module
- [ ] `infra/modules/foundry.bicep` — Azure AI Foundry resource + project
- [ ] `infra/modules/postgres.bicep` — Azure PostgreSQL Flexible Server (Burstable B1ms)
- [ ] `infra/modules/appService.bicep` — App Service (B2) for Python backend
- [ ] `infra/modules/staticWebApp.bicep` — Static Web App for React frontend
- [ ] `infra/modules/keyVault.bicep` — Key Vault for secrets (GitHub PAT, API keys) with `enableRbacAuthorization: true`, `enablePurgeProtection: true`, `enableSoftDelete: true`
- [ ] `infra/modules/aiSearch.bicep` — Azure AI Search (Basic) for policy RAG
- [ ] `infra/modules/functionApp.bicep` — Azure Functions (Consumption) for MCP server hosting
- [ ] `infra/modules/monitoring.bicep` — App Insights + Log Analytics workspace
- [ ] `infra/parameters/dev.bicepparam` and `infra/parameters/prod.bicepparam`
- [ ] Managed Identity used for all service-to-service auth
- [ ] All modules validate with `bicep build`

**Tech Details:**
- SKUs per TechSpec Section 12.1 (B2 App Service, B1ms Postgres, Basic AI Search, etc.)
- Estimated cost ~$225-275/month (TechSpec Section 12.2)
- Ref: TechSpec Section 12

---

### Issue #7 — Set up CI/CD pipelines (GitHub Actions)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 2-3) | **Assignee:** E4
**Labels:** `ci-cd`, `devops`
**Depends on:** #1
**Blocks:** #32, #33

**Description:**
Create GitHub Actions workflows for InfraAgent's own CI/CD: linting, testing, and deployment.

**Acceptance Criteria:**
- [ ] `.github/workflows/ci.yml` — Runs on PR: checkout (with `submodules: recursive`), setup Python 3.12 + uv, `uv sync --extra dev`, `ruff check`, `ruff format --check`, `mypy src/`, `pytest tests/unit/ -v`, `pytest tests/integration/ -v -m "not slow"`
- [ ] `.github/workflows/deploy-infra.yml` — Bicep deployment for InfraAgent's Azure resources (manual trigger + on push to `infra/`)
- [ ] `.github/workflows/deploy-app.yml` — Backend Docker build + push to ACR + deploy to App Service. Frontend build + deploy to Static Web Apps
- [ ] All workflows use proper secret references for Azure credentials (`AZURE_CREDENTIALS`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`)

**Tech Details:**
- Use `actions/checkout@v4`, `astral-sh/setup-uv@v4`, `actions/setup-node@v4`
- Backend deploys to App Service via `azure/webapps-deploy@v3`
- Frontend deploys to Static Web Apps via `Azure/static-web-apps-deploy@v1`
- Ref: TechSpec Section 13.1

---

### Issue #8 — Create knowledge wiki repository and wire as git submodule

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 1-3) | **Assignee:** E5
**Labels:** `knowledge-wiki`, `foundation`
**Depends on:** #1
**Blocks:** #9, #22, #23, #30

**Description:**
Create the separate `infraagent-wiki` GitHub repository with the full directory structure defined in PRD Section 8. Wire it into the InfraAgent repo as a git submodule at `knowledge-wiki/`.

**Acceptance Criteria:**
- [ ] Separate GitHub repo `infraagent-wiki` created with structure: `templates/`, `skills/`, `standards/`, `patterns/`
- [ ] `standards/naming.md` — Organization naming conventions matching domain policy defaults
- [ ] `standards/tagging.md` — Required tags matching domain policy defaults
- [ ] `standards/policies.md` — Structural and security policies
- [ ] `skills/general-azure/SKILL.md` — General Azure consulting skill with phase-specific questions, pattern catalogs, readiness checklists
- [ ] `patterns/adr/` — At least one ADR (e.g., `001-mcp-over-direct-api.md`)
- [ ] `.gitmodules` in InfraAgent repo pointing to `infraagent-wiki` at `knowledge-wiki/` path
- [ ] Wiki repo has its own CI that validates template syntax (`terraform validate` / `bicep build`) and checks `metadata.yaml` schema
- [ ] `metadata.yaml` JSON schema defined and documented
- [ ] Submodule pinned to a release tag (e.g., `v0.1.0`)

**Tech Details:**
- Skill files follow structure: metadata header, phase-specific question banks, pattern selection logic, component catalogs, readiness checklists
- Template `metadata.yaml` schema per PRD Section 8.2
- Ref: PRD Section 8, TechSpec Section 7

---

### Issue #9 — Author 3 starter templates for knowledge wiki

**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 2-5) | **Assignee:** E5
**Labels:** `knowledge-wiki`, `templates`, `iac`
**Depends on:** #8
**Blocks:** #30, #38

**Description:**
Create at least 3 pre-validated, AVM-first IaC templates in both Terraform and Bicep for the self-service catalog. These templates must pass `terraform validate` / `bicep build` and conform to organizational standards.

**Acceptance Criteria:**
- [ ] `templates/aks-cluster/` — AKS cluster with managed identity, Azure CNI, monitoring. Terraform + Bicep. `metadata.yaml` with parameters: node_count, vm_size, kubernetes_version, enable_monitoring, network_plugin
- [ ] `templates/3-tier-web-app/` — App Service + SQL Database + VNet with subnets. Terraform + Bicep. `metadata.yaml` with parameters: app_service_sku, sql_tier, region
- [ ] `templates/static-website-cdn/` — Storage Account + CDN + custom domain. Terraform + Bicep. `metadata.yaml` with parameters: cdn_sku, storage_replication
- [ ] All templates use AVM modules where available (e.g., `Azure/avm-res-containerservice-managedcluster/azurerm` for Terraform, `br/public:avm/res/container-service/managed-cluster` for Bicep)
- [ ] All templates have proper `metadata.yaml` per schema (name, description, azure_services, complexity, parameters with validation, tags, version, author)
- [ ] All Terraform templates pass `terraform fmt -check`, `terraform init -backend=false`, `terraform validate`
- [ ] All Bicep templates pass `bicep build`
- [ ] No hardcoded secrets — uses Key Vault, managed identity, `sensitive = true` / `@secure()`
- [ ] Each template has `variables.tf` / `main.bicepparam` with typed, described, alphabetized variables
- [ ] File structure per PRD Section 7.1.3.2

**Tech Details:**
- AVM Terraform modules: `source = "Azure/avm-res-{service}-{resource}/azurerm"` with `version = "~> x.y"`
- AVM Bicep modules: `br/public:avm/res/{service}/{resource}:{version}`
- Ref: PRD Section 7.1.3.1, TechSpec Section 7

---

### Issue #10 — Implement database schema and migrations

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 3-4) | **Assignee:** E4
**Labels:** `backend`, `database`
**Depends on:** #1
**Blocks:** #15, #16, #17, #31

**Description:**
Implement the PostgreSQL database schema from TechSpec Section 9 using SQLAlchemy async ORM with Alembic migrations. Local development uses Docker PostgreSQL (no Azure dependency).

**Acceptance Criteria:**
- [ ] SQLAlchemy async models for: `conversations`, `messages`, `deployments`, `generated_files`, `settings`, `audit_log`
- [ ] Alembic migration for initial schema creation
- [ ] `deployments` table includes all columns: stage, project_type, subscription_id, subscription_context (JSONB), template_name, template_params (JSONB), pr_number, pr_url, pr_branch, plan_output, plan_status, plan_error_category, plan_rework_iteration, apply_status, apply_output, iteration_count, violations (JSONB), diagram_mermaid, target_repo
- [ ] Indexes: `idx_messages_conversation`, `idx_files_deployment`
- [ ] `settings` table is singleton (fixed UUID PK)
- [ ] `audit_log` table for tracking H1/H2 approvals, PR creation, deployment actions
- [ ] Database adapter (`src/infrastructure/adapters/postgres_adapter.py`) with CRUD operations for all tables
- [ ] Docker-compose entry for local PostgreSQL (postgres:16)
- [ ] Integration test for schema creation and basic CRUD

**Tech Details:**
- Use `asyncpg` as the async PostgreSQL driver
- SQLAlchemy 2.0 async style with `AsyncSession`
- UUID primary keys via `gen_random_uuid()`
- JSONB columns for flexible structured data
- Local dev: Docker PostgreSQL, no dependency on Issue #6 (Azure infra)
- Ref: TechSpec Section 9

---

## EPIC 2: Infrastructure Adapters

---

### Issue #11 — Implement Azure OpenAI / ModelRouter LLM adapter

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E1
**Labels:** `backend`, `ai-foundry`, `adapter`
**Depends on:** #4
**Blocks:** #15, #16, #17, #19, #20, #21

**Description:**
Implement the `ILLMCompletionPort` adapter for Azure OpenAI with ModelRouter support. Agents declare task profiles instead of model names; ModelRouter routes to the optimal model.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/azure_openai_adapter.py` implementing `ILLMCompletionPort`
- [ ] `complete()` method sends request with `TaskProfile` for ModelRouter routing
- [ ] `complete_with_tools()` method supports MCP tool calls with automatic execution loop
- [ ] ModelRouter profiles configured: complex-reasoning → GPT-4o, code-generation → GPT-4o, analysis → GPT-4o-mini, fast-lightweight → GPT-4o-mini, orchestration → GPT-4o
- [ ] Fallback model handling if primary is unavailable/rate-limited
- [ ] `model_used` field populated in `LLMResponse` with the actual model selected
- [ ] Token usage tracking in response
- [ ] Retry logic with exponential backoff
- [ ] **SDK verification:** Confirm actual parameter names in the `azure-ai-projects` SDK for ModelRouter. If `model_router_profile` is not available in the SDK version used, fall back to direct model name with a comment noting the gap
- [ ] Integration test with mocked Azure endpoint

**Tech Details:**
- Use `azure-ai-projects` SDK with `AIProjectClient`
- `DefaultAzureCredential` for auth
- ModelRouter configured at Foundry project level per TechSpec Section 5.1
- Ref: TechSpec Section 2.1, PRD Section 6.1.1

---

### Issue #12 — Implement GitHub adapter (ISourceControlPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E4
**Labels:** `backend`, `github`, `adapter`
**Depends on:** #4
**Blocks:** #17, #28, #29, #32

**Description:**
Implement the `ISourceControlPort` adapter for GitHub operations: branch management, file commits, PR creation, and GitHub Actions workflow monitoring.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/github_adapter.py` implementing `ISourceControlPort`
- [ ] `create_branch(repo, branch, base)` — Creates a new branch from base
- [ ] `commit_files(repo, branch, files, message)` — Atomic tree commit of multiple files via Git Data API (avoids rate limits)
- [ ] `create_pr(repo, title, body, head, base)` — Opens PR with structured description, returns `PRResult`
- [ ] `get_pipeline_status(repo, run_id)` — Polls GitHub Actions for plan/apply status, returns `PipelineStatus`
- [ ] `trigger_workflow(repo, workflow, ref, inputs)` — Triggers a GitHub Actions workflow dispatch
- [ ] GitHub PAT loaded from Azure Key Vault (with fallback to env var for local dev)
- [ ] Rate limit handling with exponential backoff
- [ ] Branch naming convention: `infraagent/{title-slug}`
- [ ] Integration test with mocked GitHub API

**Tech Details:**
- Use `httpx` for GitHub REST API v3 (lightweight, async-native)
- Tree commit via Git Data API for atomic multi-file commits
- Ref: TechSpec Section 2.1 (ISourceControlPort)

---

### Issue #13 — Implement Terraform CLI adapter (IInfraProviderPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Labels:** `backend`, `terraform`, `adapter`
**Depends on:** #4
**Blocks:** #15, #24, #32

**Description:**
Implement the `IInfraProviderPort` adapter for Terraform CLI operations: format checking, init, validate, lint, plan, and apply.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/terraform_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — Runs `terraform fmt -check`, returns `ValidationResult`
- [ ] `validate(files)` — Runs `terraform init -backend=false` + `terraform validate`, returns `ValidationResult`. **Must use `-backend=false` flag** to avoid requiring backend config during validation-only runs
- [ ] `lint(files)` — Runs `tflint` (stretch: returns warnings only), returns `ValidationResult`
- [ ] `plan(files, variables)` — Runs `terraform plan -no-color -out=tfplan -json`, returns `PlanResult` with structured resource counts parsed from JSON output
- [ ] `apply(plan_id)` — Runs `terraform apply`, returns `ApplyResult`
- [ ] `get_language()` returns `"terraform"`
- [ ] Files written to a temporary working directory for CLI execution, properly cleaned up
- [ ] Stderr + exit code captured and returned for error categorization
- [ ] Integration test against terraform CLI

**Tech Details:**
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Temp directory per validation run, cleaned up on completion
- Parse `terraform plan -json` output for structured resource counts
- Ref: TechSpec Section 4.2, PRD Section 7.1.4

---

### Issue #14 — Implement Bicep CLI adapter (IInfraProviderPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Labels:** `backend`, `bicep`, `adapter`
**Depends on:** #4
**Blocks:** #15, #24, #32

**Description:**
Implement the `IInfraProviderPort` adapter for Bicep CLI operations: build, format, lint, and deployment.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/bicep_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — Runs `bicep format --verify`, returns `ValidationResult`
- [ ] `validate(files)` — Runs `bicep build --stdout --no-restore`, returns `ValidationResult`
- [ ] `lint(files)` — Runs Bicep linter rules, returns `ValidationResult`. Triage logic: BCP081 (type not defined) ignored if API version confirmed; BCP035 (missing property) checked and reported; BCP187 (SKU/kind unverified) ignored
- [ ] `plan(files, variables)` — Runs `az deployment group what-if`, returns `PlanResult`
- [ ] `apply(plan_id)` — Runs `az deployment group create`, returns `ApplyResult`
- [ ] `get_language()` returns `"bicep"`
- [ ] Proper lint warning triage per PRD Section 7.1.4
- [ ] Integration test against bicep CLI

**Tech Details:**
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Bicep lint triage documented in acceptance criteria
- Ref: PRD Section 7.1.4, TechSpec Section 4.2

---

### Issue #15 — Implement Template Registry adapter (ITemplateRegistryPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 4-5) | **Assignee:** E5
**Labels:** `backend`, `adapter`, `knowledge-wiki`
**Depends on:** #4, #8
**Blocks:** #16, #17, #30

**Description:**
Implement the `ITemplateRegistryPort` adapter that reads templates from the knowledge wiki git submodule, supports keyword search, hydrates templates with parameters and org standards, and publishes new templates.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/template_registry_adapter.py` implementing `ITemplateRegistryPort`
- [ ] `search(query, filters)` — Keyword search against `metadata.yaml` fields (name, description, azure_services, tags). Supports filtering by complexity and iac_language. Returns `list[TemplateMetadata]`
- [ ] `get_template(name, language)` — Returns full template content (all files) for a given template name and IaC language
- [ ] `hydrate(name, language, parameters, standards)` — Loads template files, substitutes user parameters, applies org-level standards (naming conventions, required tags), returns `HydratedTemplate` with all files ready for validation
- [ ] `publish(template, metadata)` — Prepares a new template for PR submission to the wiki repo (used by Template Curation Agent)
- [ ] Templates loaded from `knowledge-wiki/templates/*/metadata.yaml` at runtime
- [ ] Caches template metadata at startup for fast search
- [ ] Unit tests with sample template fixtures

**Tech Details:**
- Reads from git submodule path at runtime
- Hydration replaces parameter placeholders in template files with user-provided values
- Org standards (naming, tags) are injected during hydration based on Standards Agent rules
- Ref: TechSpec Section 2.1 (ITemplateRegistryPort), PRD Section 8

---

### Issue #16 — Implement Policy adapter (IPolicyEnginePort)

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 4-5) | **Assignee:** E2
**Labels:** `backend`, `adapter`
**Depends on:** #3, #4, #5
**Blocks:** #17, #23, #24

**Description:**
Implement the `IPolicyEnginePort` adapter that bridges domain policy rules (naming, tagging) with the IaC parser and external security scanning tools (tfsec, Checkov). This adapter is the enforcement layer that the Standards and Security agents call.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/policy_adapter.py` implementing `IPolicyEnginePort`
- [ ] `validate_naming(files)` — Parses IaC files via `iac_parser`, runs `validate_resource_name()` domain function against each resource, returns `PolicyResult`
- [ ] `validate_tags(files)` — Parses IaC files, runs `validate_tags()` domain function, returns `PolicyResult`
- [ ] `validate_security(files)` — Runs tfsec/Checkov CLI as subprocess, parses JSON output, maps findings to `PolicyViolation` with severity, resource, remediation. Returns `PolicyResult`
- [ ] `check_avm_availability(resource_type)` — Checks if an AVM module exists for the given resource type. Returns boolean + module source if available (used by Standards Agent for AVM compliance check)
- [ ] Security tool CLI invocation with proper temp directory handling and cleanup
- [ ] Severity mapping: tfsec/Checkov CRITICAL/HIGH → "error"; MEDIUM/LOW → "warning"
- [ ] Unit tests with sample IaC containing known violations

**Tech Details:**
- Consumes domain policies from `naming_policy.py` and `tagging_policy.py`
- Consumes `iac_parser.py` for resource extraction
- tfsec: `tfsec --format=json --no-color <dir>`
- Checkov: `checkov -d <dir> -o json`
- AVM availability check: maintain a mapping of known AVM modules or query via MCP at runtime
- Ref: TechSpec Section 2.2 composition root instantiates `PolicyAdapter(standards_repo=...)`

---

### Issue #17 — Implement Subscription Discovery adapter (ISubscriptionDiscoveryPort)

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E1
**Labels:** `backend`, `adapter`, `azure`
**Depends on:** #4, #22
**Blocks:** #19, #36

**Description:**
Implement the `ISubscriptionDiscoveryPort` adapter that connects to Azure subscriptions via Azure MCP Server to inventory existing resources, VNets, naming patterns, quotas, and state backends.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/subscription_discovery_adapter.py` implementing `ISubscriptionDiscoveryPort`
- [ ] `discover(subscription_id)` returns `SubscriptionContext` with:
  - `subscription_id`, `subscription_name`
  - `resource_groups` — List of existing resource groups
  - `resources` — List of `DiscoveredResource` (resource_group, type, name, location, tags)
  - `vnets` — List of `DiscoveredVNet` (name, resource_group, address_space, subnets with address_prefix)
  - `naming_patterns` — Detected patterns (e.g., "rg-{env}-{app}-{region}") inferred from existing resource names
  - `quotas` — Resource type quotas with used/limit
  - `state_backends` — Detected Terraform state storage accounts
  - `available_regions` — Available Azure regions
- [ ] `check_sku_availability(subscription_id, resource_type, sku, region)` — Validates SKU availability
- [ ] `check_quota(subscription_id, resource_type, region)` — Returns quota usage
- [ ] Uses Azure MCP Server for all queries
- [ ] Naming pattern detection: regex inference from existing resource names (group resources by type, find common prefix/suffix patterns)
- [ ] All discovery data is point-in-time — surfaces timestamps
- [ ] Integration test with mocked Azure MCP responses

**Tech Details:**
- Azure MCP tools: listResourceGroups, listResources, getVNetTopology, checkQuotas
- Naming pattern detection: group resources by type, find common prefixes/patterns, generate template strings
- Ref: TechSpec Section 2.1 (ISubscriptionDiscoveryPort), PRD Section 7.1.1

---

## EPIC 3: Application Layer — Use Cases

---

### Issue #18 — Implement ConsultUseCase

**Priority:** P0 | **Size:** L | **Week:** 1-2 (Day 4-7) | **Assignee:** E1
**Labels:** `backend`, `use-case`, `consulting-agent`
**Depends on:** #2, #4, #11
**Blocks:** #19, #36

**Description:**
Implement the ConsultUseCase that drives the Consulting Agent's multi-turn requirements gathering conversation, including project type classification, knowledge wiki search, and template recommendations. Subscription discovery is wired in when the adapter is available but stubbed initially.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/consult.py` with `ConsultUseCase` class
- [ ] Constructor injection of `ILLMCompletionPort`, `ITemplateRegistryPort`, `ISubscriptionDiscoveryPort` (optional — stubbed if not available), `IObservabilityPort`
- [ ] `run()` method: processes one conversation turn — builds system prompt with domain skill, searches wiki for templates, calls LLM with ModelRouter profile `complex-reasoning`, parses response for routing signals
- [ ] Project type extraction via `[PROJECT_TYPE:X]` markers in LLM response
- [ ] Template recommendation via `[RECOMMEND_TEMPLATE:name]` markers
- [ ] Requirements completion via `[REQUIREMENTS_COMPLETE]` marker
- [ ] Subscription discovery when `subscription_id` is provided — calls `ISubscriptionDiscoveryPort.discover()`, formats context into system prompt
- [ ] `ConsultResult` returned with: response, recommended_template, recommended_path ("catalog" or "custom"), requirements_complete, project_type, subscription_context
- [ ] Unit tests with mocked ports (including stubbed subscription discovery)

**Tech Details:**
- System prompt built dynamically with domain skill context and subscription context
- Template matches appended to user message as system context
- ModelRouter task profile: `complex-reasoning`
- Ref: TechSpec Section 4.1

---

### Issue #19 — Implement GenerateUseCase (custom + catalog paths)

**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 5-9) | **Assignee:** E2
**Labels:** `backend`, `use-case`, `codegen-agent`
**Depends on:** #2, #4, #11, #13, #14
**Blocks:** #24, #25, #36

**Description:**
Implement the GenerateUseCase with both the custom generation pipeline (CodeGen + IaC Validation + Standards + Security + Diagram) and the catalog fast-path (hydrate + validate). Includes the maker-checker loop (max 3 iterations) and diagram generation.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/generate.py` with `GenerateUseCase` class
- [ ] `run_custom_path()` — Full pipeline: CodeGen (AVM-first) → IaC Validation Pipeline (fmt/validate/lint) → Standards → Security → Diagram generation. Loops on violations, max 3 iterations total across all checkers
- [ ] `run_catalog_path()` — Template hydration + syntax validation only (no iterative loops)
- [ ] `_run_iac_validation_pipeline()` — Deterministic toolchain: format_check → validate → lint. Not LLM-based. Runs BEFORE standards/security
- [ ] `_generate_code()` — Calls LLM with MCP tools, AVM-first strategy enforced in prompt, secret handling rules included
- [ ] `_generate_diagram()` — Lightweight LLM call (profile: `fast-lightweight`) to produce Mermaid architecture diagram from IaC code
- [ ] `_build_codegen_prompt()` — Dynamic prompt with: AVM-first rules, secret handling, file structure conventions, project type WAF depth, subscription context, prior violations
- [ ] `FILE_STRUCTURE_TERRAFORM` and `FILE_STRUCTURE_BICEP` constants for code structure conventions
- [ ] `SECRET_HANDLING_RULES` list enforced in code generation
- [ ] `MAX_MAKER_CHECKER_ITERATIONS = 3`
- [ ] `GenerateResult` with: files, standards_passed, security_passed, violations, iteration_count, diagram_mermaid, assistant_message
- [ ] Unit tests with mocked ports for both paths

**Tech Details:**
- Validation pipeline runs BEFORE LLM-based checks (standards, security)
- Violation feedback format: `{ checker, severity, resource, file, line, message, remediation }`
- CodeGen receives last 5 violations for rework context
- Ref: TechSpec Section 4.2, PRD Sections 7.1.3, 7.1.4, 6.2.1

---

### Issue #20 — Implement DeployUseCase

**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 5-7) | **Assignee:** E4
**Labels:** `backend`, `use-case`, `deploy-agent`
**Depends on:** #2, #4, #12
**Blocks:** #28, #29, #36

**Description:**
Implement the DeployUseCase that handles PR creation, plan monitoring, plan failure categorization, and deployment triggering via GitHub Actions.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/deploy.py` with `DeployUseCase` class
- [ ] `create_pr(repo, files, title, body, base_branch)` — Creates branch (`infraagent/{slug}`), commits files atomically, opens PR with structured description
- [ ] `get_plan_status(repo, run_id)` — Polls GitHub Actions for plan/apply status
- [ ] `trigger_apply(repo, workflow, ref, inputs)` — Triggers `terraform apply` / `az deployment create` workflow
- [ ] `categorize_plan_failure(stderr, exit_code)` — Categorizes plan errors into: resource_conflict, sku_unavailable, quota_exceeded, auth_failure, provider_mismatch, module_error, unknown. Determines if fixable in code. Returns `PlanFailureAnalysis`
- [ ] `PlanFailureAnalysis` dataclass: category, error_message, stderr, exit_code, is_fixable_in_code, suggested_fix
- [ ] `MAX_PLAN_REWORK_ITERATIONS = 2`
- [ ] Observability metrics: `prs_created`, `deployments_triggered`
- [ ] Unit tests with mocked ports + plan failure categorization tests

**Tech Details:**
- Branch naming: `infraagent/{title-lowercase-slugified[:50]}`
- PR body includes: resources created, standards applied, security scan results
- Plan failure categorization logic per PRD Section 6.2.1 plan failure table
- Ref: TechSpec Section 4.3, PRD Section 7.1.8

---

## EPIC 4: Agent Definitions & Orchestration

---

### Issue #21 — Write agent system prompts (all 8 agents)

**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 3-8) | **Assignee:** E2 (CodeGen/Standards/Security prompts) + E1 (Consulting/Orchestrator/Deploy/PR/Curation prompts)
**Labels:** `agents`, `prompts`
**Depends on:** #8, #13, #14
**Blocks:** #22

**Description:**
Write comprehensive system prompts for all 8 agents. These are the `instructions` field in the Foundry agent definitions. Prompts are version-controlled markdown files.

**Assignment split:**
- **E2:** `codegen_agent_terraform.md`, `codegen_agent_bicep.md`, `standards_agent.md`, `security_agent.md`
- **E1:** `orchestrator.md`, `consulting_agent.md`, `pr_workflow_agent.md`, `deploy_agent.md`, `template_curation_agent.md`

**Acceptance Criteria:**
- [ ] `src/prompts/orchestrator.md` — Routing, lifecycle management, pipeline enforcement
- [ ] `src/prompts/consulting_agent.md` — Multi-turn requirements gathering, project type classification (`[PROJECT_TYPE:X]`), subscription discovery surfacing, template recommendation (`[RECOMMEND_TEMPLATE:name]`), requirements completion (`[REQUIREMENTS_COMPLETE]`). Includes domain skill loading instructions
- [ ] `src/prompts/codegen_agent_terraform.md` — Terraform HCL generation with AVM-first rules, MCP tool usage, secret handling, file structure conventions, violation rework, subscription context awareness
- [ ] `src/prompts/codegen_agent_bicep.md` — Bicep generation with AVM-first rules, `@secure()` decorator, file structure conventions, MCP tool usage
- [ ] `src/prompts/standards_agent.md` — Naming, tagging, structural validation, AVM compliance check, dependency correctness, file structure validation
- [ ] `src/prompts/security_agent.md` — tfsec/Checkov invocation, severity classification, remediation guidance
- [ ] `src/prompts/pr_workflow_agent.md` — Branch creation, PR description formatting, diagram commit, CI/CD workflow creation
- [ ] `src/prompts/deploy_agent.md` — Plan execution, error categorization (all 6 categories), rework routing, apply monitoring, rollback guidance
- [ ] `src/prompts/template_curation_agent.md` — Post-deploy analysis, novelty check, generalization (P1)
- [ ] Each prompt is 200-500 lines with clear behavioral rules and output format specifications
- [ ] All prompts specify JSON output format in markdown fences

**Tech Details:**
- Consulting agent must output structured markers for routing signals
- CodeGen prompt dynamically extended by GenerateUseCase with AVM rules, secret handling, WAF depth, subscription context, prior violations
- Ref: TechSpec Appendix A

---

### Issue #22 — Configure MCP server connections

**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 4-6) | **Assignee:** E1
**Labels:** `backend`, `mcp`, `integration`
**Depends on:** #6
**Blocks:** #17, #23

**Description:**
Configure connections to the 4 MCP servers (Terraform, Bicep, Azure, GitHub) used for grounding agent code generation and operations.

**Acceptance Criteria:**
- [ ] `src/infrastructure/mcp/config.py` with `MCPServerConfig` dataclass and `MCP_SERVERS` dictionary
- [ ] Terraform MCP connection (hashicorp/terraform-mcp-server) — tools: search_providers, get_provider_details, search_modules, get_module_details, resourceUsage
- [ ] Bicep MCP connection — tools: get_az_resource_type_schema, get_bicep_best_practices, list_avm_metadata, format_bicep_file, diagnostics
- [ ] Azure MCP connection (microsoft/mcp) — tools: resource management, subscription info, quota checks, VNet topology
- [ ] GitHub MCP connection (github/github-mcp-server) — tools: create_branch, commit_files, create_pull_request, workflow operations
- [ ] `src/infrastructure/mcp/tool_adapter.py` — MCP tool → Foundry tool conversion utility
- [ ] Auth per server: API key or Entra ID (values from Key Vault or env vars)
- [ ] Connection health check with graceful degradation when MCP unavailable
- [ ] `.vscode/mcp.json` configured for local development
- [ ] **Graceful degradation:** When MCP server is unavailable, agents fall back to plain LLM generation with a warning flag that output is ungrounded

**Tech Details:**
- MCP servers hosted on Azure Functions or Azure Container Apps for remote deployment
- Foundry-hosted agents require remote HTTP (not localhost/stdio) — 100-second timeout
- Ref: TechSpec Section 6, PRD Section 9

---

### Issue #23 — Register agents with Azure AI Foundry Agent Service

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E1
**Labels:** `backend`, `ai-foundry`, `agents`
**Depends on:** #6, #11, #21, #22
**Blocks:** #25, #26

**Description:**
Implement the agent registry that registers all 8 agents with Azure AI Foundry as Hosted Agents with ModelRouter task profiles and MCP tool bindings.

**Acceptance Criteria:**
- [ ] `src/infrastructure/agents/registry.py` with `AGENT_CONFIGS` dictionary defining all 8 agents
- [ ] Each agent config specifies: `task_profile` (for ModelRouter), `instructions_file` path, `tools` list (MCP and Function tools)
- [ ] `register_agents()` async function creates/updates all agents in Foundry
- [ ] ModelRouter profiles: orchestrator→orchestration, consulting→complex-reasoning, codegen→code-generation, standards→analysis, security→fast-lightweight, pr_workflow→fast-lightweight, deploy→complex-reasoning, template_curation→code-generation
- [ ] MCP tool bindings: consulting→Azure MCP, codegen→Terraform+Bicep+Azure MCP, standards→GitHub MCP, security→tfsec+Checkov function tools, pr_workflow→GitHub MCP, deploy→GitHub+Azure MCP, template_curation→GitHub MCP
- [ ] `_build_mcp_tools(agent_name)` auto-wires MCP servers from env vars with graceful degradation (warning logged if unavailable)
- [ ] Uses `DefaultAzureCredential` and Foundry `AIProjectClient`
- [ ] **Fallback plan:** If Foundry Agent Service has limitations, document path to using custom orchestration code with Foundry hosted agents directly

**Tech Details:**
- `PromptAgentDefinition` with `model_router_profile` (verify SDK parameter name; fall back to direct model name if needed)
- MCP tools use `MCPTool(server_label=..., server_url=..., require_approval="never")`
- Security agent uses `FunctionTool` for tfsec/Checkov
- Ref: TechSpec Section 5.1

---

### Issue #24 — Implement IaC Validation Pipeline (deterministic, non-LLM)

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E2
**Labels:** `backend`, `validation`, `pipeline`
**Depends on:** #13, #14, #19
**Blocks:** #36

**Description:**
Implement the deterministic IaC validation pipeline as a function tool chain invoked by the orchestrator. This is NOT an agent — it runs `terraform fmt/init/validate/tflint` or `bicep build/format/lint` without any LLM involvement.

**Acceptance Criteria:**
- [ ] Terraform chain: `fmt -check` (auto-fix with `terraform fmt`, non-blocking) → `init -backend=false` (blocking) → `validate` (blocking) → `tflint` (stretch, warnings only)
- [ ] Bicep chain: `build --stdout --no-restore` (blocking) → `format` (non-blocking, auto-format) → lint with triage (conditional — errors block, triaged warnings pass)
- [ ] Format failures auto-fixed without CodeGen rework
- [ ] Init/validate/build failures produce structured error output fed back to CodeGen
- [ ] Lint warnings attached to H1 review as informational (not blocking)
- [ ] Bicep lint triage: BCP081 ignored, BCP035 checked, BCP187 ignored
- [ ] Returns `{"passed": bool, "errors": list[str], "warnings": list[str]}`
- [ ] Integrated into GenerateUseCase `_run_iac_validation_pipeline()` (runs BEFORE standards/security)
- [ ] Shared retry counter: validation + standards + security = max 3 iterations total
- [ ] Unit tests for each chain step with sample pass/fail files

**Tech Details:**
- Called by orchestrator between CodeGen and Standards nodes
- Uses `IInfraProviderPort.format_check()`, `.validate()`, `.lint()`
- Ref: PRD Section 7.1.4, TechSpec Section 4.2

---

### Issue #25 — Implement orchestrator workflow (chat path)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 7-10) | **Assignee:** E1
**Labels:** `backend`, `orchestrator`, `agents`
**Depends on:** #18, #19, #20, #23
**Blocks:** #36, #39

**Description:**
Implement the graph-based orchestrator for the chat path using the Microsoft Agent Framework. This is the central coordination workflow: Consult → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy, with maker-checker loops and plan-failure rework.

**Acceptance Criteria:**
- [ ] `src/infrastructure/agents/orchestrator.py` with `build_chat_path_workflow()` function
- [ ] `AgentWorkflow` with all nodes: consult, subscription_discovery, codegen, iac_validation (agent_name=None — deterministic), standards, security, diagram_gen, h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] `HumanApprovalNode` for H1 (code + diagram review) and H2 (plan review)
- [ ] **Maker-checker loop (Loop 1):** ConditionalEdge from security → codegen if violations_fixable AND iteration < 3; → diagram if passed or max_iterations
- [ ] **IaC validation loop:** ConditionalEdge from iac_valid → standards if passed; → codegen if failed (feeds structured errors back)
- [ ] **Plan-failure rework (Loop 2):** ConditionalEdge from plan → h2_gate if success; → codegen if failed_fixable (max 2×); → h2_gate with error if failed_escalate (quota, auth)
- [ ] Checkpointing enabled for durable long-running workflows
- [ ] Context sharing between agents (requirements handoff, subscription context, violation feedback, plan failure analysis)
- [ ] Real-time stage updates emitted as events (consumed by API layer for SSE)

**Tech Details:**
- Use `agent_framework.AgentWorkflow`, `AgentNode`, `HumanApprovalNode`, `ConditionalEdge`
- `iac_validation` node has `agent_name=None` (deterministic, not LLM)
- `diagram_gen` uses codegen agent in diagram mode
- Ref: TechSpec Section 5.2

---

### Issue #26 — Implement orchestrator workflow (catalog path)

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-9) | **Assignee:** E1
**Labels:** `backend`, `orchestrator`, `agents`
**Depends on:** #19, #20, #23
**Blocks:** #38, #39

**Description:**
Implement the graph-based orchestrator for the catalog path. Simpler workflow: Template hydrate → IaC Validation → H1 → PR → Plan → H2 → Deploy. No consulting, no iterative codegen/standards/security loops.

**Acceptance Criteria:**
- [ ] `build_catalog_path_workflow()` function in orchestrator.py
- [ ] Nodes: hydrate (codegen in hydrate mode), iac_validation (syntax check only — Steps 1-3 TF, Steps 1-2 Bicep), h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] No maker-checker loop (templates are pre-validated at H3 time)
- [ ] H1 and H2 human gates functional
- [ ] Context: template parameters + org standards passed through pipeline

**Tech Details:**
- Templates skip standards/security agents (pre-validated)
- Validation is syntax-only (no lint/tflint for catalog path)
- Ref: TechSpec Section 5.2 (`build_catalog_path_workflow`)

---

## EPIC 5: Agent Implementation

---

### Issue #27 — Implement Standards Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E2
**Labels:** `backend`, `agents`, `standards`
**Depends on:** #3, #5, #16, #19
**Blocks:** #36

**Description:**
Implement the Standards Agent's validation logic combining domain policy rules with LLM-based structural analysis. Validates naming, tagging, AVM compliance, dependency correctness, and file structure.

**Acceptance Criteria:**
- [ ] Naming validation via domain `validate_resource_name()` against org naming rules (uses IaC parser for resource extraction)
- [ ] Tagging validation via domain `validate_tags()` against required tags
- [ ] **AVM compliance check:** Flags raw `azurerm_` resources (Terraform) or native Bicep resource declarations when an equivalent AVM module exists. Uses `check_avm_availability()` from policy adapter
- [ ] **Dependency correctness:** Detects redundant `depends_on` where dependency is implicit through resource references (uses IaC parser)
- [ ] **File structure validation:** Verifies generated code follows conventions from PRD Section 7.1.3.2 (correct file names, alphabetized variables, etc.)
- [ ] Produces structured violation reports: `{ checker: "standards", severity, resource, file, line, message, remediation }`
- [ ] Only `severity: "error"` findings trigger rework loop; warnings and info are passed through
- [ ] Policy RAG integration via Azure AI Search for loading policies from standards repo (stretch — falls back to direct file read)
- [ ] Unit tests with sample IaC code containing naming violations, missing tags, raw resources where AVM exists

**Tech Details:**
- Uses `IPolicyEnginePort.validate_naming()` and `.validate_tags()`
- Standards loaded from `knowledge-wiki/standards/` at runtime
- AVM check: if resource_type matches `azurerm_*` and AVM exists → flag with recommendation
- Ref: PRD Section 7.1.5

---

### Issue #28 — Implement Security Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-10) | **Assignee:** E2
**Labels:** `backend`, `agents`, `security`
**Depends on:** #16, #19
**Blocks:** #36

**Description:**
Implement the Security Agent that runs tfsec and Checkov static analysis on generated IaC code and produces structured finding reports.

**Acceptance Criteria:**
- [ ] tfsec integration for Terraform code — runs via policy adapter, parses structured findings
- [ ] Checkov integration for Terraform code — runs via policy adapter, parses structured findings
- [ ] Bicep security validation via `bicep build` diagnostics + equivalent checks
- [ ] Produces structured finding reports: `{ checker: "security", severity, resource, file, line, message, remediation }`
- [ ] Critical/high findings trigger rework loop; medium/low are informational (passed to H1 review)
- [ ] Findings fed back to CodeGen as part of Loop 1
- [ ] tfsec/Checkov run locally via CLI for hackathon (Azure Functions hosting is stretch)
- [ ] Uses `IPolicyEnginePort.validate_security()`
- [ ] Unit tests with known-vulnerable IaC samples (public blob access, missing encryption, open NSG rules)

**Tech Details:**
- Severity mapping: CRITICAL/HIGH → "error" (triggers retry); MEDIUM/LOW → "warning" (informational)
- Ref: PRD Section 7.1.6

---

### Issue #29 — Implement PR Workflow Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E4
**Labels:** `backend`, `agents`, `github`
**Depends on:** #12, #20
**Blocks:** #36

**Description:**
Implement the PR Workflow Agent that creates branches, commits generated IaC files, and opens PRs with structured descriptions. Also handles creating CI/CD workflow files in the target repo.

**Acceptance Criteria:**
- [ ] Creates feature branch: `infraagent/{title-slug}`
- [ ] Commits all generated IaC files atomically (single tree commit via Git Data API)
- [ ] Commits auto-generated Mermaid diagram file to `/docs/architecture/` in the repo
- [ ] Opens PR with structured body: summary of resources created, standards applied, security scan results, diagram preview link
- [ ] Returns `PRResult` with number, url, html_url, state, branch_name
- [ ] Monitors CI/CD pipeline status via GitHub MCP Server / GitHub API

**Tech Details:**
- PR body template: resources list, standards status, security status, diagram preview
- Ref: PRD Section 7.1.7

---

### Issue #30 — Author CI/CD workflow templates for generated IaC repos

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E4
**Labels:** `backend`, `github`, `ci-cd`
**Depends on:** #12
**Blocks:** #29, #32

**Description:**
Create the GitHub Actions workflow template files that the PR Workflow Agent commits to the target repo if they don't exist. These handle plan/apply for both Terraform and Bicep.

**Acceptance Criteria:**
- [ ] `terraform-plan.yml` template — Triggered on PR to `terraform/**`: checkout, setup-terraform, `terraform init`, `terraform validate`, `terraform plan -no-color -out=tfplan`, post plan output as PR comment
- [ ] `terraform-apply.yml` template — Triggered on workflow_dispatch (from Deploy Agent): `terraform apply`, report status
- [ ] `bicep-whatif.yml` template — Triggered on PR to `infra/**`: checkout, `az deployment group what-if`, post output as PR comment
- [ ] `bicep-deploy.yml` template — Triggered on workflow_dispatch: `az deployment group create`, report status
- [ ] All workflows use proper ARM auth secrets: `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`
- [ ] Plan output posted as PR comment via `actions/github-script@v7`
- [ ] Templates stored in `src/infrastructure/templates/workflows/` and committed by PR Workflow Agent when target repo lacks them

**Tech Details:**
- Ref: TechSpec Section 13.2

---

### Issue #31 — Implement Deploy Agent logic (plan/apply + rework loop)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 8-10) | **Assignee:** E4
**Labels:** `backend`, `agents`, `deploy`
**Depends on:** #12, #20
**Blocks:** #36, #39

**Description:**
Implement the Deploy Agent that triggers terraform plan/apply via GitHub Actions, monitors progress, and integrates with the plan-failure rework loop (Loop 2).

**Acceptance Criteria:**
- [ ] Triggers `terraform plan` / `bicep what-if` via GitHub Actions workflow dispatch
- [ ] Polls GitHub Actions for pipeline completion (plan/apply status) with timeout
- [ ] Surfaces plan output to user for H2 review
- [ ] **Plan failure handling:** Extracts full error output (stderr + exit code), calls `categorize_plan_failure()` from DeployUseCase:
  - resource_conflict → fixable in code
  - sku_unavailable → fixable in code (query Azure MCP for alternatives)
  - quota_exceeded → escalate to user (not fixable in code)
  - auth_failure → escalate to user (not fixable in code)
  - provider_mismatch → fixable in code
  - module_error → fixable in code
- [ ] On fixable failure: routes back to CodeGen with error context via orchestrator (Loop 2, max 2 iterations)
- [ ] On non-fixable failure: escalates to user at H2 gate with plan output + analysis
- [ ] On apply success: reports deployment status
- [ ] On apply failure: captures partial state info, provides rollback guidance
- [ ] Monitors deployment progress and reports real-time status updates

**Tech Details:**
- Plan rework loop: full plan error → DeployUseCase categorizes → orchestrator routes to CodeGen → re-enter validation pipeline (Loop 1) → new PR → re-plan
- Loop 2 max iterations = 2
- Ref: PRD Section 7.1.8, TechSpec Section 4.2

---

## EPIC 6: Backend API Layer

---

### Issue #32 — Implement chat API endpoints + WebSocket streaming

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-10) | **Assignee:** E1
**Labels:** `backend`, `api`, `chat`
**Depends on:** #10, #18, #25
**Blocks:** #36

**Description:**
Implement the FastAPI routes and WebSocket endpoint for the chat interface: sending messages, receiving streaming responses, and handling human gate approvals.

**Acceptance Criteria:**
- [ ] `src/api/routes/chat.py` with routes:
  - `POST /api/chat` — Send message to consulting/codegen agents. Returns SSE stream with events: `assistant_message`, `stage_change`, `subscription_context`, `files_generated`, `approval_required`
  - `POST /api/chat/{conversation_id}/approve` — Human gate approval (H1 or H2) with optional comment
  - `POST /api/chat/{conversation_id}/reject` — Human gate rejection with feedback text
  - `WS /ws/chat/{conversation_id}` — WebSocket for real-time streaming of chat + pipeline status
- [ ] `POST /api/pipeline/start` — Starts pipeline as background task, returns immediately
- [ ] `GET /api/pipeline/status/{session_id}` — Polls pipeline state (stage, iteration, PR URL, plan output, etc.)
- [ ] `POST /api/pipeline/approve/h1` and `POST /api/pipeline/approve/h2` — Human gate approval endpoints per API reference
- [ ] `src/api/schemas/chat.py` — Pydantic models for request/response/SSE events
- [ ] SSE event types match TechSpec Section 8.2: assistant_message, stage_change, subscription_context, files_generated, approval_required, deployment_status, plan_failure, deployment_complete
- [ ] Conversation persistence to database (create/retrieve)
- [ ] Message persistence to database
- [ ] Stage transitions emit real-time events

**Tech Details:**
- Use FastAPI `StreamingResponse` with `text/event-stream` for SSE
- WebSocket as alternative real-time transport
- Conversation ID auto-generated if not provided
- Ref: TechSpec Section 8.1, 8.2, api-reference.md

---

### Issue #33 — Implement catalog API endpoints

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E4
**Labels:** `backend`, `api`, `catalog`
**Depends on:** #8, #9, #10, #15
**Blocks:** #38

**Description:**
Implement the FastAPI routes for the self-service catalog: listing templates, getting template details, and deploying templates.

**Acceptance Criteria:**
- [ ] `src/api/routes/catalog.py` with routes:
  - `GET /api/catalog` — List templates from knowledge wiki with keyword search + optional filters (complexity, iac_language). Returns `TemplateMetadata[]`
  - `GET /api/catalog/{name}` — Get template details + full parameter schema with validation rules
  - `POST /api/catalog/{name}/deploy` — Deploy a catalog template (accepts parameters, iac_language, target_repo, subscription_id). Returns deployment_id + session_id for tracking
- [ ] `src/api/schemas/catalog.py` — Pydantic request/response models
- [ ] Template search reads from `ITemplateRegistryPort.search()`
- [ ] Deploy endpoint triggers the catalog path workflow (Issue #26)
- [ ] Returns 404 for unknown templates, 400 for missing/invalid parameters

**Tech Details:**
- Search by keyword matches against name, description, azure_services, tags in metadata.yaml
- Ref: TechSpec Section 8.1, 8.2, api-reference.md

---

### Issue #34 — Implement deployment + health + standards API endpoints

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-10) | **Assignee:** E4
**Labels:** `backend`, `api`
**Depends on:** #10, #12
**Blocks:** #39

**Description:**
Implement the FastAPI routes for deployment tracking, health checks, and standards viewing.

**Acceptance Criteria:**
- [ ] `src/api/routes/deployments.py`:
  - `GET /api/deployments/{id}` — Full deployment status (stage, PR info, plan status, file count, diagram URL, timestamps, plan_error_category, rework_iteration)
  - `GET /api/deployments/{id}/plan` — Plan output text
  - `GET /api/deployments/{id}/files` — List of generated files with content
  - `GET /api/deployments/{id}/diagram` — Architecture diagram (Mermaid source + SVG URL)
- [ ] `src/api/routes/health.py`:
  - `GET /api/health` — Health check (no auth): backend status, DB connectivity, Foundry connectivity, MCP server reachability
- [ ] `src/api/routes/standards.py`:
  - `GET /api/standards` — Load current org standards (naming rules, tag rules) from knowledge wiki
- [ ] `src/api/middleware/cors.py` — CORS configuration via `CORS_ORIGINS` env var
- [ ] `src/api/middleware/auth.py` — JWT / Entra ID auth middleware (optional for hackathon, required post-hackathon). Stub that passes all requests through with TODO comment
- [ ] Deployment stages match `DeploymentStage` enum
- [ ] Pydantic response models in `src/api/schemas/deployment.py`

**Tech Details:**
- Standards loaded from `knowledge-wiki/standards/` at runtime
- Ref: TechSpec Section 8.1, 8.2, api-reference.md

---

### Issue #35 — Implement composition root and dependency injection

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E1
**Labels:** `backend`, `architecture`
**Depends on:** #11, #12, #13, #14, #15, #16, #17, #18, #19, #20
**Blocks:** #32, #36

**Description:**
Implement the composition root (`src/main.py`) that wires all adapters, use cases, and routes together via constructor injection. No use case or adapter should directly import another — all wiring happens here.

**Acceptance Criteria:**
- [ ] `src/main.py` with `create_app()` function
- [ ] All infrastructure adapters instantiated: AzureOpenAIAdapter, TerraformAdapter, BicepAdapter, GitHubAdapter, PolicyAdapter, TemplateRegistryAdapter, SubscriptionDiscoveryAdapter, OpenTelemetryAdapter, PostgresAdapter
- [ ] `infra_providers` dict: `{"terraform": terraform_adapter, "bicep": bicep_adapter}`
- [ ] Use cases instantiated with port injection: `ConsultUseCase(llm=, templates=, subscription_discovery=, observability=)`, `GenerateUseCase(llm=, policy=, templates=, infra_providers=, observability=)`, `DeployUseCase(github=, infra_providers=, observability=)`
- [ ] FastAPI app created with all routes registered
- [ ] Configuration loaded from `src/config.py` (env vars, Key Vault references)
- [ ] **Architectural invariant:** No domain or application layer module imports infrastructure directly
- [ ] Startup validation: checks required env vars, tests DB connection, logs MCP server availability

**Tech Details:**
- Configuration via environment variables with Key Vault references for secrets
- Ref: TechSpec Section 2.2

---

## EPIC 7: Frontend

---

### Issue #36 — Scaffold frontend with Next.js + Tailwind + shadcn/ui

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E3
**Labels:** `frontend`, `foundation`
**Depends on:** #1
**Blocks:** #37, #38, #39, #40

**Description:**
Initialize the React/Next.js frontend with TypeScript, Tailwind CSS, and shadcn/ui component library. Set up routing, global state management, API client, and WebSocket client.

**Acceptance Criteria:**
- [ ] `frontend/` directory with Next.js 15+ app router
- [ ] TypeScript + Tailwind CSS + shadcn/ui configured
- [ ] Route structure: `/` (landing), `/chat`, `/chat/:conversationId`, `/catalog`, `/catalog/:templateName`, `/deployments/:id`, `/settings`
- [ ] `frontend/src/lib/api.ts` — Backend API client (fetch-based with error handling, configurable base URL via `NEXT_PUBLIC_API_URL`)
- [ ] `frontend/src/lib/ws.ts` — WebSocket client for real-time streaming with reconnection and exponential backoff
- [ ] `frontend/src/lib/types.ts` — Shared TypeScript interfaces matching backend schemas (Conversation, Deployment, Template, DeploymentStage, PipelineState, TemplateMetadata, etc.)
- [ ] Global state management via Zustand: `AppState` with conversations, activeConversationId, activeDeployment, templates, catalogSearchQuery, settings, connectionStatus
- [ ] Landing page with two entry points: "Chat with InfraAgent" and "Self-Service Catalog"
- [ ] Dark/light theme support via Tailwind

**Tech Details:**
- Next.js app router (`app/` directory)
- API client at configurable base URL (default: `http://localhost:8000`)
- Ref: TechSpec Section 10

---

### Issue #37 — Build Chat UI (ChatPanel + streaming + human gates)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 6-10) | **Assignee:** E3
**Labels:** `frontend`, `chat-ui`
**Depends on:** #32, #36
**Blocks:** #39, #41

**Description:**
Build the complete chat interface including message history, streaming responses, stage transitions, subscription discovery display, code generation display, and human gate approval modals.

**Acceptance Criteria:**
- [ ] `ChatPanel.tsx` — Full chat interface with message history, markdown rendering, code blocks with syntax highlighting
- [ ] `MessageBubble.tsx` — User and assistant message bubbles with agent name labels
- [ ] `StreamingIndicator.tsx` — Animated indicator during LLM streaming
- [ ] `SubscriptionDiscoveryPanel.tsx` — Displays discovered subscription context inline: resource groups, VNets, naming patterns, quotas
- [ ] **Stage transition visualization:** Progress bar / breadcrumb showing pipeline stage (Consulting → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy). Current stage highlighted, completed stages checked, failed stages marked red
- [ ] **SSE event handling:** assistant_message (streaming text), stage_change (update progress), subscription_context (render discovery panel), files_generated (render file explorer + diagram), approval_required (show approval modal), plan_failure (show error category + rework status)
- [ ] `ApprovalModal.tsx` — Human gate UI for H1 (code + diagram review) and H2 (plan review). Clear approve/reject buttons with feedback text area on reject
- [ ] `FileExplorer.tsx` — Tree view of generated `.tf`/`.bicep` files with syntax highlighting (react-syntax-highlighter or Monaco)
- [ ] `DiagramViewer.tsx` — Renders Mermaid diagram as SVG with zoom/pan/export (download as SVG/PNG). Uses `mermaid` npm package for client-side rendering
- [ ] `useChat.ts` hook — Manages conversation state, SSE/WebSocket connection, message sending
- [ ] IaC language selector (Terraform / Bicep) in chat header
- [ ] Chat input with multi-line support (Enter to send, Shift+Enter for new line)

**Tech Details:**
- SSE via `EventSource` or `fetch` with `ReadableStream`
- Mermaid rendering via `mermaid` npm package
- Ref: TechSpec Section 10.2, 10.3

---

### Issue #38 — Build Self-Service Catalog UI

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-10) | **Assignee:** E3
**Labels:** `frontend`, `catalog-ui`
**Depends on:** #33, #36
**Blocks:** #41

**Description:**
Build the self-service catalog interface: searchable template grid, template detail view with parameter form, and one-click deploy.

**Acceptance Criteria:**
- [ ] `CatalogGrid.tsx` — Searchable grid of template cards. Each card: name, description, complexity badge (simple=green, moderate=yellow, complex=red), Azure service icons, IaC language tags
- [ ] Search bar with keyword filtering against template name, description, services, tags
- [ ] `TemplateCard.tsx` — Card component with hover preview
- [ ] `TemplateDetail.tsx` — Full template detail view: description, Azure services, complexity, version, author, approved_by
- [ ] `ParameterForm.tsx` — Dynamic form generated from `metadata.yaml` parameters: supports integer (with min/max slider), string (with allowed_values dropdown), boolean (toggle). Default values pre-filled. Org-level parameters shown as auto-enforced (read-only badge)
- [ ] Deploy button: submits parameters + iac_language + target_repo → `POST /api/catalog/{name}/deploy`
- [ ] After deploy: redirects to `/deployments/{id}` to track progress
- [ ] `useCatalog.ts` hook — Manages template list, search, and deploy state
- [ ] Empty state for no search results
- [ ] Client-side parameter validation matching `metadata.yaml` validation rules

**Tech Details:**
- Ref: TechSpec Section 10.3

---

### Issue #39 — Build Deployment Tracker UI

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 9-11) | **Assignee:** E3
**Labels:** `frontend`, `deployment-ui`
**Depends on:** #34, #36
**Blocks:** #41

**Description:**
Build the deployment tracking page showing pipeline stage progress, PR link, plan output, and deployment result.

**Acceptance Criteria:**
- [ ] `DeploymentTracker.tsx` — Full deployment detail page at `/deployments/:id`
- [ ] `PipelineStages.tsx` — Visual pipeline showing all stages as horizontal stepper: Consulting → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy. Current stage highlighted, completed stages checked, failed stages marked red
- [ ] PR section: link to GitHub PR, branch name, PR status
- [ ] Plan section: plan output with syntax highlighting, resource counts (create/modify/destroy)
- [ ] **Destructive change warning:** Prominent red banner if plan shows `resources_to_destroy > 0`
- [ ] Plan-failure rework indicator: shows rework iteration count (Loop 2), error category, CodeGen rework status
- [ ] Deploy section: deployment progress, success/failure status
- [ ] File explorer (reused from chat) for viewing generated code
- [ ] Diagram viewer (reused from chat) for architecture diagram
- [ ] Real-time updates via polling `GET /api/deployments/{id}` every 3-5 seconds during active stages
- [ ] `useDeployment.ts` hook — Manages deployment state with polling

**Tech Details:**
- Plan output color coding: green for +create, yellow for ~modify, red for -destroy
- Ref: TechSpec Section 10.3

---

### Issue #40 — Build Settings page

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 9-10) | **Assignee:** E3
**Labels:** `frontend`, `settings`
**Depends on:** #36

**Description:**
Build the settings page for configuring Azure subscription, GitHub repo, and connection details.

**Acceptance Criteria:**
- [ ] `/settings` page with form fields: Azure subscription ID, Azure tenant ID, GitHub repo (owner/name), default branch, IaC language preference
- [ ] GitHub PAT field (masked input, stored encrypted server-side)
- [ ] Connection test buttons: verify Azure subscription access, verify GitHub repo access, verify Foundry connectivity
- [ ] Connection status indicators on the main layout header (green/red dots for Azure, GitHub, Foundry)
- [ ] Settings persisted via `POST /api/settings` → database `settings` table
- [ ] Settings loaded on app startup via `GET /api/settings`

**Tech Details:**
- Secrets (GitHub PAT) sent to backend for storage in Key Vault, never stored in browser
- Ref: TechSpec Section 10.1

---

## EPIC 8: Mermaid Diagram Rendering Pipeline

---

### Issue #41 — Implement server-side Mermaid-to-SVG rendering

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E3
**Labels:** `backend`, `diagram`, `frontend`
**Depends on:** #19

**Description:**
The frontend renders Mermaid diagrams client-side for interactive viewing, but the PR Workflow Agent needs to commit a static SVG file to `/docs/architecture/` in the repo. Implement server-side Mermaid-to-SVG conversion.

**Acceptance Criteria:**
- [ ] Install `@mermaid-js/mermaid-cli` (`mmdc`) as a backend dependency (or Node.js subprocess)
- [ ] `src/infrastructure/adapters/diagram_renderer.py` — `render_mermaid_to_svg(mermaid_code: str) -> str` that converts Mermaid text to SVG string
- [ ] Called by the PR Workflow Agent before committing files — SVG is added to the file list alongside IaC files
- [ ] SVG committed to `/docs/architecture/{deployment-id}.svg` in the PR
- [ ] Fallback: if `mmdc` is unavailable, commit the `.mermaid` file directly and log a warning
- [ ] Unit test with sample Mermaid input

**Tech Details:**
- `mmdc -i input.mmd -o output.svg -t dark` for SVG generation
- May need Puppeteer/headless Chrome for server-side rendering
- Alternative: use `mermaid-render` Python package if available
- This is consumed by Issue #29 (PR Workflow Agent) during file commit

---

## EPIC 9: AI Search & Policy RAG

---

### Issue #42 — Set up AI Search indexes for Policy RAG and template search

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E5
**Labels:** `backend`, `ai-search`, `infrastructure`
**Depends on:** #6, #8, #9
**Blocks:** #27

**Description:**
Configure Azure AI Search indexes for the Standards Agent (Policy RAG) and the Self-Service Catalog (template search). Create the indexing pipeline that populates indexes from the knowledge wiki submodule.

**Acceptance Criteria:**
- [ ] AI Search index `standards-policies` — Indexes content from `knowledge-wiki/standards/*.md` (naming.md, tagging.md, policies.md). Fields: title, content, section, category
- [ ] AI Search index `templates` — Indexes template metadata from `knowledge-wiki/templates/*/metadata.yaml`. Fields: name, display_name, description, azure_services, complexity, iac_languages, tags, parameters (as JSON), version
- [ ] `src/infrastructure/adapters/ai_search_adapter.py` — Adapter for querying AI Search indexes
- [ ] Indexer script or backend startup routine that populates/refreshes indexes from the knowledge wiki submodule content
- [ ] CI pipeline step in wiki repo that triggers index refresh when standards or templates are updated
- [ ] Falls back gracefully to direct file-read search if AI Search is unavailable (for local dev)

**Tech Details:**
- Use `azure-search-documents` SDK for index operations
- Index schema should support keyword search (BM25) for templates and semantic search for policy RAG
- Ref: TechSpec Section 11 (Azure AI Search), deployment.md (AI Search setup)

---

## EPIC 10: Integration & End-to-End

---

### Issue #43 — End-to-end integration: Chat path (Demo 1)

**Priority:** P0 | **Size:** XL | **Week:** 2-3 (Day 10-13) | **Assignee:** E1 + E3
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #24, #25, #27, #28, #29, #31, #32, #37
**Blocks:** #46

**Description:**
Wire everything together for the chat path end-to-end: user sends message → Consulting Agent gathers requirements → subscription discovery → CodeGen generates Bicep/Terraform (AVM-first) → IaC Validation Pipeline → Standards → Security → H1 approval → PR created → plan runs → H2 approval → deploy succeeds.

**Acceptance Criteria:**
- [ ] User types "I need a 3-tier web app with App Service, SQL Database, and a VNet" in chat
- [ ] Consulting Agent asks 2-3 clarifying questions (environment, region, sizing)
- [ ] Consulting Agent classifies project type (e.g., `[PROJECT_TYPE:PRODUCTION]`)
- [ ] Subscription discovery runs and surfaces existing resources conversationally
- [ ] CodeGen generates modular IaC code using AVM modules
- [ ] IaC Validation Pipeline passes (fmt + validate + lint)
- [ ] Standards validates naming/tags — passes
- [ ] Security scans — passes (no critical/high findings)
- [ ] H1 gate shows generated code + Mermaid architecture diagram for review
- [ ] PR is created in target repo with structured description
- [ ] GitHub Actions runs plan
- [ ] H2 gate shows plan output for review
- [ ] Deployment succeeds
- [ ] All stage transitions visible in real-time on frontend
- [ ] Target: < 3 minutes from first message to open PR

**Tech Details:**
- This is Demo 1 from PRD Section 12.1
- Ref: PRD Section 5.1 (full journey), Section 12.1 (demo script)

---

### Issue #44 — End-to-end integration: Catalog path (Demo 2)

**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 11-13) | **Assignee:** E4 + E3
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #26, #29, #31, #33, #38
**Blocks:** #46

**Description:**
Wire everything together for the catalog path end-to-end: user browses catalog → selects AKS template → fills parameters → subscription discovery (lightweight) → hydrate template → validate → H1 → PR → plan → H2 → deploy.

**Acceptance Criteria:**
- [ ] User opens catalog, searches "AKS cluster"
- [ ] Template detail view shows parameters (node_count, vm_size, kubernetes_version, etc.)
- [ ] User fills parameters and clicks deploy
- [ ] Subscription discovery (lightweight) verifies target resource group, checks naming conflicts and quota
- [ ] Template hydrated with org naming/tags applied
- [ ] IaC Validation Pipeline runs (terraform validate on hydrated code)
- [ ] H1 gate shows parameterized code for review
- [ ] PR created, plan runs, H2 approval, deployment succeeds
- [ ] Target: < 1 minute from deploy click to open PR

**Tech Details:**
- This is Demo 2 from PRD Section 12.1
- Catalog path skips consulting, iterative codegen/standards/security loops
- Ref: PRD Section 5.2 (full journey), Section 12.1 (demo script)

---

### Issue #45 — End-to-end integration: Plan failure + rework (Demo 3)

**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 12-14) | **Assignee:** E4 + E2
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #31, #43
**Blocks:** #46

**Description:**
Wire and test the plan-failure rework loop end-to-end: user requests AKS cluster → code generated → plan fails (SKU unavailable) → Deploy Agent categorizes error → CodeGen reworks code → re-validates → new PR → plan succeeds → deploy.

**Acceptance Criteria:**
- [ ] User requests AKS cluster via chat
- [ ] CodeGen generates Terraform code
- [ ] Validation pipeline passes, standards pass, security passes
- [ ] H1 approved, PR created
- [ ] `terraform plan` fails: "VM size Standard_D4s_v3 not available in westeurope"
- [ ] Deploy Agent categorizes failure as `sku_unavailable` (fixable in code)
- [ ] Error output fed back to CodeGen with original requirements + current code + plan error
- [ ] CodeGen queries Azure MCP for available SKUs, updates VM size
- [ ] Code re-enters validation pipeline → passes
- [ ] New PR created, plan succeeds
- [ ] H2 approval, deployment succeeds
- [ ] UI shows plan-failure rework iteration indicator (Loop 2 iteration 1 of 2)

**Tech Details:**
- This is Demo 3 from PRD Section 12.1
- Loop 2: max 2 iterations of plan-failure rework
- May need to use a SKU that's known to be unavailable in the target region to trigger the failure reliably
- Ref: PRD Section 6.2.1, Section 12.1 (demo script)

---

## EPIC 11: Observability

---

### Issue #46a — Implement observability adapter (OpenTelemetry + App Insights)

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E1
**Labels:** `backend`, `observability`
**Depends on:** #4, #6

**Description:**
Implement the `IObservabilityPort` adapter wrapping OpenTelemetry for tracing, metrics, and logging. Export to Azure App Insights.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/otel_adapter.py` implementing `IObservabilityPort`
- [ ] `start_span(name, attributes)` — Creates OpenTelemetry spans for tracing
- [ ] `record_metric(name, value, tags)` — Records custom metrics
- [ ] `log(level, message, **kwargs)` — Structured logging
- [ ] Trace hierarchy per TechSpec Section 14.1: API route → use case → LLM call → MCP tool call → IaC validation step
- [ ] Key metrics instrumented:
  - `infraagent.chat.latency` (histogram)
  - `infraagent.subscription_discoveries` (counter)
  - `infraagent.generate.iterations` (histogram)
  - `infraagent.generate.max_iterations_reached` (counter)
  - `infraagent.iac_validation.failures` (counter by step)
  - `infraagent.plan_rework.iterations` (histogram)
  - `infraagent.plan_rework.category` (counter by category)
  - `infraagent.prs_created` (counter)
  - `infraagent.deployments_triggered` / `succeeded` / `failed` (counters)
  - `infraagent.token_usage` (counter by agent, profile, model_used)
  - `infraagent.mcp.call_latency` (histogram by server, tool)
- [ ] Export to Azure App Insights via `azure-monitor-opentelemetry-exporter`
- [ ] Connection string from environment variable, graceful no-op if not configured

**Tech Details:**
- Use `opentelemetry-api`, `opentelemetry-sdk`, `azure-monitor-opentelemetry-exporter`
- Ref: TechSpec Section 14

---

## EPIC 12: Polish & Demo Preparation

---

### Issue #46 — Demo script rehearsal and edge case hardening

**Priority:** P0 | **Size:** L | **Week:** 3 (Day 13-15) | **Assignee:** ALL
**Labels:** `demo`, `polish`
**Depends on:** #43, #44, #45

**Description:**
Rehearse all 3 demo scenarios end-to-end against real Azure subscription. Identify and fix edge cases, timing issues, and UI polish items.

**Acceptance Criteria:**
- [ ] Demo 1 (Chat path — 3-4 min) runs successfully end-to-end against real Azure subscription
- [ ] Demo 2 (Catalog path — 1-2 min) runs successfully end-to-end
- [ ] Demo 3 (Plan failure + rework — 2-3 min) runs successfully end-to-end
- [ ] Subscription discovery surfaces real resources in demo subscription
- [ ] Architecture diagrams render correctly for all demo scenarios
- [ ] Edge cases handled: network timeouts, MCP server unavailability (graceful degradation), GitHub Actions delays, LLM rate limiting
- [ ] **Performance validation:** Measure actual timings against success metrics (< 3 min chat path to PR, < 1 min catalog path to PR)
- [ ] UI polished: loading states, error messages, stage transition animations
- [ ] Recording backup prepared (screen recording of successful demo run)
- [ ] Demo environment pre-seeded: Azure subscription has existing VNet, resource groups, naming patterns for discovery to surface

**Tech Details:**
- Use a dedicated demo Azure subscription with pre-existing resources
- Pre-seed subscription with a VNet, resource groups so discovery has data to show
- Ref: PRD Section 12.1

---

### Issue #47 — UI polish and responsive design

**Priority:** P0 | **Size:** M | **Week:** 3 (Day 13-14) | **Assignee:** E3
**Labels:** `frontend`, `polish`
**Depends on:** #37, #38, #39

**Description:**
Final UI polish pass: loading states, error handling, responsive layout, keyboard shortcuts, and visual consistency.

**Acceptance Criteria:**
- [ ] Consistent loading skeletons on all data-fetching components
- [ ] Error boundaries with user-friendly error messages
- [ ] Responsive layout that works on 13" laptop screens (primary demo device)
- [ ] Keyboard shortcuts: Enter to send message, Shift+Enter for new line
- [ ] Copy-to-clipboard on code blocks
- [ ] Proper empty states on all list views
- [ ] Favicon and page titles set
- [ ] Stage transition animations (smooth progress bar movement)
- [ ] Plan output color coding (green for create, yellow for modify, red for destroy)
- [ ] Destructive change warning prominently displayed (red banner)

---

### Issue #48 — Update pitch deck and documentation

**Priority:** P0 | **Size:** S | **Week:** 3 (Day 14-15) | **Assignee:** E5
**Labels:** `docs`, `demo`
**Depends on:** #46

**Description:**
Update the hackathon pitch deck with final architecture screenshots, demo GIFs/screenshots, and metrics from demo runs. Ensure all documentation reflects the implemented state.

**Acceptance Criteria:**
- [ ] Pitch deck updated with: actual architecture diagram, UI screenshots from all 3 demo paths, performance metrics from demo runs
- [ ] README.md updated with current setup instructions
- [ ] Any deviations from PRD/TechSpec documented (what was implemented vs. what was designed)
- [ ] API reference reflects actual implemented endpoints

---

## EPIC 13: P1 Stretch Features

---

### Issue #49 — Template Curation Agent (post-deploy feedback loop)

**Priority:** P1 | **Size:** XL | **Week:** 3 (stretch) | **Assignee:** E5
**Labels:** `agents`, `knowledge-wiki`, `p1-stretch`
**Depends on:** #43

**Description:**
Implement the Template Curation Agent that runs post-deployment to analyze deployed custom code, check novelty against existing wiki templates, generalize parameters, and propose a new template via PR to the knowledge wiki repo.

**Acceptance Criteria:**
- [ ] Post-deploy trigger: after successful deployment via chat path
- [ ] Novelty check: compares deployed resources against existing wiki templates
- [ ] Parameter generalization: extracts hardcoded values into configurable parameters
- [ ] Generates `metadata.yaml` for the proposed template
- [ ] Opens PR to the knowledge wiki repo (not InfraAgent repo)
- [ ] **Human Gate H3:** Platform engineer reviews and approves the template PR
- [ ] Approved templates appear in catalog after submodule update

---

### Issue #50 — Conversation memory persistence

**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E1
**Labels:** `backend`, `p1-stretch`
**Depends on:** #10, #32

**Description:**
Persist chat history across sessions so users can return to previous conversations.

**Acceptance Criteria:**
- [ ] Conversations saved to PostgreSQL `conversations` + `messages` tables
- [ ] Chat UI shows conversation list sidebar with recent conversations
- [ ] User can click a previous conversation to reload history and continue
- [ ] Conversation title auto-generated from first user message

---

### Issue #51 — Cost estimation integration

**Priority:** P1 | **Size:** L | **Week:** 3 (stretch) | **Assignee:** E2
**Labels:** `backend`, `p1-stretch`
**Depends on:** #19

**Description:**
Integrate Infracost (Terraform) or Azure Pricing Calculator API to show estimated monthly cost before deployment.

**Acceptance Criteria:**
- [ ] For Terraform: run `infracost breakdown --path <dir> --format json` on generated code
- [ ] Cost estimate shown alongside plan output at H2 review
- [ ] Monthly cost breakdown by resource

---

### Issue #52 — Set Diff Analyzer for plan review

**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E4
**Labels:** `backend`, `deploy`, `p1-stretch`
**Depends on:** #31

**Description:**
Filter false-positive diffs in Terraform plan output caused by AzureRM Set-type attribute reordering.

**Acceptance Criteria:**
- [ ] Categorize changes: 🟢 order-only (safe to ignore), 🟡 actual Set changes (review content), 🔴 resource replacement (check downtime impact)
- [ ] Frontend `PlanDiffViewer.tsx` shows filtered view by default with option to show all
- [ ] Relevant for Application Gateway backend pools, NSG security rules

**Tech Details:**
- Parse `terraform plan -json` output, detect Set-type attributes, compare element content ignoring order
- Ref: PRD Section 7.1.8

---

### Issue #53 — IaC language toggle mid-conversation

**Priority:** P1 | **Size:** S | **Week:** 3 (stretch) | **Assignee:** E3
**Labels:** `frontend`, `p1-stretch`
**Depends on:** #37

**Description:**
Allow user to switch between Terraform and Bicep mid-conversation. CodeGen agent adapts to the new language.

**Acceptance Criteria:**
- [ ] Language toggle in chat header (Terraform / Bicep)
- [ ] Switching language re-triggers code generation in the new language
- [ ] Previous code shown as "previous version" in file explorer

---

## EPIC 14: Risk Mitigations

---

### Issue #54 — Implement graceful degradation for MCP server unavailability

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E1
**Labels:** `backend`, `resilience`
**Depends on:** #22

**Description:**
When MCP servers are unavailable, agents should fall back to plain LLM generation with cached schemas rather than failing. Output should be flagged as ungrounded.

**Acceptance Criteria:**
- [ ] MCP health check on startup and periodically (every 60 seconds)
- [ ] When MCP is down, CodeGen agent generates code using LLM training data with a warning: "Generated without live registry grounding — review carefully"
- [ ] `GenerateResult` includes `grounded: bool` flag indicating whether MCP tools were used
- [ ] Frontend surfaces "ungrounded" warning badge on generated code when `grounded=false`
- [ ] Cached provider schemas available as fallback (basic `azurerm` resources)
- [ ] Logged as warning metric: `infraagent.mcp.degraded_generations` (counter)

---

### Issue #55 — Implement Foundry Agent Service fallback orchestration

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 9-10) | **Assignee:** E1
**Labels:** `backend`, `resilience`
**Depends on:** #23, #25

**Description:**
If Foundry Agent Service workflow API has limitations hit during build (PRD Risk #2), implement a simpler fallback orchestration pattern using direct agent calls with custom code.

**Acceptance Criteria:**
- [ ] `src/infrastructure/agents/simple_orchestrator.py` — Sequential pipeline using direct `AIProjectClient.agents` calls instead of `AgentWorkflow` graph API
- [ ] Same pipeline sequence (consult → codegen → validation → standards → security → H1 → PR → plan → H2 → deploy)
- [ ] Same maker-checker loop logic (max 3 iterations)
- [ ] Same plan-failure rework logic (max 2 iterations)
- [ ] Human gates implemented as simple async waits on approval endpoints
- [ ] Can be swapped in via configuration flag: `USE_SIMPLE_ORCHESTRATOR=true`
- [ ] Passes the same integration tests as the Agent Framework orchestrator

**Tech Details:**
- This is the escape hatch if the Agent Framework graph workflow API proves too complex or buggy
- Should be a drop-in replacement with identical pipeline behavior

---

## Summary: Issue Dependency & Parallelization Map

**The below are REF numbers**

### Week 1 (Foundation) — 21 issues, high parallelism

| Day | E1 (Agent Backend) | E2 (CodeGen+Validation) | E3 (Frontend) | E4 (GitHub+Deploy) | E5 (Wiki+Infra) |
|-----|---------------------|-------------------------|---------------|--------------------|--------------------|
| 1-2 | #1 (repo), #4 (ports) | #2 (models), #3 (policies) | #36 (scaffold FE) | #7 (CI/CD) | #6 (Azure infra), #8 (wiki repo) |
| 3-5 | #11 (LLM adapter), #18 (ConsultUC) | #5 (IaC parser), #13 (TF adapter), #14 (Bicep adapter), #16 (policy adapter) | #36 (cont.) | #10 (DB schema), #12 (GitHub adapter), #20 (DeployUC) | #9 (templates), #15 (template registry adapter) |

### Week 2 (Integration) — 25 issues, moderate parallelism

| Day | E1 (Agent Backend) | E2 (CodeGen+Validation) | E3 (Frontend) | E4 (GitHub+Deploy) | E5 (Wiki+Infra) |
|-----|---------------------|-------------------------|---------------|--------------------|--------------------|
| 6-8 | #17 (sub discovery), #22 (MCP config), #23 (agent reg), #35 (DI) | #19 (GenerateUC), #21 (prompts - E2 portion), #24 (validation pipeline) | #37 (chat UI) | #29 (PR agent), #30 (CI/CD templates), #33 (catalog API) | #42 (AI Search indexes) |
| 8-10 | #25 (chat workflow), #26 (catalog workflow), #32 (chat API), #46a (otel), #54 (MCP fallback) | #27 (standards agent), #28 (security agent) | #38 (catalog UI), #39 (deploy tracker), #40 (settings), #41 (Mermaid SVG) | #31 (deploy agent), #34 (deployment+health API) | #21 (prompts - E1 portion) |

### Week 3 (Polish + Demo) — 10 issues, sequential focus

| Day | E1 | E2 | E3 | E4 | E5 |
|-----|-----|-----|-----|-----|------|
| 11-12 | #43 (E2E chat), #55 (fallback orch) | #45 (E2E plan fail) | #43 (E2E chat - FE), #44 (E2E catalog - FE) | #44 (E2E catalog), #45 (E2E plan fail) | #49 (P1: curation agent) |
| 13-15 | #46 (demo rehearsal), #50 (P1: memory) | #46 (demo rehearsal), #51 (P1: cost) | #46 (demo rehearsal), #47 (UI polish) | #46 (demo rehearsal), #52 (P1: set diff) | #46 (demo rehearsal), #48 (docs+pitch) |

### Critical Path

```
#1 → #4 → #11 → #18 → #23 → #25 → #32 → #43 → #46
     ↓
     #13/#14 → #19 → #24 → #27/#28 → #43
     ↓
     #12 → #20 → #29/#31 → #44/#45
     ↓
     #8 → #9 → #15 → #33 → #38/#44
```
  ---                                                                                                          
  Critical Path Explanation                                                                                    
                                                                                                               
  The critical path is a dependency graph showing the minimum sequence of work that gates everything else.     
  Delays on this path delay the whole project.                                                                 
                  
  #1 → #4 → #11 → #18 → #23 → #25 → #32 → #43 → #46
       ↓
       #13/#14 → #19 → #24 → #27/#28 → #43
       ↓
       #12 → #20 → #29/#31 → #44/#45
       ↓
       #8 → #9 → #15 → #33 → #38/#44

  ---
  The Trunk (single-threaded blocker chain)

  ┌───────┬──────────────────────────┬─────────────────────────────────────────────────────────────────────┐
  │ Issue │          Title           │                            Why it blocks                            │
  ├───────┼──────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ #1    │ Initialize monorepo      │ Foundation for everything — nothing can start without the project   │
  │       │                          │ structure                                                           │
  ├───────┼──────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ #4    │ Define all port          │ All adapters and use cases depend on these contracts                │
  │       │ interfaces               │                                                                     │
  └───────┴──────────────────────────┴─────────────────────────────────────────────────────────────────────┘

  #1 → #4 must be done sequentially before any of the 4 parallel tracks can begin.

  ---
  4 Parallel Tracks (all fan out from #4)

  Once #4 is done, 4 tracks can run in parallel, each converging on the demo issues:

  Track 1 — Chat / Orchestration path (E1)
  #4 → #11 (LLM/ModelRouter adapter)
     → #18 (ConsultUseCase)
     → #23 (Register agents in Azure AI Foundry)
     → #25 (Orchestrator chat workflow)
     → #32 (Chat API + WebSocket)
     → #43 (E2E Demo 1: Chat path)
     → #46 (Demo rehearsal + hardening)
  This is the spine of Demo 1 — the conversational IaC generation flow.

  Track 2 — IaC Generation & Validation (E2)
  #4 → #13/#14 (Terraform + Bicep CLI adapters)
     → #19 (GenerateUseCase)
     → #24 (IaC Validation Pipeline)
     → #27/#28 (Standards Agent + Security Agent)
     → #43
  Delivers the code generation + policy enforcement pipeline that feeds Demo 1.

  Track 3 — Deployment & GitHub (E4)
  #4 → #12 (GitHub adapter)
     → #20 (DeployUseCase)
     → #29/#31 (PR Workflow Agent + Deploy Agent)
     → #44/#45 (Demo 2: Catalog path + Demo 3: Plan failure/rework)
  Delivers the full plan/apply/rework loop and PR automation for Demos 2 & 3.

  Track 4 — Knowledge Wiki & Catalog (E5)
  #4 → #8 (Knowledge wiki repo + submodule)
     → #9 (3 starter templates)
     → #15 (Template Registry adapter)
     → #33 (Catalog API endpoints)
     → #38 (Self-Service Catalog UI)
     → #44
  Delivers the template catalog browsing experience for Demo 2.

  ---
  Convergence Points

  ┌───────┬──────────────────────────────────────────────────────────────────────────┐
  │ Issue │                                   Role                                   │
  ├───────┼──────────────────────────────────────────────────────────────────────────┤
  │ #43   │ Tracks 1 & 2 must both be complete before E2E Demo 1 can pass            │
  ├───────┼──────────────────────────────────────────────────────────────────────────┤
  │ #44   │ Tracks 3 & 4 must both be complete before Demo 2 (Catalog path) can pass │
  ├───────┼──────────────────────────────────────────────────────────────────────────┤
  │ #46   │ Final gate — demo rehearsal only starts when #43 is green                │
  └───────┴──────────────────────────────────────────────────────────────────────────┘

  The riskiest point is #4 → #11/#13/#14 simultaneously, since any slip in the port interfaces (or in the
  LLM/Terraform/Bicep adapters) cascades into all 4 tracks.

The critical path runs through: repo setup → port interfaces → LLM adapter → ConsultUseCase → agent registration → orchestrator workflows → chat API → E2E integration → demo rehearsal.

---

## Issue Count Summary

| Category | P0 (MVP) | P1 (Stretch) | Total |
|----------|----------|--------------|-------|
| Project Setup & Foundation (EPIC 1) | 10 | 0 | 10 |
| Infrastructure Adapters (EPIC 2) | 7 | 0 | 7 |
| Use Cases (EPIC 3) | 3 | 0 | 3 |
| Agent Definitions & Orchestration (EPIC 4) | 5 | 0 | 5 |
| Agent Implementation (EPIC 5) | 5 | 0 | 5 |
| Backend API (EPIC 6) | 4 | 0 | 4 |
| Frontend (EPIC 7) | 5 | 0 | 5 |
| Diagram Rendering (EPIC 8) | 1 | 0 | 1 |
| AI Search & Policy RAG (EPIC 9) | 1 | 0 | 1 |
| Integration & E2E (EPIC 10) | 3 | 0 | 3 |
| Observability (EPIC 11) | 1 | 0 | 1 |
| Polish & Demo (EPIC 12) | 3 | 0 | 3 |
| P1 Stretch (EPIC 13) | 0 | 5 | 5 |
| Risk Mitigations (EPIC 14) | 2 | 0 | 2 |
| **Total** | **50** | **5** | **55** |