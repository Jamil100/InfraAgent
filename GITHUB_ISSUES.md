# InfraAgent - GitHub Issues Backlog

**Timeline:** 3 weeks (April 2026)
**Team:** 5 engineers
**Priority Legend:** P0 = Must Have (MVP), P1 = Should Have (Stretch), P2 = Nice to Have (Post-Hackathon)
**Size Legend:** XS (< 2h), S (2-4h), M (4-8h), L (1-2 days), XL (2-3 days)

**Engineer Tracks:**
- **E1** — Agent Backend + Foundry
- **E2** — CodeGen + Validation + Standards + Security
- **E3** — Frontend
- **E4** — GitHub + Deploy Pipeline
- **E5** — Knowledge Wiki + Infrastructure

---

## EPIC 1: Project Setup & Infrastructure Foundation

---

### Issue #1 — Initialize monorepo with clean architecture project structure

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1) | **Assignee:** E1
**Labels:** `setup`, `backend`, `foundation`
**Blocks:** #2, #3, #4, #5, #6, #7, #8, #9, #10, #14, #15

**Description:**
Create the InfraAgent monorepo with the full clean architecture directory structure defined in TechSpec Section 11. This is the skeleton that all other work builds on.

**Acceptance Criteria:**
- [ ] Repository initialized with `src/domain/`, `src/application/`, `src/infrastructure/`, `src/api/`, `src/prompts/`, `frontend/`, `infra/`, `tests/`, `.github/workflows/`
- [ ] `pyproject.toml` configured with Python 3.12, dependencies (fastapi, uvicorn, azure-ai-projects, azure-identity, sqlalchemy[asyncio], pydantic, ruff, mypy, pytest, pytest-asyncio)
- [ ] `ruff` and `mypy` configured per TechSpec Section 16.1
- [ ] `Dockerfile` and `docker-compose.yml` scaffolded (backend + postgres)
- [ ] `.gitignore` for Python, Node, Terraform, Bicep artifacts
- [ ] Empty `__init__.py` files in all Python packages
- [ ] `README.md` with project overview and setup instructions

**Tech Details:**
- Follow the project structure from TechSpec Section 11 exactly
- Use `pyproject.toml` with `[project.optional-dependencies] dev = [...]` for dev deps
- Python 3.12+ required (Foundry SDK dependency)

---

### Issue #2 — Define domain layer models and enums

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E2
**Labels:** `domain`, `backend`, `foundation`
**Depends on:** #1
**Blocks:** #10, #14, #15, #16

**Description:**
Implement all domain models, enums, and dataclasses from TechSpec Section 3.1. These are pure Python dataclasses with zero external dependencies — the core of the clean architecture.

**Acceptance Criteria:**
- [ ] `src/domain/models/deployment.py` — `DeploymentStage`, `ProjectType`, `IaCLanguage`, `DeploymentPath`, `GeneratedFile`, `DeploymentRequest`, `Conversation` enums and dataclasses
- [ ] `src/domain/models/template.py` — `TemplateMetadata`, `HydratedTemplate` dataclasses
- [ ] All enums match PRD Section 6 and TechSpec Section 3.1 exactly
- [ ] Zero imports from `azure`, `openai`, `fastapi`, or any third-party package
- [ ] Unit tests in `tests/unit/domain/test_models.py`

**Tech Details:**
- Use Python `dataclasses` and `enum.Enum` (no Pydantic in domain layer)
- `DeploymentStage` must include all 14 stages: CONSULTING through CANCELLED
- `ProjectType`: DEMO, PRODUCTION, ENTERPRISE, REGULATED
- Ref: TechSpec Section 3.1

---

### Issue #3 — Implement domain policies (naming, tagging, security)

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 2-3) | **Assignee:** E2
**Labels:** `domain`, `backend`, `foundation`
**Depends on:** #1
**Blocks:** #22, #23

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
**Blocks:** #10, #11, #12, #13, #14, #15, #16

**Description:**
Define all abstract port interfaces in the application layer. These are the contracts between layers — changing an LLM provider, IaC tool, or git service means implementing a new adapter without touching business logic.

**Acceptance Criteria:**
- [ ] `src/application/ports/llm_port.py` — `LLMMessage`, `LLMResponse`, `ToolDefinition`, `TaskProfile` dataclasses + `ILLMCompletionPort` ABC with `complete()` and `complete_with_tools()` methods (ModelRouter-aware via TaskProfile)
- [ ] `src/application/ports/infra_provider_port.py` — `ValidationResult`, `PlanResult`, `ApplyResult` dataclasses + `IInfraProviderPort` ABC with `format_check()`, `validate()`, `lint()`, `plan()`, `apply()`, `get_language()`
- [ ] `src/application/ports/source_control_port.py` — `PRResult`, `PipelineStatus` dataclasses + `ISourceControlPort` ABC with `create_branch()`, `commit_files()`, `create_pr()`, `get_pipeline_status()`, `trigger_workflow()`
- [ ] `src/application/ports/policy_engine_port.py` — `PolicyViolation`, `PolicyResult` dataclasses + `IPolicyEnginePort` ABC with `validate_naming()`, `validate_tags()`, `validate_security()`
- [ ] `src/application/ports/template_registry_port.py` — `TemplateMetadata`, `HydratedTemplate` dataclasses + `ITemplateRegistryPort` ABC with `search()`, `get_template()`, `hydrate()`, `publish()`
- [ ] `src/application/ports/subscription_discovery_port.py` — `DiscoveredResource`, `DiscoveredVNet`, `SubscriptionContext` dataclasses + `ISubscriptionDiscoveryPort` ABC with `discover()`, `check_sku_availability()`, `check_quota()`
- [ ] `src/application/ports/observability_port.py` — `IObservabilityPort` ABC with `start_span()`, `record_metric()`, `log()`
- [ ] All ports use `async` methods and Python ABCs
- [ ] No implementation details — only contracts

**Tech Details:**
- `TaskProfile` has `profile` field for ModelRouter: "complex-reasoning", "code-generation", "analysis", "fast-lightweight", "orchestration"
- `LLMResponse` includes `model_used: str | None` to track which model ModelRouter selected
- Ref: TechSpec Section 2.1 for all port definitions

---

### Issue #5 — Provision Azure infrastructure via Bicep (InfraAgent self-deployment)

**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 1-4) | **Assignee:** E5
**Labels:** `infrastructure`, `bicep`, `azure`
**Blocks:** #9, #17, #18, #26

**Description:**
Create Bicep modules to deploy all Azure resources InfraAgent needs. This is dogfooding — InfraAgent's own infra is IaC.

**Acceptance Criteria:**
- [ ] `infra/main.bicep` — Root orchestration module
- [ ] `infra/modules/foundry.bicep` — Azure AI Foundry resource + project
- [ ] `infra/modules/postgres.bicep` — Azure PostgreSQL Flexible Server (Burstable B1ms)
- [ ] `infra/modules/appService.bicep` — App Service (B2) for Python backend
- [ ] `infra/modules/staticWebApp.bicep` — Static Web App for React frontend
- [ ] `infra/modules/keyVault.bicep` — Key Vault for secrets (GitHub PAT, API keys)
- [ ] `infra/modules/aiSearch.bicep` — Azure AI Search (Basic) for policy RAG
- [ ] `infra/modules/functionApp.bicep` — Azure Functions (Consumption) for MCP server hosting
- [ ] `infra/modules/monitoring.bicep` — App Insights + Log Analytics workspace
- [ ] `infra/parameters/dev.bicepparam` and `infra/parameters/prod.bicepparam`
- [ ] Managed Identity used for all service-to-service auth
- [ ] All modules validate with `bicep build`

**Tech Details:**
- SKUs per TechSpec Section 12.1 (B2 App Service, B1ms Postgres, Basic AI Search, etc.)
- Estimated cost ~$225-275/month (TechSpec Section 12.2)
- Use `enableRbacAuthorization: true` on Key Vault
- Configure VNET integration where applicable for security
- Ref: TechSpec Section 12

---

### Issue #6 — Set up CI/CD pipelines (GitHub Actions)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 2-3) | **Assignee:** E4
**Labels:** `ci-cd`, `devops`
**Depends on:** #1
**Blocks:** #29, #30

**Description:**
Create GitHub Actions workflows for InfraAgent's own CI/CD: linting, testing, and deployment.

**Acceptance Criteria:**
- [ ] `.github/workflows/ci.yml` — Runs on PR: checkout, setup Python 3.12, `pip install -e ".[dev]"`, `ruff check`, `mypy`, `pytest tests/unit/`, `pytest tests/integration/ -m "not slow"`
- [ ] `.github/workflows/deploy-infra.yml` — Bicep deployment for InfraAgent's Azure resources (manual trigger + on push to `infra/`)
- [ ] `.github/workflows/deploy-app.yml` — Backend + frontend deployment to Azure App Service / Static Web App
- [ ] `.github/workflows/ci.yml` includes `git submodule update --init --recursive` for knowledge wiki
- [ ] All workflows use proper secret references for Azure credentials

**Tech Details:**
- Use `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`
- Backend deploys to App Service via `azure/webapps-deploy@v3`
- Frontend deploys to Static Web Apps via `Azure/static-web-apps-deploy@v1`
- Ref: TechSpec Section 13.1

---

### Issue #7 — Create knowledge wiki repository and wire as git submodule

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 1-3) | **Assignee:** E5
**Labels:** `knowledge-wiki`, `foundation`
**Depends on:** #1
**Blocks:** #8, #20, #21, #27

**Description:**
Create the separate `infraagent-wiki` GitHub repository with the full directory structure defined in PRD Section 8. Wire it into the InfraAgent repo as a git submodule at `knowledge-wiki/`.

**Acceptance Criteria:**
- [ ] Separate GitHub repo `infraagent-wiki` created with structure: `templates/`, `skills/`, `standards/`, `patterns/`
- [ ] `standards/naming.md` — Organization naming conventions matching domain policy defaults
- [ ] `standards/tagging.md` — Required tags matching domain policy defaults
- [ ] `standards/policies.md` — Structural and security policies
- [ ] `skills/general-azure/SKILL.md` — General Azure consulting skill with phase-specific questions
- [ ] `.gitmodules` in InfraAgent repo pointing to `infraagent-wiki` at `knowledge-wiki/` path
- [ ] Wiki repo has its own CI that validates template syntax
- [ ] `metadata.yaml` JSON schema defined and documented

**Tech Details:**
- Pin submodule to a release tag (e.g., `v0.1.0`)
- Skill files follow structure: metadata header, phase-specific question banks, pattern selection logic, component catalogs, readiness checklists
- Template `metadata.yaml` schema per PRD Section 8.2
- Ref: PRD Section 8, TechSpec Section 7

---

### Issue #8 — Author 3 starter templates for knowledge wiki

**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 2-5) | **Assignee:** E5
**Labels:** `knowledge-wiki`, `templates`, `iac`
**Depends on:** #7
**Blocks:** #27, #34

**Description:**
Create at least 3 pre-validated, AVM-first IaC templates in both Terraform and Bicep for the self-service catalog. These templates must pass `terraform validate` / `bicep build` and conform to organizational standards.

**Acceptance Criteria:**
- [ ] `templates/aks-cluster/` — AKS cluster with managed identity, Azure CNI, monitoring. Terraform + Bicep. `metadata.yaml` with parameters: node_count, vm_size, kubernetes_version, enable_monitoring, network_plugin
- [ ] `templates/3-tier-web-app/` — App Service + SQL Database + VNet with subnets. Terraform + Bicep. `metadata.yaml` with parameters: app_service_sku, sql_tier, region
- [ ] `templates/static-website-cdn/` — Storage Account + CDN + custom domain. Terraform + Bicep. `metadata.yaml` with parameters: cdn_sku, storage_replication
- [ ] All templates use AVM modules where available (e.g., `Azure/avm-res-containerservice-managedcluster/azurerm`)
- [ ] All templates have proper `metadata.yaml` per schema (name, description, azure_services, complexity, parameters with validation, tags, version)
- [ ] All Terraform templates pass `terraform fmt -check`, `terraform init`, `terraform validate`
- [ ] All Bicep templates pass `bicep build`
- [ ] No hardcoded secrets — uses Key Vault, managed identity, `sensitive = true` / `@secure()`
- [ ] Each template has `variables.tf` / `main.bicepparam` with typed, described, alphabetized variables

**Tech Details:**
- AVM Terraform modules: `source = "Azure/avm-res-{service}-{resource}/azurerm"` with `version = "~> x.y"`
- AVM Bicep modules: `br/public:avm/res/{service}/{resource}:{version}`
- File structure per PRD Section 7.1.3.2
- Ref: PRD Section 7.1.3.1, TechSpec Section 7

---

### Issue #9 — Implement database schema and migrations

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 3-4) | **Assignee:** E4
**Labels:** `backend`, `database`
**Depends on:** #5
**Blocks:** #14, #15, #16

**Description:**
Implement the PostgreSQL database schema from TechSpec Section 9 using SQLAlchemy async ORM with Alembic migrations.

**Acceptance Criteria:**
- [ ] SQLAlchemy async models for: `conversations`, `messages`, `deployments`, `generated_files`, `settings`, `audit_log`
- [ ] Alembic migration for initial schema creation
- [ ] `deployments` table includes all columns: stage, project_type, subscription_id, subscription_context (JSONB), template_name, template_params (JSONB), pr_number, pr_url, plan_output, plan_status, plan_error_category, plan_rework_iteration, apply_status, violations (JSONB), diagram_mermaid, target_repo
- [ ] Indexes: `idx_messages_conversation`, `idx_files_deployment`
- [ ] `settings` table is singleton (fixed UUID PK)
- [ ] `audit_log` table for tracking H1/H2 approvals, PR creation, deployment actions
- [ ] Database adapter (`src/infrastructure/adapters/postgres_adapter.py`) with CRUD operations
- [ ] Integration test for schema creation

**Tech Details:**
- Use `asyncpg` as the async PostgreSQL driver
- SQLAlchemy 2.0 async style with `AsyncSession`
- UUID primary keys via `gen_random_uuid()`
- JSONB columns for flexible structured data (violations, subscription_context, template_params)
- Ref: TechSpec Section 9

---

## EPIC 2: Agent Backend & Foundry Integration

---

### Issue #10 — Implement Azure OpenAI / ModelRouter LLM adapter

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E1
**Labels:** `backend`, `ai-foundry`, `adapter`
**Depends on:** #4
**Blocks:** #14, #15, #16, #17, #18, #19

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
- [ ] Integration test with mocked Azure endpoint

**Tech Details:**
- Use `azure-ai-projects` SDK with `AIProjectClient`
- `DefaultAzureCredential` for auth
- ModelRouter configured at Foundry project level per TechSpec Section 5.1
- Ref: TechSpec Section 2.1, PRD Section 6.1.1

---

### Issue #11 — Implement GitHub adapter (ISourceControlPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E4
**Labels:** `backend`, `github`, `adapter`
**Depends on:** #4
**Blocks:** #25, #26, #29

**Description:**
Implement the `ISourceControlPort` adapter for GitHub operations: branch management, file commits, PR creation, and GitHub Actions workflow monitoring.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/github_adapter.py` implementing `ISourceControlPort`
- [ ] `create_branch(repo, branch, base)` — Creates a new branch from base
- [ ] `commit_files(repo, branch, files, message)` — Atomic tree commit of multiple files
- [ ] `create_pr(repo, title, body, head, base)` — Opens PR with structured description, returns `PRResult`
- [ ] `get_pipeline_status(repo, run_id)` — Polls GitHub Actions for plan/apply status, returns `PipelineStatus`
- [ ] `trigger_workflow(repo, workflow, ref, inputs)` — Triggers a GitHub Actions workflow dispatch
- [ ] GitHub PAT loaded from Azure Key Vault (not env vars)
- [ ] Rate limit handling with exponential backoff
- [ ] Batch file commits into single tree commit (avoid rate limits per PRD Section 14)
- [ ] Integration test with mocked GitHub API

**Tech Details:**
- Use PyGithub or `httpx` for GitHub REST API
- Tree commit via Git Data API for atomic multi-file commits
- Branch naming convention: `infraagent/{title-slug}`
- Ref: TechSpec Section 2.1 (ISourceControlPort)

---

### Issue #12 — Implement Terraform CLI adapter (IInfraProviderPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Labels:** `backend`, `terraform`, `adapter`
**Depends on:** #4
**Blocks:** #21, #22, #29

**Description:**
Implement the `IInfraProviderPort` adapter for Terraform CLI operations: format checking, init, validate, lint, plan, and apply.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/terraform_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — Runs `terraform fmt -check`, returns `ValidationResult`
- [ ] `validate(files)` — Runs `terraform init` + `terraform validate`, returns `ValidationResult`
- [ ] `lint(files)` — Runs `tflint` (stretch: returns warnings only), returns `ValidationResult`
- [ ] `plan(files, variables)` — Runs `terraform plan -no-color -out=tfplan`, returns `PlanResult` with resource counts
- [ ] `apply(plan_id)` — Runs `terraform apply`, returns `ApplyResult`
- [ ] `get_language()` returns `"terraform"`
- [ ] Files are written to a temporary working directory for CLI execution
- [ ] Proper cleanup of temp directories
- [ ] Stderr + exit code captured for error categorization
- [ ] Integration test against terraform CLI

**Tech Details:**
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Temp directory per validation run, cleaned up on completion
- `terraform init` runs with `-backend=false` for validation-only mode
- Parse `terraform plan` JSON output (`-json` flag) for structured resource counts
- Ref: TechSpec Section 4.2, PRD Section 7.1.4

---

### Issue #13 — Implement Bicep CLI adapter (IInfraProviderPort)

**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Labels:** `backend`, `bicep`, `adapter`
**Depends on:** #4
**Blocks:** #21, #22, #29

**Description:**
Implement the `IInfraProviderPort` adapter for Bicep CLI operations: build, format, lint, and deployment.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/bicep_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — Runs `bicep format --verify`, returns `ValidationResult`
- [ ] `validate(files)` — Runs `bicep build --stdout --no-restore`, returns `ValidationResult`
- [ ] `lint(files)` — Runs Bicep linter rules, returns `ValidationResult`. Triage: BCP081 ignored if API version confirmed, BCP035 checked, BCP187 ignored
- [ ] `plan(files, variables)` — Runs `az deployment group what-if`, returns `PlanResult`
- [ ] `apply(plan_id)` — Runs `az deployment group create`, returns `ApplyResult`
- [ ] `get_language()` returns `"bicep"`
- [ ] Proper lint warning triage per PRD Section 7.1.4
- [ ] Integration test against bicep CLI

**Tech Details:**
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Bicep lint warnings triaged: BCP081 (type not defined) ignored if API version confirmed; BCP035 (missing property) checked; BCP187 (SKU/kind unverified) ignored
- Ref: PRD Section 7.1.4, TechSpec Section 4.2

---

### Issue #14 — Implement ConsultUseCase

**Priority:** P0 | **Size:** L | **Week:** 1-2 (Day 4-6) | **Assignee:** E1
**Labels:** `backend`, `use-case`, `consulting-agent`
**Depends on:** #2, #4, #10
**Blocks:** #17, #33

**Description:**
Implement the ConsultUseCase that drives the Consulting Agent's multi-turn requirements gathering conversation, including project type classification, subscription discovery, knowledge wiki search, and template recommendations.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/consult.py` with `ConsultUseCase` class
- [ ] Constructor injection of `ILLMCompletionPort`, `ITemplateRegistryPort`, `ISubscriptionDiscoveryPort`, `IObservabilityPort`
- [ ] `run()` method: processes one conversation turn — builds system prompt with domain skill, searches wiki for templates, calls LLM with ModelRouter profile `complex-reasoning`, parses response for routing signals
- [ ] Project type extraction via `[PROJECT_TYPE:X]` markers
- [ ] Template recommendation via `[RECOMMEND_TEMPLATE:name]` markers
- [ ] Requirements completion via `[REQUIREMENTS_COMPLETE]` marker
- [ ] Subscription discovery when `subscription_id` is provided — calls `ISubscriptionDiscoveryPort.discover()`, formats context into system prompt
- [ ] `ConsultResult` returned with response, recommended_template, recommended_path ("catalog" or "custom"), requirements_complete, project_type, subscription_context
- [ ] Unit tests with mocked ports

**Tech Details:**
- System prompt built dynamically with domain skill context and subscription context
- Template matches appended to user message as system context
- ModelRouter task profile: `complex-reasoning`
- Ref: TechSpec Section 4.1

---

### Issue #15 — Implement GenerateUseCase (custom + catalog paths)

**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 4-8) | **Assignee:** E2
**Labels:** `backend`, `use-case`, `codegen-agent`
**Depends on:** #2, #4, #10, #12, #13
**Blocks:** #22, #23, #24, #33

**Description:**
Implement the GenerateUseCase with both the custom generation pipeline (CodeGen + IaC Validation + Standards + Security + Diagram) and the catalog fast-path (hydrate + validate). Includes the maker-checker loop (max 3 iterations) and plan-failure rework logic.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/generate.py` with `GenerateUseCase` class
- [ ] `run_custom_path()` — Full pipeline: CodeGen (AVM-first) → IaC Validation Pipeline (fmt/validate/lint) → Standards → Security → Diagram generation. Loops on violations, max 3 iterations total
- [ ] `run_catalog_path()` — Template hydration + syntax validation only (no iterative loops)
- [ ] `_run_iac_validation_pipeline()` — Deterministic toolchain: format_check → validate → lint. Not LLM-based
- [ ] `_generate_code()` — Calls LLM with MCP tools, AVM-first strategy enforced in prompt, secret handling rules included
- [ ] `_generate_diagram()` — Lightweight LLM call to produce Mermaid architecture diagram from IaC code
- [ ] `_categorize_plan_failure()` — Categorizes plan errors into: resource_conflict, sku_unavailable, quota_exceeded, auth_failure, provider_mismatch, module_error, unknown. Determines if fixable in code
- [ ] `_build_codegen_prompt()` — Dynamic prompt with AVM-first rules, secret handling, file structure, project type WAF depth, subscription context, prior violations
- [ ] `FILE_STRUCTURE_TERRAFORM` and `FILE_STRUCTURE_BICEP` constants for code structure conventions
- [ ] `SECRET_HANDLING_RULES` list enforced in code generation
- [ ] `MAX_MAKER_CHECKER_ITERATIONS = 3`, `MAX_PLAN_REWORK_ITERATIONS = 2`
- [ ] `GenerateResult` with files, standards_passed, security_passed, violations, iteration_count, diagram_mermaid
- [ ] `PlanFailureAnalysis` dataclass for structured error categorization
- [ ] Unit tests with mocked ports for both paths

**Tech Details:**
- Validation pipeline runs BEFORE LLM-based checks (standards, security)
- Violation feedback format: `{ checker, severity, resource, file, line, message, remediation }`
- CodeGen receives last 5 violations for rework context
- Ref: TechSpec Section 4.2, PRD Sections 7.1.3, 7.1.4, 6.2.1

---

### Issue #16 — Implement DeployUseCase

**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 4-6) | **Assignee:** E4
**Labels:** `backend`, `use-case`, `deploy-agent`
**Depends on:** #2, #4, #11
**Blocks:** #25, #26, #33

**Description:**
Implement the DeployUseCase that handles PR creation, plan monitoring, and deployment triggering via GitHub Actions.

**Acceptance Criteria:**
- [ ] `src/application/use_cases/deploy.py` with `DeployUseCase` class
- [ ] `create_pr(repo, files, title, body, base_branch)` — Creates branch (`infraagent/{slug}`), commits files atomically, opens PR with structured description
- [ ] `get_plan_status(repo, run_id)` — Polls GitHub Actions for plan/apply status
- [ ] `trigger_apply(repo, workflow, ref, inputs)` — Triggers `terraform apply` / `az deployment create` workflow
- [ ] Observability metrics: `prs_created`, `deployments_triggered`
- [ ] Unit tests with mocked ports

**Tech Details:**
- Branch naming: `infraagent/{title-lowercase-slugified[:50]}`
- PR body includes: resources created, standards applied, security scan results
- Ref: TechSpec Section 4.3

---

### Issue #17 — Register agents with Azure AI Foundry Agent Service

**Priority:** P0 | **Size:** L | **Week:** 1-2 (Day 4-7) | **Assignee:** E1
**Labels:** `backend`, `ai-foundry`, `agents`
**Depends on:** #5, #10
**Blocks:** #18, #19

**Description:**
Implement the agent registry that registers all 8 agents (orchestrator, consulting, codegen, standards, security, pr_workflow, deploy, template_curation) with Azure AI Foundry as Hosted Agents with ModelRouter task profiles and MCP tool bindings.

**Acceptance Criteria:**
- [ ] `src/infrastructure/agents/registry.py` with `AGENT_CONFIGS` dictionary defining all 8 agents
- [ ] Each agent config specifies: `task_profile` (for ModelRouter), `instructions_file` path, `tools` list (MCP and Function tools)
- [ ] `register_agents()` async function creates/updates all agents in Foundry
- [ ] ModelRouter profiles: orchestrator→orchestration, consulting→complex-reasoning, codegen→code-generation, standards→analysis, security→fast-lightweight, pr_workflow→fast-lightweight, deploy→orchestration, template_curation→code-generation
- [ ] MCP tool bindings: consulting→Azure MCP, codegen→Terraform+Bicep+Azure MCP, standards→GitHub MCP, security→tfsec+Checkov function tools, pr_workflow→GitHub MCP, deploy→GitHub+Azure MCP
- [ ] Uses `DefaultAzureCredential` and Foundry `AIProjectClient`

**Tech Details:**
- `PromptAgentDefinition` with `model_router_profile` instead of model name
- MCP tools use `MCPTool(server_label=..., server_url=..., require_approval="never")`
- Security agent uses `FunctionTool` for tfsec/Checkov
- Ref: TechSpec Section 5.1

---

### Issue #18 — Implement orchestrator workflow (chat path)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 6-10) | **Assignee:** E1
**Labels:** `backend`, `orchestrator`, `agents`
**Depends on:** #14, #15, #16, #17
**Blocks:** #33, #36

**Description:**
Implement the graph-based orchestrator for the chat path using the Microsoft Agent Framework. This is the central coordination workflow: Consult → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy, with maker-checker loops and plan-failure rework.

**Acceptance Criteria:**
- [ ] `src/infrastructure/agents/orchestrator.py` with `build_chat_path_workflow()` function
- [ ] `AgentWorkflow` with all nodes: consult, subscription_discovery, codegen, iac_validation, standards, security, diagram_gen, h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] `HumanApprovalNode` for H1 (code + diagram review) and H2 (plan review)
- [ ] **Maker-checker loop (Loop 1):** ConditionalEdge from security → codegen if violations_fixable AND iteration < 3; → diagram if passed or max_iterations
- [ ] **IaC validation loop:** ConditionalEdge from iac_valid → standards if passed; → codegen if failed
- [ ] **Plan-failure rework (Loop 2):** ConditionalEdge from plan → h2_gate if success; → codegen if failed_fixable (max 2x); → h2_gate with error if failed_escalate (quota, auth)
- [ ] Checkpointing enabled for durable long-running workflows
- [ ] Context sharing between agents (requirements handoff, subscription context, violation feedback)
- [ ] Real-time stage updates emitted as SSE events

**Tech Details:**
- Use `agent_framework.AgentWorkflow`, `AgentNode`, `HumanApprovalNode`, `ConditionalEdge`
- `iac_validation` node has `agent_name=None` (deterministic, not LLM)
- `diagram_gen` uses codegen agent in diagram mode
- Ref: TechSpec Section 5.2

---

### Issue #19 — Implement orchestrator workflow (catalog path)

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E1
**Labels:** `backend`, `orchestrator`, `agents`
**Depends on:** #15, #16, #17
**Blocks:** #34, #36

**Description:**
Implement the graph-based orchestrator for the catalog path. Simpler workflow: Template hydrate → Validate → H1 → PR → Plan → H2 → Deploy. No consulting, no iterative codegen/standards/security loops.

**Acceptance Criteria:**
- [ ] `build_catalog_path_workflow()` function in orchestrator.py
- [ ] Nodes: hydrate (codegen in hydrate mode), validate (syntax only), h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] No maker-checker loop (templates are pre-validated)
- [ ] H1 and H2 human gates functional
- [ ] Context: template parameters + org standards passed through pipeline

**Tech Details:**
- Templates skip standards/security agents (pre-validated at H3 time)
- Validation is syntax-only (Steps 1-3 Terraform, Steps 1-2 Bicep)
- Ref: TechSpec Section 5.2 (`build_catalog_path_workflow`)

---

### Issue #20 — Configure MCP server connections

**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 4-6) | **Assignee:** E1
**Labels:** `backend`, `mcp`, `integration`
**Depends on:** #5, #7
**Blocks:** #17, #18, #19

**Description:**
Configure connections to the 4 MCP servers (Terraform, Bicep, Azure, GitHub) used for grounding agent code generation and operations.

**Acceptance Criteria:**
- [ ] `src/infrastructure/mcp/config.py` with `MCPServerConfig` dataclass and `MCP_SERVERS` dictionary
- [ ] Terraform MCP Server connection (hashicorp/terraform-mcp-server) — tools: search_providers, get_provider_details, search_modules, get_module_details
- [ ] Bicep MCP Server connection — tools: get_az_resource_type_schema, get_bicep_best_practices, list_avm_metadata, format_bicep_file
- [ ] Azure MCP Server connection (microsoft/mcp) — tools: resource management, subscription info, quota checks
- [ ] GitHub MCP Server connection (github/github-mcp-server) — tools: create_branch, commit_files, create_pull_request, workflow operations
- [ ] `src/infrastructure/mcp/tool_adapter.py` — MCP tool → Foundry tool conversion utility
- [ ] Auth configured per server: API key or Entra ID
- [ ] Connection health check

**Tech Details:**
- MCP servers hosted on Azure Functions or Foundry MCP Server surface (`mcp.ai.azure.com`)
- Auth values from Key Vault
- Ref: TechSpec Section 6, PRD Section 9

---

## EPIC 3: Agent Implementation

---

### Issue #21 — Write agent system prompts (all 8 agents)

**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 3-8) | **Assignee:** E2 + E1
**Labels:** `agents`, `prompts`
**Depends on:** #7, #12, #13
**Blocks:** #17

**Description:**
Write comprehensive system prompts for all 8 agents. These are the `instructions` field in the Foundry agent definitions. Prompts are version-controlled markdown files.

**Acceptance Criteria:**
- [ ] `src/prompts/orchestrator.md` — Routing, lifecycle management, pipeline enforcement
- [ ] `src/prompts/consulting_agent.md` — Multi-turn requirements gathering, project type classification, subscription discovery, template recommendation. Includes `[PROJECT_TYPE:X]`, `[RECOMMEND_TEMPLATE:name]`, `[REQUIREMENTS_COMPLETE]` signal markers
- [ ] `src/prompts/codegen_agent_terraform.md` — Terraform HCL generation with AVM-first rules, MCP tool usage, secret handling, file structure conventions, violation rework
- [ ] `src/prompts/codegen_agent_bicep.md` — Bicep generation with AVM-first rules, MCP tool usage, `@secure()` decorator, file structure conventions
- [ ] `src/prompts/standards_agent.md` — Naming, tagging, structural validation, AVM compliance check, dependency correctness
- [ ] `src/prompts/security_agent.md` — tfsec/Checkov invocation, severity classification, remediation guidance
- [ ] `src/prompts/pr_workflow_agent.md` — Branch creation, PR description formatting, diagram commit
- [ ] `src/prompts/deploy_agent.md` — Plan execution, error categorization, rework routing, apply monitoring
- [ ] `src/prompts/template_curation_agent.md` — Post-deploy analysis, novelty check, generalization (P1)
- [ ] Each prompt is 200-500 lines with clear behavioral rules

**Tech Details:**
- Consulting agent must output structured markers for routing signals
- CodeGen prompt dynamically extended by GenerateUseCase with AVM rules, secret handling, WAF depth, subscription context, prior violations
- Ref: TechSpec Appendix A

---

### Issue #22 — Implement IaC Validation Pipeline (deterministic, non-LLM)

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E2
**Labels:** `backend`, `validation`, `pipeline`
**Depends on:** #12, #13, #15
**Blocks:** #33, #36

**Description:**
Implement the deterministic IaC validation pipeline as a function tool chain invoked by the orchestrator. This is NOT an agent — it runs `terraform fmt/init/validate/tflint` or `bicep build/format/lint` without any LLM involvement.

**Acceptance Criteria:**
- [ ] Terraform chain: `fmt -check` (auto-fix, non-blocking) → `init -backend=false` (blocking) → `validate` (blocking) → `tflint` (stretch, warnings only)
- [ ] Bicep chain: `build --stdout --no-restore` (blocking) → `format` (non-blocking) → lint with triage (conditional)
- [ ] Format failures auto-fixed without CodeGen rework
- [ ] Init/validate/build failures produce structured error output fed back to CodeGen
- [ ] Lint warnings attached to H1 review as informational
- [ ] Bicep lint triage: BCP081 ignored, BCP035 checked, BCP187 ignored
- [ ] Returns `{"passed": bool, "errors": list[str], "warnings": list[str]}`
- [ ] Integrated into GenerateUseCase `_run_iac_validation_pipeline()` (runs BEFORE standards/security)
- [ ] Shared retry counter: validation + standards + security = max 3 iterations

**Tech Details:**
- Called by orchestrator between CodeGen and Standards nodes
- Uses `IInfraProviderPort.format_check()`, `.validate()`, `.lint()`
- Ref: PRD Section 7.1.4, TechSpec Section 4.2

---

### Issue #23 — Implement Standards Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 6-8) | **Assignee:** E2
**Labels:** `backend`, `agents`, `standards`
**Depends on:** #3, #15
**Blocks:** #33

**Description:**
Implement the Standards Agent's validation logic combining domain policy rules with LLM-based structural analysis. Validates naming, tagging, AVM compliance, dependency correctness, and file structure.

**Acceptance Criteria:**
- [ ] Naming validation via domain `validate_resource_name()` against org naming rules
- [ ] Tagging validation via domain `validate_tags()` against required tags
- [ ] **AVM compliance check:** Flags raw `azurerm_` resources when an equivalent AVM module exists
- [ ] **Dependency correctness:** Detects redundant `depends_on` where dependency is implicit
- [ ] **File structure validation:** Verifies generated code follows conventions (TechSpec Section 7.1.3.2)
- [ ] Produces structured violation reports: `{ resource, policy, severity, expected, actual, remediation }`
- [ ] Violations fed back to CodeGen as part of Loop 1
- [ ] Policy RAG integration via Azure AI Search for loading policies from standards repo
- [ ] Unit tests with sample IaC code

**Tech Details:**
- Uses `IPolicyEnginePort.validate_naming()` and `.validate_tags()`
- Standards loaded from `knowledge-wiki/standards/` at runtime
- AVM check: if resource_type matches `azurerm_*` and AVM exists → flag
- Ref: PRD Section 7.1.5

---

### Issue #24 — Implement Security Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E2
**Labels:** `backend`, `agents`, `security`
**Depends on:** #15
**Blocks:** #33

**Description:**
Implement the Security Agent that runs tfsec and Checkov static analysis on generated IaC code and produces structured finding reports.

**Acceptance Criteria:**
- [ ] tfsec integration for Terraform code — run as subprocess, parse JSON output
- [ ] Checkov integration for Terraform code — run as subprocess, parse JSON output
- [ ] Bicep security validation via `bicep build` diagnostics + equivalent checks
- [ ] Produces structured finding reports: `{ severity, resource, finding, remediation }`
- [ ] Critical/high findings trigger rework loop; medium/low are informational
- [ ] Findings fed back to CodeGen as part of Loop 1
- [ ] tfsec/Checkov hosted as Azure Functions (or run locally via CLI for hackathon)
- [ ] Uses `IPolicyEnginePort.validate_security()`
- [ ] Unit tests with known-vulnerable IaC samples

**Tech Details:**
- tfsec: `tfsec --format=json --no-color <dir>`
- Checkov: `checkov -d <dir> -o json`
- Severity mapping: CRITICAL/HIGH → rework required; MEDIUM/LOW → warning
- Ref: PRD Section 7.1.6

---

### Issue #25 — Implement PR Workflow Agent logic

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 6-8) | **Assignee:** E4
**Labels:** `backend`, `agents`, `github`
**Depends on:** #11, #16
**Blocks:** #33, #36

**Description:**
Implement the PR Workflow Agent that creates branches, commits generated IaC files, and opens PRs with structured descriptions.

**Acceptance Criteria:**
- [ ] Creates feature branch: `infraagent/{title-slug}`
- [ ] Commits all generated IaC files atomically (single tree commit)
- [ ] Commits auto-generated Mermaid diagram SVG to `/docs/architecture/`
- [ ] Opens PR with structured body: summary of resources created, standards applied, security scan results, diagram link
- [ ] Creates GitHub Actions workflow file in target repo if it doesn't exist (terraform-plan.yml or bicep-whatif.yml)
- [ ] Returns `PRResult` with number, url, html_url, state, branch_name
- [ ] Monitors CI/CD pipeline status via GitHub MCP Server

**Tech Details:**
- PR body template: resources list, standards status, security status, diagram preview
- Workflow templates from TechSpec Section 13.2
- Ref: PRD Section 7.1.7

---

### Issue #26 — Implement Deploy Agent logic (plan/apply + rework loop)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 7-10) | **Assignee:** E4
**Labels:** `backend`, `agents`, `deploy`
**Depends on:** #11, #16
**Blocks:** #33, #36

**Description:**
Implement the Deploy Agent that triggers terraform plan/apply via GitHub Actions, monitors progress, categorizes plan failures, and routes to the plan-failure rework loop (Loop 2).

**Acceptance Criteria:**
- [ ] Triggers `terraform plan` / `bicep what-if` via GitHub Actions workflow dispatch
- [ ] Polls GitHub Actions for pipeline completion (plan/apply status)
- [ ] Surfaces plan output to user for H2 review
- [ ] **Plan failure handling:** Extracts full error output (stderr + exit code), categorizes failure using `_categorize_plan_failure()`:
  - resource_conflict → "Use data source or adjust naming" (fixable)
  - sku_unavailable → "Query Azure MCP for alternatives" (fixable)
  - quota_exceeded → escalate to user (not fixable in code)
  - auth_failure → escalate to user (not fixable in code)
  - provider_mismatch → "Update provider version" (fixable)
  - module_error → "Fix variable value via MCP docs" (fixable)
- [ ] On fixable failure: routes back to CodeGen with error context (Loop 2, max 2 iterations)
- [ ] On non-fixable failure: escalates to user with plan output + analysis
- [ ] On apply success: reports deployment status in real-time
- [ ] On apply failure: captures partial state, provides rollback guidance
- [ ] **Set Diff Analyzer (P1 stretch):** Filters false-positive diffs from Set-type attribute reordering (🟢 order-only, 🟡 actual changes, 🔴 replacement)
- [ ] Monitors deployment progress and reports status updates

**Tech Details:**
- Plan rework loop: full plan error → CodeGen → re-enter validation pipeline (Loop 1) → new PR → re-plan
- Loop 2 max iterations = 2
- Ref: PRD Section 7.1.8, TechSpec Section 4.2 (`_categorize_plan_failure`)

---

## EPIC 4: Backend API Layer

---

### Issue #27 — Implement catalog API endpoints

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 6-8) | **Assignee:** E4
**Labels:** `backend`, `api`, `catalog`
**Depends on:** #7, #8, #9
**Blocks:** #34

**Description:**
Implement the FastAPI routes for the self-service catalog: listing templates, getting template details, and deploying templates.

**Acceptance Criteria:**
- [ ] `src/api/routes/catalog.py` with routes:
  - `GET /api/catalog` — List templates from knowledge wiki with keyword search, returns `TemplateMetadata[]`
  - `GET /api/catalog/{name}` — Get template details + parameter schema
  - `POST /api/catalog/{name}/deploy` — Deploy a catalog template (accepts parameters, iac_language, target_repo)
- [ ] `src/api/schemas/catalog.py` — Pydantic request/response models
- [ ] Template search reads from `knowledge-wiki/templates/*/metadata.yaml`
- [ ] Deploy endpoint triggers the catalog path workflow
- [ ] Returns deployment_id for tracking

**Tech Details:**
- Templates loaded from git submodule path at runtime
- Search by keyword matches against name, description, azure_services, tags in metadata.yaml
- Ref: TechSpec Section 8.1, 8.2

---

### Issue #28 — Implement chat API endpoints + WebSocket streaming

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-9) | **Assignee:** E1
**Labels:** `backend`, `api`, `chat`
**Depends on:** #9, #14, #18
**Blocks:** #33

**Description:**
Implement the FastAPI routes and WebSocket endpoint for the chat interface: sending messages, receiving streaming responses, and handling human gate approvals.

**Acceptance Criteria:**
- [ ] `src/api/routes/chat.py` with routes:
  - `POST /api/chat` — Send message to consulting/codegen agents. Returns SSE stream with events: `assistant_message`, `stage_change`, `subscription_context`, `files_generated`, `approval_required`
  - `POST /api/chat/{conversation_id}/approve` — Human gate approval (H1 or H2)
  - `POST /api/chat/{conversation_id}/reject` — Human gate rejection with feedback text
  - `WS /ws/chat/{conversation_id}` — WebSocket for real-time streaming of chat + pipeline status
- [ ] `src/api/schemas/chat.py` — Pydantic models for request/response/SSE events
- [ ] SSE event types match TechSpec Section 8.2: assistant_message, stage_change, subscription_context, files_generated, approval_required, deployment_status
- [ ] Conversation persistence to database (create/retrieve)
- [ ] Message persistence to database
- [ ] Stage transitions emit real-time events

**Tech Details:**
- Use FastAPI `StreamingResponse` with `text/event-stream` for SSE
- WebSocket as alternative real-time transport
- Conversation ID auto-generated if not provided
- Ref: TechSpec Section 8.1, 8.2

---

### Issue #29 — Implement deployment API endpoints

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E4
**Labels:** `backend`, `api`, `deploy`
**Depends on:** #9, #11, #16
**Blocks:** #35

**Description:**
Implement the FastAPI routes for deployment tracking: status, plan output, generated files, and architecture diagram.

**Acceptance Criteria:**
- [ ] `src/api/routes/deployments.py` with routes:
  - `GET /api/deployments/{id}` — Full deployment status (stage, PR info, plan status, file count, diagram URL, timestamps)
  - `GET /api/deployments/{id}/plan` — Plan output text (terraform plan / bicep what-if)
  - `GET /api/deployments/{id}/files` — List of generated files with content
  - `GET /api/deployments/{id}/diagram` — Architecture diagram (Mermaid source or rendered SVG)
- [ ] `src/api/schemas/deployment.py` — Pydantic response models matching TechSpec Section 8.2 schemas
- [ ] Returns plan_error_category and rework_iteration for plan-failure rework visibility
- [ ] Deployment stages match `DeploymentStage` enum

**Tech Details:**
- Deployment response includes: id, conversation_id, path, iac_language, stage, project_type, subscription_id, pr info, plan info, diagram_url, files_count, timestamps
- Ref: TechSpec Section 8.2

---

### Issue #30 — Implement health, settings, and standards API endpoints

**Priority:** P0 | **Size:** S | **Week:** 2 (Day 6-7) | **Assignee:** E4
**Labels:** `backend`, `api`
**Depends on:** #9
**Blocks:** None

**Description:**
Implement supporting API endpoints for health checks, settings management, and standards viewing.

**Acceptance Criteria:**
- [ ] `GET /api/health` — Health check (no auth): backend status, database connectivity, Foundry connectivity
- [ ] `GET /api/standards` — Load current org standards (naming rules, tag rules, security policies) from knowledge wiki
- [ ] `src/api/middleware/cors.py` — CORS configuration for frontend origin
- [ ] `src/api/middleware/auth.py` — JWT / Entra ID auth middleware (optional for hackathon, required post-hackathon)

**Tech Details:**
- Standards loaded from `knowledge-wiki/standards/` at runtime
- Health endpoint checks: DB connection, MCP server reachability
- Ref: TechSpec Section 8.1

---

### Issue #31 — Implement composition root and dependency injection

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 6-7) | **Assignee:** E1
**Labels:** `backend`, `architecture`
**Depends on:** #10, #11, #12, #13, #14, #15, #16
**Blocks:** #28, #33

**Description:**
Implement the composition root (`src/main.py`) that wires all adapters, use cases, and routes together via constructor injection. No use case or adapter should directly import another — all wiring happens here.

**Acceptance Criteria:**
- [ ] `src/main.py` with `create_app()` function
- [ ] All infrastructure adapters instantiated: AzureOpenAIAdapter, TerraformAdapter, BicepAdapter, GitHubAdapter, PolicyAdapter, TemplateRegistryAdapter, SubscriptionDiscoveryAdapter, OpenTelemetryAdapter, PostgresAdapter
- [ ] `infra_providers` dict: `{"terraform": terraform, "bicep": bicep}`
- [ ] Use cases instantiated with port injection: `ConsultUseCase(llm=, templates=, subscription_discovery=, observability=)`, `GenerateUseCase(llm=, policy=, templates=, infra_providers=, observability=)`, `DeployUseCase(github=, infra_providers=, observability=)`
- [ ] FastAPI app created with all routes registered
- [ ] Configuration loaded from `src/config.py` (environment variables, Key Vault references)
- [ ] No domain or application layer module imports infrastructure directly

**Tech Details:**
- Configuration via environment variables or Azure App Configuration
- Key Vault references for secrets (GitHub PAT, API keys)
- Ref: TechSpec Section 2.2

---

## EPIC 5: Frontend

---

### Issue #32 — Scaffold frontend with Next.js + Tailwind + shadcn/ui

**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E3
**Labels:** `frontend`, `foundation`
**Depends on:** #1
**Blocks:** #33, #34, #35

**Description:**
Initialize the React/Next.js frontend with TypeScript, Tailwind CSS, and shadcn/ui component library. Set up routing, global state management, API client, and WebSocket client.

**Acceptance Criteria:**
- [ ] `frontend/` directory with Next.js 14+ app router
- [ ] TypeScript + Tailwind CSS + shadcn/ui configured
- [ ] Route structure: `/` (landing), `/chat`, `/chat/:conversationId`, `/catalog`, `/catalog/:templateName`, `/deployments/:id`, `/settings`
- [ ] `frontend/src/lib/api.ts` — Backend API client (fetch-based with error handling)
- [ ] `frontend/src/lib/ws.ts` — WebSocket client for real-time streaming
- [ ] `frontend/src/lib/types.ts` — Shared TypeScript interfaces matching backend schemas (Conversation, Deployment, Template, DeploymentStage, etc.)
- [ ] Global state management via Zustand or React Context + useReducer
- [ ] `AppState` interface: conversations, activeConversationId, activeDeployment, templates, catalogSearchQuery, settings, connectionStatus
- [ ] Landing page with two entry points: "Chat with InfraAgent" and "Self-Service Catalog"
- [ ] Dark/light theme support

**Tech Details:**
- Next.js app router (`app/` directory)
- API client connects to backend at configurable base URL
- WebSocket reconnection with exponential backoff
- Ref: TechSpec Section 10

---

### Issue #33 — Build Chat UI (ChatPanel + streaming + human gates)

**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 6-10) | **Assignee:** E3
**Labels:** `frontend`, `chat-ui`
**Depends on:** #28, #32
**Blocks:** #36

**Description:**
Build the complete chat interface including message history, streaming responses, stage transitions, subscription discovery display, code generation display, and human gate approval modals.

**Acceptance Criteria:**
- [ ] `ChatPanel.tsx` — Full chat interface with message history, markdown rendering, code blocks with syntax highlighting
- [ ] `MessageBubble.tsx` — User and assistant message bubbles with agent name labels
- [ ] `StreamingIndicator.tsx` — Animated indicator during LLM streaming
- [ ] `SubscriptionDiscoveryPanel.tsx` — Displays discovered subscription context: resource groups, VNets, naming patterns, quotas (inline in chat)
- [ ] **Stage transition visualization:** Progress bar or breadcrumb showing current pipeline stage (Consulting → Discovery → CodeGen → Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy)
- [ ] **SSE event handling:** assistant_message (streaming text), stage_change (update progress), subscription_context (render discovery panel), files_generated (render file explorer), approval_required (show approval modal)
- [ ] `ApprovalModal.tsx` — Human gate UI for H1 (code + diagram review) and H2 (plan review). Clear approve/reject buttons with feedback text area on reject
- [ ] `FileExplorer.tsx` — Tree view of generated `.tf`/`.bicep` files with syntax highlighting (Monaco or Prism)
- [ ] `DiagramViewer.tsx` — Renders Mermaid diagram as SVG with zoom/pan/export (download as SVG/PNG)
- [ ] `useChat.ts` hook — Manages conversation state, SSE connection, message sending
- [ ] IaC language selector (Terraform / Bicep) in chat header
- [ ] Chat input with multi-line support and send button

**Tech Details:**
- SSE via `EventSource` or `fetch` with `ReadableStream`
- Mermaid rendering via `mermaid` npm package (client-side SVG render)
- Syntax highlighting via `react-syntax-highlighter` or Monaco Editor
- Ref: TechSpec Section 10.2, 10.3

---

### Issue #34 — Build Self-Service Catalog UI

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-9) | **Assignee:** E3
**Labels:** `frontend`, `catalog-ui`
**Depends on:** #27, #32
**Blocks:** #36

**Description:**
Build the self-service catalog interface: searchable template grid, template detail view with parameter form, and one-click deploy.

**Acceptance Criteria:**
- [ ] `CatalogGrid.tsx` — Searchable grid of template cards. Each card shows: name, description, complexity badge (simple/moderate/complex), Azure service icons, IaC language tags
- [ ] Search bar with keyword filtering against template name, description, services, tags
- [ ] `TemplateCard.tsx` — Card component with hover preview
- [ ] `TemplateDetail.tsx` — Full template detail view: description, Azure services used, complexity, version, author
- [ ] `ParameterForm.tsx` — Dynamic form generated from `metadata.yaml` parameters: supports integer (with min/max), string (with allowed_values dropdown), boolean (toggle), with default values pre-filled. Org-level parameters (naming, tags) shown as auto-enforced (read-only)
- [ ] Deploy button: submits parameters + iac_language + target_repo → `POST /api/catalog/{name}/deploy`
- [ ] After deploy: redirects to `/deployments/{id}` to track progress
- [ ] `useCatalog.ts` hook — Manages template list, search, and deploy state
- [ ] Empty state for no search results

**Tech Details:**
- Parameter validation on client side matching metadata.yaml validation rules
- Complexity badges: simple (green), moderate (yellow), complex (red)
- Ref: TechSpec Section 10.3

---

### Issue #35 — Build Deployment Tracker UI

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 8-10) | **Assignee:** E3
**Labels:** `frontend`, `deployment-ui`
**Depends on:** #29, #32
**Blocks:** #36

**Description:**
Build the deployment tracking page showing pipeline stage progress, PR link, plan output, and deployment result.

**Acceptance Criteria:**
- [ ] `DeploymentTracker.tsx` — Full deployment detail page at `/deployments/:id`
- [ ] `PipelineStages.tsx` — Visual pipeline showing all stages as a horizontal stepper: Consulting → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy. Current stage highlighted, completed stages checked, failed stages marked red
- [ ] PR section: link to GitHub PR, branch name, PR status
- [ ] Plan section: plan output with syntax highlighting, resource counts (create/modify/destroy), plan error category if failed
- [ ] Plan-failure rework indicator: shows rework iteration count (Loop 2), error category, CodeGen rework status
- [ ] Deploy section: deployment progress, success/failure status
- [ ] File explorer (reused from chat) for viewing generated code
- [ ] Diagram viewer (reused from chat) for architecture diagram
- [ ] Real-time updates via WebSocket polling of `GET /api/deployments/{id}`
- [ ] `useDeployment.ts` hook — Manages deployment state with polling
- [ ] Destructive change warning: prominent UI warning if plan shows resource destruction

**Tech Details:**
- Poll deployment status every 3-5 seconds during active stages
- Plan output formatted with color coding for +/- changes
- Ref: TechSpec Section 10.3

---

## EPIC 6: Subscription Discovery

---

### Issue #36a — Implement Subscription Discovery adapter

**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-9) | **Assignee:** E1
**Labels:** `backend`, `adapter`, `azure`
**Depends on:** #4, #20
**Blocks:** #14, #33

**Description:**
Implement the `ISubscriptionDiscoveryPort` adapter that connects to Azure subscriptions via Azure MCP Server to inventory existing resources, VNets, naming patterns, quotas, and state backends.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/subscription_discovery_adapter.py` implementing `ISubscriptionDiscoveryPort`
- [ ] `discover(subscription_id)` returns `SubscriptionContext` with:
  - `resource_groups` — List of existing resource groups
  - `resources` — List of `DiscoveredResource` (resource_group, type, name, location, tags)
  - `vnets` — List of `DiscoveredVNet` (name, resource_group, address_space, subnets with address_prefix)
  - `naming_patterns` — Detected patterns (e.g., "rg-{env}-{app}-{region}") inferred from existing resource names
  - `quotas` — Resource type quotas with used/limit
  - `state_backends` — Detected Terraform state storage accounts
  - `available_regions` — Available Azure regions for the subscription
- [ ] `check_sku_availability(subscription_id, resource_type, sku, region)` — Validates SKU availability
- [ ] `check_quota(subscription_id, resource_type, region)` — Returns quota usage
- [ ] Uses Azure MCP Server for all queries
- [ ] Naming pattern detection: regex inference from existing resource names

**Tech Details:**
- Azure MCP tools: list resource groups, list resources, get VNet details, check quotas
- Naming pattern detection: group resources by type, find common prefixes/patterns
- Ref: TechSpec Section 2.1 (ISubscriptionDiscoveryPort), PRD Section 7.1.1

---

## EPIC 7: Integration & End-to-End

---

### Issue #36 — End-to-end integration: Chat path (Demo 1)

**Priority:** P0 | **Size:** XL | **Week:** 2-3 (Day 9-13) | **Assignee:** E1 + E3
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #18, #22, #23, #24, #25, #26, #28, #33
**Blocks:** #39

**Description:**
Wire everything together for the chat path end-to-end: user sends message → Consulting Agent gathers requirements → subscription discovery → CodeGen generates Bicep/Terraform (AVM-first) → IaC Validation Pipeline → Standards → Security → H1 approval → PR created → plan runs → H2 approval → deploy succeeds.

**Acceptance Criteria:**
- [ ] User types "I need a 3-tier web app with App Service, SQL Database, and a VNet" in chat
- [ ] Consulting Agent asks 2-3 clarifying questions (environment, region, sizing)
- [ ] Subscription discovery runs and surfaces existing resources
- [ ] CodeGen generates modular IaC code using AVM modules
- [ ] IaC Validation Pipeline passes (fmt + validate + lint)
- [ ] Standards validates naming/tags — passes
- [ ] Security scans — passes
- [ ] H1 gate shows code + Mermaid architecture diagram for review
- [ ] PR is created in target repo
- [ ] GitHub Actions runs plan
- [ ] H2 gate shows plan output for review
- [ ] Deployment succeeds
- [ ] All stage transitions visible in real-time on frontend
- [ ] E2E test in `tests/e2e/test_chat_to_deploy.py`

**Tech Details:**
- This is Demo 1 from PRD Section 12.1
- Target: < 3 minutes from first message to open PR
- Ref: PRD Section 5.1 (full journey), Section 12.1 (demo script)

---

### Issue #37 — End-to-end integration: Catalog path (Demo 2)

**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 10-13) | **Assignee:** E4 + E3
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #19, #25, #26, #27, #34
**Blocks:** #39

**Description:**
Wire everything together for the catalog path end-to-end: user browses catalog → selects AKS template → fills parameters → subscription discovery (lightweight) → hydrate template → validate → H1 → PR → plan → H2 → deploy.

**Acceptance Criteria:**
- [ ] User opens catalog, searches "AKS cluster"
- [ ] Template detail view shows parameters (node_count, vm_size, kubernetes_version, etc.)
- [ ] User fills parameters and clicks deploy
- [ ] Subscription discovery verifies target resource group, checks naming conflicts and quota
- [ ] Template hydrated with org naming/tags applied by Standards Agent
- [ ] IaC Validation Pipeline runs (terraform validate on hydrated code)
- [ ] H1 gate shows parameterized code for review
- [ ] PR created, plan runs, H2 approval, deployment succeeds
- [ ] Significantly faster than chat path (target: < 1 minute to open PR)

**Tech Details:**
- This is Demo 2 from PRD Section 12.1
- Catalog path skips consulting, iterative codegen/standards/security loops
- Ref: PRD Section 5.2 (full journey), Section 12.1 (demo script)

---

### Issue #38 — End-to-end integration: Plan failure + rework (Demo 3)

**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 11-14) | **Assignee:** E4 + E2
**Labels:** `integration`, `e2e`, `demo`
**Depends on:** #26, #36
**Blocks:** #39

**Description:**
Wire and test the plan-failure rework loop end-to-end: user requests AKS cluster → code generated → plan fails (SKU unavailable) → Deploy Agent categorizes error → CodeGen reworks code → re-validates → new PR → plan succeeds → deploy.

**Acceptance Criteria:**
- [ ] User requests AKS cluster via chat
- [ ] CodeGen generates Terraform code (intentionally using a SKU that will fail in target region)
- [ ] Validation pipeline passes, standards pass, security passes
- [ ] H1 approved, PR created
- [ ] `terraform plan` fails: "VM size Standard_D4s_v3 not available in westeurope"
- [ ] Deploy Agent categorizes failure as `sku_unavailable`
- [ ] Error output fed back to CodeGen with original requirements + current code
- [ ] CodeGen queries Azure MCP for available SKUs, updates VM size
- [ ] Code re-enters validation pipeline → passes
- [ ] New PR created, plan succeeds
- [ ] H2 approval, deployment succeeds
- [ ] UI shows plan-failure rework iteration indicator

**Tech Details:**
- This is Demo 3 from PRD Section 12.1
- Loop 2: max 2 iterations of plan-failure rework
- Error categories handled: resource_conflict, sku_unavailable, provider_mismatch, module_error
- Non-fixable errors (quota_exceeded, auth_failure) escalated to user
- Ref: PRD Section 6.2.1, Section 12.1 (demo script)

---

## EPIC 8: Polish & Demo Preparation

---

### Issue #39 — Demo script rehearsal and edge case hardening

**Priority:** P0 | **Size:** L | **Week:** 3 (Day 13-15) | **Assignee:** ALL
**Labels:** `demo`, `polish`
**Depends on:** #36, #37, #38

**Description:**
Rehearse all 3 demo scenarios end-to-end against real Azure subscription. Identify and fix edge cases, timing issues, and UI polish items.

**Acceptance Criteria:**
- [ ] Demo 1 (Chat path — 3-4 min) runs successfully end-to-end against real Azure subscription
- [ ] Demo 2 (Catalog path — 1-2 min) runs successfully end-to-end
- [ ] Demo 3 (Plan failure + rework — 2-3 min) runs successfully end-to-end
- [ ] Subscription discovery surfaces real resources in demo subscription
- [ ] Architecture diagrams render correctly for all demo scenarios
- [ ] Edge cases handled: network timeouts, MCP server unavailability (graceful degradation), GitHub Actions delays
- [ ] UI polished: loading states, error messages, stage transition animations
- [ ] Recording backup prepared (screen recording of successful demo run)

**Tech Details:**
- Use a dedicated demo Azure subscription with pre-existing resources
- Pre-seed subscription with a VNet, resource groups so discovery has data to show
- Ref: PRD Section 12.1

---

### Issue #40 — UI polish and responsive design

**Priority:** P0 | **Size:** M | **Week:** 3 (Day 13-14) | **Assignee:** E3
**Labels:** `frontend`, `polish`
**Depends on:** #33, #34, #35

**Description:**
Final UI polish pass: loading states, error handling, responsive layout, keyboard shortcuts, and visual consistency.

**Acceptance Criteria:**
- [ ] Consistent loading skeletons on all data-fetching components
- [ ] Error boundaries with user-friendly error messages
- [ ] Responsive layout that works on 13" laptop screens (primary demo device)
- [ ] Keyboard shortcut: Enter to send message, Cmd+Enter for new line
- [ ] Copy-to-clipboard on code blocks
- [ ] Proper empty states on all list views
- [ ] Favicon and page titles set
- [ ] Stage transition animations (smooth progress bar movement)
- [ ] Plan output color coding (green for create, yellow for modify, red for destroy)
- [ ] Destructive change warning prominently displayed

---

## EPIC 9: Observability

---

### Issue #41 — Implement observability adapter (OpenTelemetry + App Insights)

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E1
**Labels:** `backend`, `observability`
**Depends on:** #4, #5

**Description:**
Implement the `IObservabilityPort` adapter wrapping OpenTelemetry for tracing, metrics, and logging. Export to Azure App Insights.

**Acceptance Criteria:**
- [ ] `src/infrastructure/adapters/otel_adapter.py` implementing `IObservabilityPort`
- [ ] `start_span(name, attributes)` — Creates OpenTelemetry spans for tracing
- [ ] `record_metric(name, value, tags)` — Records custom metrics
- [ ] `log(level, message, **kwargs)` — Structured logging
- [ ] Trace hierarchy per TechSpec Section 14.1: API route → use case → LLM call → MCP tool call
- [ ] Key metrics instrumented: `infraagent.chat.latency`, `infraagent.generate.iterations`, `infraagent.prs_created`, `infraagent.deployments_triggered`, `infraagent.token_usage`, `infraagent.mcp.call_latency`
- [ ] Export to Azure App Insights via OpenTelemetry collector
- [ ] Connection string from environment variable

**Tech Details:**
- Use `opentelemetry-api`, `opentelemetry-sdk`, `azure-monitor-opentelemetry-exporter`
- Ref: TechSpec Section 14

---

## EPIC 10: P1 Stretch Features

---

### Issue #42 — Template Curation Agent (post-deploy feedback loop)

**Priority:** P1 | **Size:** XL | **Week:** 3 (stretch) | **Assignee:** E5
**Labels:** `agents`, `knowledge-wiki`, `p1-stretch`
**Depends on:** #36

**Description:**
Implement the Template Curation Agent that runs post-deployment to analyze deployed custom code, check novelty against existing wiki templates, generalize parameters, and propose a new template via PR to the knowledge wiki repo.

**Acceptance Criteria:**
- [ ] Post-deploy trigger: after successful deployment via chat path, Template Curation Agent is invoked
- [ ] Novelty check: compares deployed resources against existing wiki templates
- [ ] Parameter generalization: extracts hardcoded values into configurable parameters
- [ ] Generates `metadata.yaml` for the proposed template
- [ ] Opens PR to the knowledge wiki repo (not InfraAgent repo) with the proposed template
- [ ] **Human Gate H3:** Platform engineer reviews and approves the template PR
- [ ] Approved templates automatically appear in the self-service catalog after submodule update

**Tech Details:**
- Template Curation Agent uses ModelRouter profile `code-generation`
- Uses GitHub MCP for PR creation to wiki repo
- Ref: PRD Section 7.2, TechSpec Section 5.1

---

### Issue #43 — Conversation memory persistence

**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E1
**Labels:** `backend`, `p1-stretch`
**Depends on:** #9, #28

**Description:**
Persist chat history across sessions so users can return to previous conversations and resume where they left off.

**Acceptance Criteria:**
- [ ] Conversations saved to PostgreSQL `conversations` + `messages` tables
- [ ] Chat UI shows conversation list sidebar with recent conversations
- [ ] User can click a previous conversation to reload history and continue
- [ ] Conversation title auto-generated from first user message

---

### Issue #44 — Cost estimation integration

**Priority:** P1 | **Size:** L | **Week:** 3 (stretch) | **Assignee:** E2
**Labels:** `backend`, `p1-stretch`
**Depends on:** #15

**Description:**
Integrate Infracost (Terraform) or Azure Pricing Calculator API to show estimated monthly cost before deployment.

**Acceptance Criteria:**
- [ ] For Terraform: run `infracost breakdown --path <dir>` on generated code
- [ ] Cost estimate shown alongside plan output at H2 review
- [ ] Monthly cost breakdown by resource

---

### Issue #45 — Set Diff Analyzer for plan review

**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E4
**Labels:** `backend`, `deploy`, `p1-stretch`
**Depends on:** #26

**Description:**
Filter false-positive diffs in Terraform plan output caused by AzureRM Set-type attribute reordering, reducing noise in H2 review.

**Acceptance Criteria:**
- [ ] Categorize changes: 🟢 order-only (safe to ignore), 🟡 actual Set changes (review content), 🔴 resource replacement (check downtime impact)
- [ ] Frontend `PlanDiffViewer.tsx` shows filtered view by default with option to show all
- [ ] Particularly relevant for Application Gateway backend pools, NSG security rules

**Tech Details:**
- Parse `terraform plan -json` output, detect Set-type attributes, compare element content ignoring order
- Ref: PRD Section 7.1.8

---

### Issue #46 — IaC language toggle mid-conversation

**Priority:** P1 | **Size:** S | **Week:** 3 (stretch) | **Assignee:** E3
**Labels:** `frontend`, `p1-stretch`
**Depends on:** #33

**Description:**
Allow user to switch between Terraform and Bicep mid-conversation. CodeGen agent adapts to the new language.

**Acceptance Criteria:**
- [ ] Language toggle in chat header (Terraform / Bicep)
- [ ] Switching language re-triggers code generation in the new language
- [ ] Previous code is not lost — shown as "previous version" in file explorer

---

### Issue #47 — Settings page (Azure + GitHub connection config)

**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E3
**Labels:** `frontend`, `settings`
**Depends on:** #32

**Description:**
Build the settings page for configuring Azure subscription, GitHub repo, and connection details.

**Acceptance Criteria:**
- [ ] `/settings` page with form fields: Azure subscription ID, Azure tenant ID, GitHub PAT (masked), GitHub repo, default branch
- [ ] Connection test buttons: verify Azure subscription access, verify GitHub repo access, verify Foundry connectivity
- [ ] Connection status indicators on the main layout (green/red dots for Azure, GitHub, Foundry)
- [ ] Settings persisted to database `settings` table
- [ ] Secrets (GitHub PAT) stored encrypted in Key Vault, not in database

---

---

## Summary: Issue Dependency & Parallelization Map

### Week 1 (Foundation) — 17 issues, high parallelism

| Day | E1 (Agent Backend) | E2 (CodeGen+Validation) | E3 (Frontend) | E4 (GitHub+Deploy) | E5 (Wiki+Infra) |
|-----|---------------------|-------------------------|---------------|--------------------|--------------------|
| 1-2 | #1 (repo), #4 (ports) | #2 (models), #3 (policies) | #32 (scaffold FE) | #6 (CI/CD) | #5 (Azure infra), #7 (wiki repo) |
| 3-5 | #10 (LLM adapter), #20 (MCP config) | #12 (TF adapter), #13 (Bicep adapter), #21 (prompts) | #32 (cont.) | #9 (DB schema), #11 (GitHub adapter) | #5 (cont.), #8 (templates) |

### Week 2 (Integration) — 20 issues, moderate parallelism

| Day | E1 (Agent Backend) | E2 (CodeGen+Validation) | E3 (Frontend) | E4 (GitHub+Deploy) | E5 (Wiki+Infra) |
|-----|---------------------|-------------------------|---------------|--------------------|--------------------|
| 6-8 | #14 (ConsultUC), #17 (agent reg), #31 (DI) | #15 (GenerateUC), #22 (validation), #23 (standards) | #33 (chat UI), #34 (catalog UI) | #16 (DeployUC), #25 (PR agent), #27 (catalog API) | #8 (cont.) |
| 8-10 | #18 (chat workflow), #28 (chat API), #41 (otel) | #24 (security), #15 (cont.) | #33 (cont.), #35 (deploy tracker), #47 (settings) | #26 (deploy agent), #29 (deploy API), #30 (health API) | #36a (sub discovery) |

### Week 3 (Polish + Demo) — 8 issues, sequential focus

| Day | E1 | E2 | E3 | E4 | E5 |
|-----|-----|-----|-----|-----|------|
| 11-12 | #36 (E2E chat), #19 (catalog workflow) | #38 (E2E plan fail) | #36 (E2E chat - FE), #37 (E2E catalog) | #37 (E2E catalog), #38 (E2E plan fail) | #42 (P1: curation agent) |
| 13-15 | #39 (demo rehearsal), #43 (P1: memory) | #39 (demo rehearsal), #44 (P1: cost) | #39 (demo rehearsal), #40 (UI polish) | #39 (demo rehearsal), #45 (P1: set diff) | #39 (demo rehearsal) |

### Critical Path

```
#1 → #4 → #10 → #14 → #18 → #28 → #36 → #39
           ↓
      #12/#13 → #15 → #22 → #33 → #36
           ↓
      #11 → #16 → #25/#26 → #37/#38
```

The critical path runs through: repo setup → port interfaces → LLM adapter → use cases → orchestrator workflows → API endpoints → E2E integration → demo rehearsal.

---

## Issue Count Summary

| Category | P0 (MVP) | P1 (Stretch) | Total |
|----------|----------|--------------|-------|
| Setup & Infrastructure | 9 | 0 | 9 |
| Agent Backend & Foundry | 12 | 0 | 12 |
| Agent Implementation | 5 | 0 | 5 |
| Backend API | 4 | 0 | 4 |
| Frontend | 6 | 1 | 7 |
| Subscription Discovery | 1 | 0 | 1 |
| Integration & E2E | 3 | 0 | 3 |
| Polish & Demo | 2 | 0 | 2 |
| Observability | 1 | 0 | 1 |
| P1 Stretch | 0 | 5 | 5 |
| **Total** | **43** | **6** | **49** |