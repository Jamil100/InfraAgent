#!/usr/bin/env python3
"""
create_github_issues.py
-----------------------
Creates all 55 InfraAgent backlog issues in GitHub, adds them to the
InfraAgent Roadmap project, then patches every issue body so that
"REF #X" placeholders become real clickable "#N" cross-references.

Usage:
    python create_github_issues.py
"""

import subprocess
import time
import sys
import re
import json
import tempfile
import os

OWNER          = "Jamil100"
REPO           = "InfraAgent"

# Use the OS temp directory (works on both Windows and Unix)
_TMP = tempfile.gettempdir()
BODY_FILE        = os.path.join(_TMP, "_ib.md")
BODY_PATCH_FILE  = os.path.join(_TMP, "_ib_patch.md")
PROJECT_NUMBER = 1

# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: str) -> tuple[str, int]:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr.strip():
        print(f"  [warn] {r.stderr.strip()[:120]}", file=sys.stderr)
    return r.stdout.strip(), r.returncode


def create_label(name: str, color: str) -> None:
    run(f'gh label create "{name}" --color "{color}" --repo {OWNER}/{REPO} --force')


def get_existing_issues() -> dict[str, int]:
    """Return {title: issue_number} for every issue already in the repo."""
    out, _ = run(f'gh issue list --repo {OWNER}/{REPO} --state all --limit 200 --json number,title')
    try:
        return {item["title"]: item["number"] for item in json.loads(out)}
    except Exception:
        return {}


def create_issue(title: str, body: str, labels: list[str], existing: dict[str, int]) -> int | None:
    if title in existing:
        num = existing[title]
        print(f"    → already exists as #{num}, skipping creation")
        return num

    with open(BODY_FILE, "w", encoding="utf-8") as f:
        f.write(body)

    label_args = " ".join(f'--label "{l}"' for l in labels)
    url, code = run(f'gh issue create --title "{title}" --body-file "{BODY_FILE}" {label_args} --repo {OWNER}/{REPO}')

    if code == 0 and url.startswith("http"):
        return int(url.rstrip("/").split("/")[-1])

    print(f"    [ERROR] could not create: {title[:80]}")
    return None


def add_to_project(issue_number: int) -> None:
    url = f"https://github.com/{OWNER}/{REPO}/issues/{issue_number}"
    run(f'gh project item-add {PROJECT_NUMBER} --owner {OWNER} --url "{url}"')


def patch_body(issue_number: int, body: str) -> None:
    with open(BODY_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write(body)
    run(f'gh issue edit {issue_number} --body-file "{BODY_PATCH_FILE}" --repo {OWNER}/{REPO}')


def resolve_refs(text: str, ref_map: dict[str, int]) -> str:
    """Replace every 'REF #X' token with the real '#N' GitHub issue number."""
    def _sub(m: re.Match) -> str:
        key = m.group(1)            # e.g. "1", "46a"
        actual = ref_map.get(key)
        return f"#{actual}" if actual else m.group(0)
    return re.sub(r"REF #(\w+)", _sub, text)


# ── label catalogue ───────────────────────────────────────────────────────────

LABELS: list[tuple[str, str]] = [
    ("setup",             "0075ca"), ("backend",          "e4e669"),
    ("foundation",        "d4c5f9"), ("domain",           "bfd4f2"),
    ("architecture",      "c2e0c6"), ("infrastructure",   "f9d0c4"),
    ("bicep",             "0e8a16"), ("azure",            "1d76db"),
    ("ci-cd",             "e99695"), ("devops",           "fef2c0"),
    ("knowledge-wiki",    "d93f0b"), ("templates",        "c5def5"),
    ("iac",               "bfd4f2"), ("database",         "6f42c1"),
    ("ai-foundry",        "e11d48"), ("adapter",          "c2e0c6"),
    ("terraform",         "006b75"), ("use-case",         "84b6eb"),
    ("consulting-agent",  "fbca04"), ("codegen-agent",    "84b6eb"),
    ("deploy-agent",      "c5def5"), ("validation",       "fef2c0"),
    ("pipeline",          "d93f0b"), ("orchestrator",     "bfd4f2"),
    ("agents",            "e4e669"), ("prompts",          "f9d0c4"),
    ("mcp",               "c2e0c6"), ("integration",      "0075ca"),
    ("standards",         "e11d48"), ("security",         "b60205"),
    ("deploy",            "fbca04"), ("api",              "84b6eb"),
    ("chat",              "c5def5"), ("catalog",          "fef2c0"),
    ("diagram",           "d93f0b"), ("frontend",         "0e8a16"),
    ("ai-search",         "1d76db"), ("e2e",              "e99695"),
    ("demo",              "d4c5f9"), ("observability",    "bfd4f2"),
    ("polish",            "e4e669"), ("docs",             "c2e0c6"),
    ("p1-stretch",        "fbca04"), ("resilience",       "84b6eb"),
    ("settings",          "c5def5"), ("catalog-ui",       "fef2c0"),
    ("deployment-ui",     "d93f0b"), ("chat-ui",          "e99695"),
]

# ── issue definitions ─────────────────────────────────────────────────────────
# Each entry: ref (str key matching "REF #X"), title, labels, body.
# Bodies use "REF #X" for cross-references — these are resolved to real GitHub
# issue numbers in the second pass.

ISSUES: list[dict] = [

  # ════════════════════════════════════════════════════════════
  # EPIC 1: Project Setup & Infrastructure Foundation
  # ════════════════════════════════════════════════════════════
  { "ref": "1",
    "title": "[EPIC 1][REF #1] Initialize monorepo with clean architecture project structure",
    "labels": ["setup", "backend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1) | **Assignee:** E1
**Blocks:** REF #2, REF #3, REF #4, REF #5, REF #6, REF #7, REF #8, REF #9, REF #10, REF #11, REF #12, REF #13, REF #14, REF #15, REF #16

## Description
Create the InfraAgent monorepo with the full clean architecture directory structure defined in TechSpec Section 11.

## Acceptance Criteria
- [ ] Repository initialized with `src/domain/`, `src/application/`, `src/infrastructure/`, `src/api/`, `src/prompts/`, `frontend/`, `infra/`, `tests/`, `.github/workflows/`
- [ ] `pyproject.toml` configured with Python 3.12, dependencies (fastapi, uvicorn, azure-ai-projects, azure-identity, sqlalchemy[asyncio], asyncpg, pydantic, ruff, mypy, pytest, pytest-asyncio, httpx)
- [ ] `ruff` and `mypy` configured per TechSpec Section 16.1
- [ ] `Dockerfile` and `docker-compose.yml` scaffolded (backend + postgres)
- [ ] `.gitignore` for Python, Node, Terraform, Bicep artifacts
- [ ] Empty `__init__.py` files in all Python packages
- [ ] `README.md` with project overview and setup instructions
- [ ] `.env.example` with all environment variables documented

## Tech Details
- Follow project structure from TechSpec Section 11 exactly
- Use `pyproject.toml` with `[project.optional-dependencies] dev = [...]` for dev deps
- Python 3.12+ required (Foundry SDK dependency)
""" },

  { "ref": "2",
    "title": "[EPIC 1][REF #2] Define domain layer models and enums",
    "labels": ["domain", "backend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E2
**Depends on:** REF #1
**Blocks:** REF #10, REF #14, REF #15, REF #16, REF #17

## Description
Implement all domain models, enums, and dataclasses from TechSpec Section 3.1. Pure Python with zero external dependencies.

## Acceptance Criteria
- [ ] `src/domain/models/deployment.py` — `DeploymentStage` (14 stages: CONSULTING, DISCOVERING_SUBSCRIPTION, GENERATING, VALIDATING_IAC, VALIDATING_STANDARDS, SCANNING_SECURITY, AWAITING_CODE_REVIEW, CREATING_PR, RUNNING_PLAN, REWORKING_PLAN_FAILURE, AWAITING_PLAN_REVIEW, DEPLOYING, DEPLOYED, FAILED, CANCELLED), `ProjectType`, `IaCLanguage`, `DeploymentPath`, `GeneratedFile`, `DeploymentRequest`, `Conversation`
- [ ] `src/domain/models/template.py` — `TemplateMetadata`, `HydratedTemplate` dataclasses
- [ ] All enums match PRD Section 6 and TechSpec Section 3.1 exactly
- [ ] Zero imports from `azure`, `openai`, `fastapi`, or any third-party package
- [ ] Unit tests in `tests/unit/domain/test_models.py`

## Tech Details
- Use Python `dataclasses` and `enum.Enum` (no Pydantic in domain layer)
- Ref: TechSpec Section 3.1
""" },

  { "ref": "3",
    "title": "[EPIC 1][REF #3] Implement domain policies (naming, tagging, security)",
    "labels": ["domain", "backend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 2-3) | **Assignee:** E2
**Depends on:** REF #1
**Blocks:** REF #23, REF #24, REF #28

## Description
Implement deterministic business rule validators for naming conventions, required tags, and security policy checks as pure functions in the domain layer.

## Acceptance Criteria
- [ ] `src/domain/policies/naming_policy.py` — `NamingRule` dataclass, `DEFAULT_NAMING_RULES` (rg, vnet, snet, vm, storage, nsg patterns), `validate_resource_name()` pure function
- [ ] `src/domain/policies/tagging_policy.py` — `TagRule` dataclass, `DEFAULT_REQUIRED_TAGS` (environment, owner, cost-center, application, created-by), `validate_tags()` pure function
- [ ] `src/domain/policies/security_policy.py` — `SECURITY_RULES` list (SEC-001 through SEC-007)
- [ ] `src/domain/services/standards_service.py` — `StandardsViolation`, `StandardsResult`, `validate_standards()` orchestrating naming + tagging checks
- [ ] 100% unit test coverage in `tests/unit/domain/`
- [ ] All functions are pure — no I/O, no LLM calls, no external dependencies

## Tech Details
- Naming patterns use regex (e.g., `^rg-\\w+-\\w+-\\w+$`)
- Tags with enforcement "required" must be present; "auto" are system-injected
- Ref: TechSpec Section 3.2, 3.3
""" },

  { "ref": "4",
    "title": "[EPIC 1][REF #4] Define all port interfaces (application layer contracts)",
    "labels": ["architecture", "backend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E1
**Depends on:** REF #1
**Blocks:** REF #10, REF #11, REF #12, REF #13, REF #14, REF #15, REF #16, REF #17, REF #28, REF #29

## Description
Define all abstract port interfaces in the application layer — the contracts between layers.

## Acceptance Criteria
- [ ] `src/application/ports/llm_port.py` — `LLMMessage`, `LLMResponse`, `ToolDefinition`, `TaskProfile` + `ILLMCompletionPort` ABC with `complete()` and `complete_with_tools()`
- [ ] `src/application/ports/infra_provider_port.py` — `ValidationResult`, `PlanResult`, `ApplyResult` + `IInfraProviderPort` ABC
- [ ] `src/application/ports/source_control_port.py` — `PRResult`, `PipelineStatus` + `ISourceControlPort` ABC
- [ ] `src/application/ports/policy_engine_port.py` — `PolicyViolation`, `PolicyResult` + `IPolicyEnginePort` ABC
- [ ] `src/application/ports/template_registry_port.py` — `ITemplateRegistryPort` ABC
- [ ] `src/application/ports/subscription_discovery_port.py` — `DiscoveredResource`, `DiscoveredVNet`, `SubscriptionContext` + `ISubscriptionDiscoveryPort` ABC
- [ ] `src/application/ports/observability_port.py` — `IObservabilityPort` ABC
- [ ] All ports use `async` methods and Python ABCs; no implementation details

## Tech Details
- `TaskProfile.profile` values: "complex-reasoning", "code-generation", "analysis", "fast-lightweight", "orchestration"
- `LLMResponse` includes `model_used: str | None`
- Ref: TechSpec Section 2.1
""" },

  { "ref": "5",
    "title": "[EPIC 1][REF #5] Implement IaC parser for HCL/Bicep resource extraction",
    "labels": ["domain", "backend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 3-4) | **Assignee:** E2
**Depends on:** REF #1, REF #2
**Blocks:** REF #23, REF #24

## Description
Implement `src/domain/services/iac_parser.py` — parses raw HCL (Terraform) and Bicep text into structured resource models.

## Acceptance Criteria
- [ ] `parse_terraform_resources(hcl_content: str) -> list[dict]` — Extracts resource type, name, tags, key attributes from HCL resource blocks
- [ ] `parse_bicep_resources(bicep_content: str) -> list[dict]` — Extracts resource type, name, tags, key attributes from Bicep resource declarations
- [ ] Handles multi-file parsing: accepts list of `GeneratedFile`, returns aggregated resource list
- [ ] Detects AVM module usage vs raw resource declarations
- [ ] Detects explicit `depends_on` declarations
- [ ] Detects `sensitive = true` on variables/outputs (Terraform) and `@secure()` decorators (Bicep)
- [ ] Pure domain function — no external dependencies (regex + string parsing only)
- [ ] Unit tests with sample HCL and Bicep files

## Tech Details
- HCL: regex extraction of `resource "type" "name" { ... }` blocks
- Bicep: regex extraction of `resource name 'Microsoft.Type/resource@version' = { ... }` blocks
""" },

  { "ref": "6",
    "title": "[EPIC 1][REF #6] Provision Azure infrastructure via Bicep (InfraAgent self-deployment)",
    "labels": ["infrastructure", "bicep", "azure"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 1-4) | **Assignee:** E5
**Blocks:** REF #20, REF #21, REF #30

## Description
Create Bicep modules to deploy all Azure resources InfraAgent needs. This is dogfooding — InfraAgent's own infra is IaC.

## Acceptance Criteria
- [ ] `infra/main.bicep` — Root orchestration module
- [ ] `infra/modules/foundry.bicep` — Azure AI Foundry resource + project
- [ ] `infra/modules/postgres.bicep` — Azure PostgreSQL Flexible Server (Burstable B1ms)
- [ ] `infra/modules/appService.bicep` — App Service (B2)
- [ ] `infra/modules/staticWebApp.bicep` — Static Web App for React frontend
- [ ] `infra/modules/keyVault.bicep` — Key Vault with `enableRbacAuthorization: true`, `enablePurgeProtection: true`, `enableSoftDelete: true`
- [ ] `infra/modules/aiSearch.bicep` — Azure AI Search (Basic)
- [ ] `infra/modules/functionApp.bicep` — Azure Functions (Consumption)
- [ ] `infra/modules/monitoring.bicep` — App Insights + Log Analytics workspace
- [ ] `infra/parameters/dev.bicepparam` and `infra/parameters/prod.bicepparam`
- [ ] Managed Identity used for all service-to-service auth
- [ ] All modules validate with `bicep build`

## Tech Details
- SKUs per TechSpec Section 12.1; estimated cost ~$225-275/month
- Ref: TechSpec Section 12
""" },

  { "ref": "7",
    "title": "[EPIC 1][REF #7] Set up CI/CD pipelines (GitHub Actions)",
    "labels": ["ci-cd", "devops"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 2-3) | **Assignee:** E4
**Depends on:** REF #1
**Blocks:** REF #32, REF #33

## Description
Create GitHub Actions workflows for InfraAgent's own CI/CD: linting, testing, and deployment.

## Acceptance Criteria
- [ ] `.github/workflows/ci.yml` — On PR: checkout (submodules: recursive), setup Python 3.12 + uv, `uv sync --extra dev`, `ruff check`, `ruff format --check`, `mypy src/`, `pytest tests/unit/ -v`, `pytest tests/integration/ -v -m "not slow"`
- [ ] `.github/workflows/deploy-infra.yml` — Bicep deployment (manual trigger + on push to `infra/`)
- [ ] `.github/workflows/deploy-app.yml` — Backend Docker build + push to ACR + deploy to App Service; Frontend build + deploy to Static Web Apps
- [ ] All workflows use proper secret references: `AZURE_CREDENTIALS`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`

## Tech Details
- Use `actions/checkout@v4`, `astral-sh/setup-uv@v4`, `actions/setup-node@v4`
- Ref: TechSpec Section 13.1
""" },

  { "ref": "8",
    "title": "[EPIC 1][REF #8] Create knowledge wiki repository and wire as git submodule",
    "labels": ["knowledge-wiki", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 1-3) | **Assignee:** E5
**Depends on:** REF #1
**Blocks:** REF #9, REF #22, REF #23, REF #30

## Description
Create the separate `infraagent-wiki` GitHub repository with the full directory structure and wire it as a git submodule at `knowledge-wiki/`.

## Acceptance Criteria
- [ ] Separate GitHub repo `infraagent-wiki` with structure: `templates/`, `skills/`, `standards/`, `patterns/`
- [ ] `standards/naming.md`, `standards/tagging.md`, `standards/policies.md`
- [ ] `skills/general-azure/SKILL.md` with phase-specific questions, pattern catalogs, readiness checklists
- [ ] `patterns/adr/` — At least one ADR (e.g., `001-mcp-over-direct-api.md`)
- [ ] `.gitmodules` in InfraAgent repo pointing to `infraagent-wiki` at `knowledge-wiki/`
- [ ] Wiki repo has its own CI that validates template syntax and checks `metadata.yaml` schema
- [ ] `metadata.yaml` JSON schema defined and documented
- [ ] Submodule pinned to a release tag (e.g., `v0.1.0`)

## Tech Details
- Template `metadata.yaml` schema per PRD Section 8.2
- Ref: PRD Section 8, TechSpec Section 7
""" },

  { "ref": "9",
    "title": "[EPIC 1][REF #9] Author 3 starter templates for knowledge wiki",
    "labels": ["knowledge-wiki", "templates", "iac"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 1 (Day 2-5) | **Assignee:** E5
**Depends on:** REF #8
**Blocks:** REF #30, REF #38

## Description
Create at least 3 pre-validated, AVM-first IaC templates in both Terraform and Bicep for the self-service catalog.

## Acceptance Criteria
- [ ] `templates/aks-cluster/` — AKS cluster with managed identity, Azure CNI, monitoring. Terraform + Bicep. Parameters: node_count, vm_size, kubernetes_version, enable_monitoring, network_plugin
- [ ] `templates/3-tier-web-app/` — App Service + SQL Database + VNet. Terraform + Bicep. Parameters: app_service_sku, sql_tier, region
- [ ] `templates/static-website-cdn/` — Storage Account + CDN + custom domain. Terraform + Bicep. Parameters: cdn_sku, storage_replication
- [ ] All templates use AVM modules where available
- [ ] All templates have proper `metadata.yaml` per schema
- [ ] All Terraform templates pass `terraform fmt -check`, `terraform init -backend=false`, `terraform validate`
- [ ] All Bicep templates pass `bicep build`
- [ ] No hardcoded secrets

## Tech Details
- AVM Terraform: `source = "Azure/avm-res-{service}-{resource}/azurerm"`
- AVM Bicep: `br/public:avm/res/{service}/{resource}:{version}`
- Ref: PRD Section 7.1.3.1, TechSpec Section 7
""" },

  { "ref": "10",
    "title": "[EPIC 1][REF #10] Implement database schema and migrations",
    "labels": ["backend", "database"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 3-4) | **Assignee:** E4
**Depends on:** REF #1
**Blocks:** REF #15, REF #16, REF #17, REF #31

## Description
Implement the PostgreSQL database schema using SQLAlchemy async ORM with Alembic migrations.

## Acceptance Criteria
- [ ] SQLAlchemy async models for: `conversations`, `messages`, `deployments`, `generated_files`, `settings`, `audit_log`
- [ ] Alembic migration for initial schema creation
- [ ] `deployments` table includes all columns: stage, project_type, subscription_id, subscription_context (JSONB), template_name, template_params (JSONB), pr_number, pr_url, pr_branch, plan_output, plan_status, plan_error_category, plan_rework_iteration, apply_status, apply_output, iteration_count, violations (JSONB), diagram_mermaid, target_repo
- [ ] Indexes: `idx_messages_conversation`, `idx_files_deployment`
- [ ] `settings` table is singleton (fixed UUID PK)
- [ ] `audit_log` table for tracking H1/H2 approvals, PR creation, deployment actions
- [ ] Database adapter (`src/infrastructure/adapters/postgres_adapter.py`) with CRUD for all tables
- [ ] Docker-compose entry for local PostgreSQL (postgres:16)
- [ ] Integration test for schema creation and basic CRUD

## Tech Details
- Use `asyncpg` as async driver, SQLAlchemy 2.0 async with `AsyncSession`
- UUID primary keys via `gen_random_uuid()`, JSONB columns for flexible data
- Local dev: Docker PostgreSQL — no dependency on REF #6 (Azure infra)
- Ref: TechSpec Section 9
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 2: Infrastructure Adapters
  # ════════════════════════════════════════════════════════════
  { "ref": "11",
    "title": "[EPIC 2][REF #11] Implement Azure OpenAI / ModelRouter LLM adapter",
    "labels": ["backend", "ai-foundry", "adapter"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E1
**Depends on:** REF #4
**Blocks:** REF #15, REF #16, REF #17, REF #19, REF #20, REF #21

## Description
Implement the `ILLMCompletionPort` adapter for Azure OpenAI with ModelRouter support. Agents declare task profiles; ModelRouter routes to the optimal model.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/azure_openai_adapter.py` implementing `ILLMCompletionPort`
- [ ] `complete()` method with `TaskProfile` for ModelRouter routing
- [ ] `complete_with_tools()` method with MCP tool call execution loop
- [ ] ModelRouter profiles: complex-reasoning → GPT-4o, code-generation → GPT-4o, analysis → GPT-4o-mini, fast-lightweight → GPT-4o-mini, orchestration → GPT-4o
- [ ] Fallback model if primary is unavailable/rate-limited
- [ ] `model_used` populated in `LLMResponse`
- [ ] Token usage tracking; retry logic with exponential backoff
- [ ] SDK verification: confirm ModelRouter parameter names; fall back to direct model name if needed
- [ ] Integration test with mocked Azure endpoint

## Tech Details
- Use `azure-ai-projects` SDK with `AIProjectClient`, `DefaultAzureCredential`
- Ref: TechSpec Section 2.1, PRD Section 6.1.1
""" },

  { "ref": "12",
    "title": "[EPIC 2][REF #12] Implement GitHub adapter (ISourceControlPort)",
    "labels": ["backend", "adapter"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E4
**Depends on:** REF #4
**Blocks:** REF #17, REF #28, REF #29, REF #32

## Description
Implement the `ISourceControlPort` adapter for GitHub operations: branch management, file commits, PR creation, and workflow monitoring.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/github_adapter.py` implementing `ISourceControlPort`
- [ ] `create_branch(repo, branch, base)`
- [ ] `commit_files(repo, branch, files, message)` — Atomic tree commit via Git Data API
- [ ] `create_pr(repo, title, body, head, base)` — Returns `PRResult`
- [ ] `get_pipeline_status(repo, run_id)` — Returns `PipelineStatus`
- [ ] `trigger_workflow(repo, workflow, ref, inputs)` — Triggers workflow dispatch
- [ ] GitHub PAT loaded from Azure Key Vault (fallback to env var for local dev)
- [ ] Rate limit handling with exponential backoff
- [ ] Branch naming convention: `infraagent/{title-slug}`
- [ ] Integration test with mocked GitHub API

## Tech Details
- Use `httpx` for GitHub REST API v3 (async-native)
- Ref: TechSpec Section 2.1
""" },

  { "ref": "13",
    "title": "[EPIC 2][REF #13] Implement Terraform CLI adapter (IInfraProviderPort)",
    "labels": ["backend", "terraform", "adapter"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Depends on:** REF #4
**Blocks:** REF #15, REF #24, REF #32

## Description
Implement the `IInfraProviderPort` adapter for Terraform CLI operations.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/terraform_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — `terraform fmt -check`
- [ ] `validate(files)` — `terraform init -backend=false` + `terraform validate` (MUST use `-backend=false`)
- [ ] `lint(files)` — `tflint` (warnings only)
- [ ] `plan(files, variables)` — `terraform plan -no-color -out=tfplan -json`
- [ ] `apply(plan_id)` — `terraform apply`
- [ ] `get_language()` returns `"terraform"`
- [ ] Files written to temp dir, properly cleaned up after execution
- [ ] Stderr + exit code captured for error categorization
- [ ] Integration test against terraform CLI

## Tech Details
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Parse `terraform plan -json` output for structured resource counts
- Ref: TechSpec Section 4.2, PRD Section 7.1.4
""" },

  { "ref": "14",
    "title": "[EPIC 2][REF #14] Implement Bicep CLI adapter (IInfraProviderPort)",
    "labels": ["backend", "bicep", "adapter"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 3-5) | **Assignee:** E2
**Depends on:** REF #4
**Blocks:** REF #15, REF #24, REF #32

## Description
Implement the `IInfraProviderPort` adapter for Bicep CLI operations.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/bicep_adapter.py` implementing `IInfraProviderPort`
- [ ] `format_check(files)` — `bicep format --verify`
- [ ] `validate(files)` — `bicep build --stdout --no-restore`
- [ ] `lint(files)` — Bicep linter with triage: BCP081 ignored, BCP035 checked, BCP187 ignored
- [ ] `plan(files, variables)` — `az deployment group what-if`
- [ ] `apply(plan_id)` — `az deployment group create`
- [ ] `get_language()` returns `"bicep"`
- [ ] Integration test against bicep CLI

## Tech Details
- Use `asyncio.create_subprocess_exec` for async CLI calls
- Ref: PRD Section 7.1.4, TechSpec Section 4.2
""" },

  { "ref": "15",
    "title": "[EPIC 2][REF #15] Implement Template Registry adapter (ITemplateRegistryPort)",
    "labels": ["backend", "adapter", "knowledge-wiki"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1 (Day 4-5) | **Assignee:** E5
**Depends on:** REF #4, REF #8
**Blocks:** REF #16, REF #17, REF #30

## Description
Implement the `ITemplateRegistryPort` adapter that reads templates from the knowledge wiki submodule, supports keyword search, hydrates templates, and publishes new templates.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/template_registry_adapter.py` implementing `ITemplateRegistryPort`
- [ ] `search(query, filters)` — Keyword search against `metadata.yaml` fields; filters by complexity and iac_language
- [ ] `get_template(name, language)` — Returns full template content
- [ ] `hydrate(name, language, parameters, standards)` — Substitutes user parameters + applies org standards, returns `HydratedTemplate`
- [ ] `publish(template, metadata)` — Prepares new template for PR submission to wiki repo
- [ ] Templates loaded from `knowledge-wiki/templates/*/metadata.yaml` at runtime
- [ ] Caches template metadata at startup for fast search
- [ ] Unit tests with sample template fixtures

## Tech Details
- Reads from git submodule path at runtime
- Ref: TechSpec Section 2.1, PRD Section 8
""" },

  { "ref": "16",
    "title": "[EPIC 2][REF #16] Implement Policy adapter (IPolicyEnginePort)",
    "labels": ["backend", "adapter"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 4-5) | **Assignee:** E2
**Depends on:** REF #3, REF #4, REF #5
**Blocks:** REF #17, REF #23, REF #24

## Description
Implement the `IPolicyEnginePort` adapter bridging domain policy rules with the IaC parser and external security scanning tools (tfsec, Checkov).

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/policy_adapter.py` implementing `IPolicyEnginePort`
- [ ] `validate_naming(files)` — Parses IaC via `iac_parser`, runs `validate_resource_name()`, returns `PolicyResult`
- [ ] `validate_tags(files)` — Parses IaC, runs `validate_tags()`, returns `PolicyResult`
- [ ] `validate_security(files)` — Runs tfsec/Checkov CLI as subprocess, maps findings to `PolicyViolation`
- [ ] `check_avm_availability(resource_type)` — Returns boolean + module source if AVM module exists
- [ ] Severity mapping: CRITICAL/HIGH → "error"; MEDIUM/LOW → "warning"
- [ ] Unit tests with sample IaC containing known violations

## Tech Details
- tfsec: `tfsec --format=json --no-color <dir>`; Checkov: `checkov -d <dir> -o json`
- Ref: TechSpec Section 2.2
""" },

  { "ref": "17",
    "title": "[EPIC 2][REF #17] Implement Subscription Discovery adapter (ISubscriptionDiscoveryPort)",
    "labels": ["backend", "adapter", "azure"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E1
**Depends on:** REF #4, REF #22
**Blocks:** REF #19, REF #36

## Description
Implement the `ISubscriptionDiscoveryPort` adapter connecting to Azure via Azure MCP Server to inventory existing resources, VNets, naming patterns, and quotas.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/subscription_discovery_adapter.py` implementing `ISubscriptionDiscoveryPort`
- [ ] `discover(subscription_id)` returns `SubscriptionContext` with: subscription_id/name, resource_groups, resources (list of `DiscoveredResource`), vnets (list of `DiscoveredVNet`), naming_patterns, quotas, state_backends, available_regions
- [ ] `check_sku_availability(subscription_id, resource_type, sku, region)`
- [ ] `check_quota(subscription_id, resource_type, region)`
- [ ] Naming pattern detection: regex inference from existing resource names
- [ ] All discovery data is point-in-time with timestamps
- [ ] Integration test with mocked Azure MCP responses

## Tech Details
- Azure MCP tools: listResourceGroups, listResources, getVNetTopology, checkQuotas
- Ref: TechSpec Section 2.1, PRD Section 7.1.1
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 3: Application Layer — Use Cases
  # ════════════════════════════════════════════════════════════
  { "ref": "18",
    "title": "[EPIC 3][REF #18] Implement ConsultUseCase",
    "labels": ["backend", "use-case", "consulting-agent"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 1-2 (Day 4-7) | **Assignee:** E1
**Depends on:** REF #2, REF #4, REF #11
**Blocks:** REF #19, REF #36

## Description
Implement the ConsultUseCase driving the Consulting Agent's multi-turn requirements gathering conversation, including project type classification, knowledge wiki search, and template recommendations.

## Acceptance Criteria
- [ ] `src/application/use_cases/consult.py` with `ConsultUseCase` class
- [ ] Constructor injection: `ILLMCompletionPort`, `ITemplateRegistryPort`, `ISubscriptionDiscoveryPort` (optional), `IObservabilityPort`
- [ ] `run()` method: one conversation turn — builds system prompt, searches wiki for templates, calls LLM
- [ ] Project type extraction via `[PROJECT_TYPE:X]` markers in LLM response
- [ ] Template recommendation via `[RECOMMEND_TEMPLATE:name]` markers
- [ ] Requirements completion via `[REQUIREMENTS_COMPLETE]` marker
- [ ] Subscription discovery when `subscription_id` is provided
- [ ] `ConsultResult` with: response, recommended_template, recommended_path, requirements_complete, project_type, subscription_context
- [ ] Unit tests with mocked ports

## Tech Details
- ModelRouter task profile: `complex-reasoning`
- Ref: TechSpec Section 4.1
""" },

  { "ref": "19",
    "title": "[EPIC 3][REF #19] Implement GenerateUseCase (custom + catalog paths)",
    "labels": ["backend", "use-case", "codegen-agent"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 5-9) | **Assignee:** E2
**Depends on:** REF #2, REF #4, REF #11, REF #13, REF #14
**Blocks:** REF #24, REF #25, REF #36

## Description
Implement the GenerateUseCase with both the custom generation pipeline and the catalog fast-path. Includes maker-checker loop (max 3 iterations) and diagram generation.

## Acceptance Criteria
- [ ] `src/application/use_cases/generate.py` with `GenerateUseCase` class
- [ ] `run_custom_path()` — Full pipeline: CodeGen (AVM-first) → IaC Validation → Standards → Security → Diagram; loops on violations, max 3 iterations total
- [ ] `run_catalog_path()` — Template hydration + syntax validation only
- [ ] `_run_iac_validation_pipeline()` — Deterministic: format_check → validate → lint; runs BEFORE standards/security
- [ ] `_generate_code()` — Calls LLM with MCP tools, AVM-first strategy enforced in prompt
- [ ] `_generate_diagram()` — Lightweight LLM call (profile: `fast-lightweight`) for Mermaid diagram
- [ ] `FILE_STRUCTURE_TERRAFORM`, `FILE_STRUCTURE_BICEP`, `SECRET_HANDLING_RULES` constants
- [ ] `MAX_MAKER_CHECKER_ITERATIONS = 3`
- [ ] `GenerateResult` with: files, standards_passed, security_passed, violations, iteration_count, diagram_mermaid, assistant_message
- [ ] Unit tests with mocked ports for both paths

## Tech Details
- Violation feedback format: `{ checker, severity, resource, file, line, message, remediation }`
- CodeGen receives last 5 violations for rework context
- Ref: TechSpec Section 4.2, PRD Sections 7.1.3, 7.1.4, 6.2.1
""" },

  { "ref": "20",
    "title": "[EPIC 3][REF #20] Implement DeployUseCase",
    "labels": ["backend", "use-case", "deploy-agent"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 5-7) | **Assignee:** E4
**Depends on:** REF #2, REF #4, REF #12
**Blocks:** REF #28, REF #29, REF #36

## Description
Implement the DeployUseCase handling PR creation, plan monitoring, plan failure categorization, and deployment triggering via GitHub Actions.

## Acceptance Criteria
- [ ] `src/application/use_cases/deploy.py` with `DeployUseCase` class
- [ ] `create_pr(repo, files, title, body, base_branch)` — Creates branch, commits files atomically, opens PR
- [ ] `get_plan_status(repo, run_id)` — Polls GitHub Actions for plan/apply status
- [ ] `trigger_apply(repo, workflow, ref, inputs)` — Triggers apply workflow
- [ ] `categorize_plan_failure(stderr, exit_code)` — Categories: resource_conflict, sku_unavailable, quota_exceeded, auth_failure, provider_mismatch, module_error, unknown
- [ ] `PlanFailureAnalysis` dataclass: category, error_message, stderr, exit_code, is_fixable_in_code, suggested_fix
- [ ] `MAX_PLAN_REWORK_ITERATIONS = 2`
- [ ] Observability metrics: `prs_created`, `deployments_triggered`
- [ ] Unit tests with mocked ports + plan failure categorization tests

## Tech Details
- Branch naming: `infraagent/{title-lowercase-slugified[:50]}`
- Ref: TechSpec Section 4.3, PRD Section 7.1.8
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 4: Agent Definitions & Orchestration
  # ════════════════════════════════════════════════════════════
  { "ref": "21",
    "title": "[EPIC 4][REF #21] Write agent system prompts (all 8 agents)",
    "labels": ["agents", "prompts"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 1-2 (Day 3-8) | **Assignee:** E2 + E1
**Depends on:** REF #8, REF #13, REF #14
**Blocks:** REF #22

## Description
Write comprehensive system prompts for all 8 agents — the `instructions` field in the Foundry agent definitions.

## Assignment Split
- **E2:** `codegen_agent_terraform.md`, `codegen_agent_bicep.md`, `standards_agent.md`, `security_agent.md`
- **E1:** `orchestrator.md`, `consulting_agent.md`, `pr_workflow_agent.md`, `deploy_agent.md`, `template_curation_agent.md`

## Acceptance Criteria
- [ ] `src/prompts/orchestrator.md` — Routing, lifecycle management, pipeline enforcement
- [ ] `src/prompts/consulting_agent.md` — Multi-turn requirements gathering, `[PROJECT_TYPE:X]`, `[RECOMMEND_TEMPLATE:name]`, `[REQUIREMENTS_COMPLETE]` markers
- [ ] `src/prompts/codegen_agent_terraform.md` — Terraform HCL with AVM-first rules, MCP tool usage, secret handling, violation rework
- [ ] `src/prompts/codegen_agent_bicep.md` — Bicep with AVM-first rules, `@secure()` decorator, file structure conventions
- [ ] `src/prompts/standards_agent.md` — Naming, tagging, structural validation, AVM compliance check
- [ ] `src/prompts/security_agent.md` — tfsec/Checkov invocation, severity classification, remediation guidance
- [ ] `src/prompts/pr_workflow_agent.md` — Branch creation, PR description formatting, diagram commit
- [ ] `src/prompts/deploy_agent.md` — Plan execution, error categorization, rework routing, apply monitoring
- [ ] `src/prompts/template_curation_agent.md` — Post-deploy analysis, novelty check, generalization
- [ ] Each prompt is 200-500 lines with clear behavioral rules and JSON output format specifications

## Tech Details
- Ref: TechSpec Appendix A
""" },

  { "ref": "22",
    "title": "[EPIC 4][REF #22] Configure MCP server connections",
    "labels": ["backend", "mcp", "integration"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1-2 (Day 4-6) | **Assignee:** E1
**Depends on:** REF #6
**Blocks:** REF #17, REF #23

## Description
Configure connections to the 4 MCP servers (Terraform, Bicep, Azure, GitHub) used for grounding agent code generation and operations.

## Acceptance Criteria
- [ ] `src/infrastructure/mcp/config.py` with `MCPServerConfig` dataclass and `MCP_SERVERS` dict
- [ ] Terraform MCP (hashicorp/terraform-mcp-server) — tools: search_providers, get_provider_details, search_modules, get_module_details, resourceUsage
- [ ] Bicep MCP — tools: get_az_resource_type_schema, get_bicep_best_practices, list_avm_metadata, format_bicep_file, diagnostics
- [ ] Azure MCP (microsoft/mcp) — tools: resource management, subscription info, quota checks, VNet topology
- [ ] GitHub MCP (github/github-mcp-server) — tools: create_branch, commit_files, create_pull_request, workflow operations
- [ ] `src/infrastructure/mcp/tool_adapter.py` — MCP tool → Foundry tool conversion utility
- [ ] Auth per server via Key Vault or env vars
- [ ] Connection health check with graceful degradation when MCP unavailable
- [ ] `.vscode/mcp.json` configured for local development
- [ ] **Graceful degradation:** When MCP down, agents fall back to plain LLM generation with warning flag

## Tech Details
- Foundry-hosted agents require remote HTTP (not localhost/stdio) — 100-second timeout
- Ref: TechSpec Section 6, PRD Section 9
""" },

  { "ref": "23",
    "title": "[EPIC 4][REF #23] Register agents with Azure AI Foundry Agent Service",
    "labels": ["backend", "ai-foundry", "agents"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E1
**Depends on:** REF #6, REF #11, REF #21, REF #22
**Blocks:** REF #25, REF #26

## Description
Implement the agent registry that registers all 8 agents with Azure AI Foundry as Hosted Agents with ModelRouter task profiles and MCP tool bindings.

## Acceptance Criteria
- [ ] `src/infrastructure/agents/registry.py` with `AGENT_CONFIGS` dict defining all 8 agents
- [ ] Each agent config: `task_profile`, `instructions_file` path, `tools` list
- [ ] `register_agents()` async function creates/updates all agents in Foundry
- [ ] ModelRouter profiles: orchestrator→orchestration, consulting→complex-reasoning, codegen→code-generation, standards→analysis, security→fast-lightweight, pr_workflow→fast-lightweight, deploy→complex-reasoning, template_curation→code-generation
- [ ] MCP tool bindings per agent
- [ ] `_build_mcp_tools(agent_name)` auto-wires MCP servers with graceful degradation (warning logged if unavailable)
- [ ] Uses `DefaultAzureCredential` and Foundry `AIProjectClient`
- [ ] **Fallback:** If Foundry Agent Service has limitations, document path to using custom orchestration

## Tech Details
- `MCPTool(server_label=..., server_url=..., require_approval="never")`
- Security agent uses `FunctionTool` for tfsec/Checkov
- Ref: TechSpec Section 5.1
""" },

  { "ref": "24",
    "title": "[EPIC 4][REF #24] Implement IaC Validation Pipeline (deterministic, non-LLM)",
    "labels": ["backend", "validation", "pipeline"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 6-8) | **Assignee:** E2
**Depends on:** REF #13, REF #14, REF #19
**Blocks:** REF #36

## Description
Implement the deterministic IaC validation pipeline as a function tool chain. NOT an agent — runs CLI tools without any LLM involvement.

## Acceptance Criteria
- [ ] Terraform chain: `fmt -check` (auto-fix, non-blocking) → `init -backend=false` (blocking) → `validate` (blocking) → `tflint` (stretch, warnings only)
- [ ] Bicep chain: `build --stdout --no-restore` (blocking) → `format` (non-blocking) → lint with triage (BCP081 ignored, BCP035 checked, BCP187 ignored)
- [ ] Format failures auto-fixed without CodeGen rework
- [ ] Init/validate/build failures produce structured error output fed back to CodeGen
- [ ] Lint warnings attached to H1 review as informational (not blocking)
- [ ] Returns `{"passed": bool, "errors": list[str], "warnings": list[str]}`
- [ ] Integrated into `GenerateUseCase._run_iac_validation_pipeline()` (runs BEFORE standards/security)
- [ ] Shared retry counter: validation + standards + security = max 3 iterations total
- [ ] Unit tests for each chain step

## Tech Details
- Uses `IInfraProviderPort.format_check()`, `.validate()`, `.lint()`
- Ref: PRD Section 7.1.4, TechSpec Section 4.2
""" },

  { "ref": "25",
    "title": "[EPIC 4][REF #25] Implement orchestrator workflow (chat path)",
    "labels": ["backend", "orchestrator", "agents"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 7-10) | **Assignee:** E1
**Depends on:** REF #18, REF #19, REF #20, REF #23
**Blocks:** REF #36, REF #39

## Description
Implement the graph-based orchestrator for the chat path: Consult → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy.

## Acceptance Criteria
- [ ] `src/infrastructure/agents/orchestrator.py` with `build_chat_path_workflow()` function
- [ ] `AgentWorkflow` with all nodes: consult, subscription_discovery, codegen, iac_validation (deterministic), standards, security, diagram_gen, h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] `HumanApprovalNode` for H1 and H2
- [ ] **Maker-checker loop (Loop 1):** security → codegen if violations_fixable AND iteration < 3; → diagram if passed
- [ ] **IaC validation loop:** iac_valid → standards if passed; → codegen if failed
- [ ] **Plan-failure rework (Loop 2):** plan → h2_gate if success; → codegen if failed_fixable (max 2×); → h2_gate with error if failed_escalate
- [ ] Checkpointing enabled for durable long-running workflows
- [ ] Context sharing between agents
- [ ] Real-time stage updates emitted as events for SSE

## Tech Details
- `iac_validation` node has `agent_name=None` (deterministic, not LLM)
- Ref: TechSpec Section 5.2
""" },

  { "ref": "26",
    "title": "[EPIC 4][REF #26] Implement orchestrator workflow (catalog path)",
    "labels": ["backend", "orchestrator", "agents"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-9) | **Assignee:** E1
**Depends on:** REF #19, REF #20, REF #23
**Blocks:** REF #38, REF #39

## Description
Implement the graph-based orchestrator for the catalog path: Template hydrate → IaC Validation → H1 → PR → Plan → H2 → Deploy. No consulting, no iterative loops.

## Acceptance Criteria
- [ ] `build_catalog_path_workflow()` function in orchestrator.py
- [ ] Nodes: hydrate (codegen in hydrate mode), iac_validation (syntax check only), h1_code_review, pr_workflow, plan, h2_plan_review, deploy
- [ ] No maker-checker loop (templates are pre-validated)
- [ ] H1 and H2 human gates functional
- [ ] Context: template parameters + org standards passed through pipeline

## Tech Details
- Validation is syntax-only (no lint/tflint for catalog path)
- Ref: TechSpec Section 5.2
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 5: Agent Implementation
  # ════════════════════════════════════════════════════════════
  { "ref": "27",
    "title": "[EPIC 5][REF #27] Implement Standards Agent logic",
    "labels": ["backend", "agents", "standards"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E2
**Depends on:** REF #3, REF #5, REF #16, REF #19
**Blocks:** REF #36

## Description
Implement the Standards Agent's validation logic combining domain policy rules with LLM-based structural analysis.

## Acceptance Criteria
- [ ] Naming validation via domain `validate_resource_name()` using IaC parser for resource extraction
- [ ] Tagging validation via domain `validate_tags()` against required tags
- [ ] **AVM compliance check:** Flags raw `azurerm_` resources when equivalent AVM module exists; uses `check_avm_availability()`
- [ ] **Dependency correctness:** Detects redundant `depends_on` where dependency is implicit
- [ ] **File structure validation:** Verifies generated code follows PRD Section 7.1.3.2 conventions
- [ ] Structured violation reports: `{ checker: "standards", severity, resource, file, line, message, remediation }`
- [ ] Only `severity: "error"` findings trigger rework loop
- [ ] Policy RAG via Azure AI Search (stretch — falls back to direct file read)
- [ ] Unit tests with sample IaC containing naming violations, missing tags, raw resources

## Tech Details
- AVM check: if resource_type matches `azurerm_*` and AVM exists → flag with recommendation
- Ref: PRD Section 7.1.5
""" },

  { "ref": "28",
    "title": "[EPIC 5][REF #28] Implement Security Agent logic",
    "labels": ["backend", "agents", "security"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-10) | **Assignee:** E2
**Depends on:** REF #16, REF #19
**Blocks:** REF #36

## Description
Implement the Security Agent that runs tfsec and Checkov static analysis on generated IaC code and produces structured finding reports.

## Acceptance Criteria
- [ ] tfsec integration for Terraform — runs via policy adapter, parses structured findings
- [ ] Checkov integration for Terraform — runs via policy adapter, parses structured findings
- [ ] Bicep security validation via `bicep build` diagnostics
- [ ] Structured finding reports: `{ checker: "security", severity, resource, file, line, message, remediation }`
- [ ] Critical/high findings trigger rework loop; medium/low are informational (passed to H1)
- [ ] Findings fed back to CodeGen as part of Loop 1
- [ ] Uses `IPolicyEnginePort.validate_security()`
- [ ] Unit tests with known-vulnerable IaC samples (public blob access, missing encryption, open NSG rules)

## Tech Details
- Severity mapping: CRITICAL/HIGH → "error" (triggers retry); MEDIUM/LOW → "warning"
- Ref: PRD Section 7.1.6
""" },

  { "ref": "29",
    "title": "[EPIC 5][REF #29] Implement PR Workflow Agent logic",
    "labels": ["backend", "agents"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E4
**Depends on:** REF #12, REF #20
**Blocks:** REF #36

## Description
Implement the PR Workflow Agent that creates branches, commits generated IaC files, and opens PRs with structured descriptions.

## Acceptance Criteria
- [ ] Creates feature branch: `infraagent/{title-slug}`
- [ ] Commits all generated IaC files atomically (single tree commit via Git Data API)
- [ ] Commits auto-generated Mermaid diagram file to `/docs/architecture/` in the target repo
- [ ] Opens PR with structured body: resources created, standards applied, security scan results, diagram preview link
- [ ] Returns `PRResult` with number, url, html_url, state, branch_name
- [ ] Monitors CI/CD pipeline status via GitHub MCP Server / GitHub API

## Tech Details
- PR body template: resources list, standards status, security status, diagram preview
- Ref: PRD Section 7.1.7
""" },

  { "ref": "30",
    "title": "[EPIC 5][REF #30] Author CI/CD workflow templates for generated IaC repos",
    "labels": ["backend", "ci-cd"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E4
**Depends on:** REF #12
**Blocks:** REF #29, REF #32

## Description
Create GitHub Actions workflow template files that the PR Workflow Agent commits to the target repo if they don't exist.

## Acceptance Criteria
- [ ] `terraform-plan.yml` — Triggered on PR to `terraform/**`: checkout, setup-terraform, `terraform init`, `terraform validate`, `terraform plan -no-color -out=tfplan`, post plan output as PR comment
- [ ] `terraform-apply.yml` — Triggered on workflow_dispatch: `terraform apply`, report status
- [ ] `bicep-whatif.yml` — Triggered on PR to `infra/**`: checkout, `az deployment group what-if`, post output as PR comment
- [ ] `bicep-deploy.yml` — Triggered on workflow_dispatch: `az deployment group create`, report status
- [ ] All workflows use: `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`
- [ ] Plan output posted as PR comment via `actions/github-script@v7`
- [ ] Templates stored in `src/infrastructure/templates/workflows/`

## Tech Details
- Ref: TechSpec Section 13.2
""" },

  { "ref": "31",
    "title": "[EPIC 5][REF #31] Implement Deploy Agent logic (plan/apply + rework loop)",
    "labels": ["backend", "agents", "deploy"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 8-10) | **Assignee:** E4
**Depends on:** REF #12, REF #20
**Blocks:** REF #36, REF #39

## Description
Implement the Deploy Agent that triggers terraform plan/apply via GitHub Actions, monitors progress, and integrates with the plan-failure rework loop (Loop 2).

## Acceptance Criteria
- [ ] Triggers `terraform plan` / `bicep what-if` via GitHub Actions workflow dispatch
- [ ] Polls GitHub Actions for pipeline completion with timeout
- [ ] Surfaces plan output to user for H2 review
- [ ] **Plan failure handling:** Extracts full error output, calls `categorize_plan_failure()`:
  - `resource_conflict` → fixable in code
  - `sku_unavailable` → fixable in code (query Azure MCP for alternatives)
  - `quota_exceeded` → escalate to user
  - `auth_failure` → escalate to user
  - `provider_mismatch` → fixable in code
  - `module_error` → fixable in code
- [ ] On fixable failure: routes back to CodeGen via orchestrator (Loop 2, max 2 iterations)
- [ ] On non-fixable failure: escalates to user at H2 gate with plan output + analysis
- [ ] On apply success: reports deployment status
- [ ] On apply failure: captures partial state info, provides rollback guidance

## Tech Details
- Plan rework: full plan error → categorize → CodeGen → re-enter validation pipeline → new PR → re-plan
- Loop 2 max iterations = 2
- Ref: PRD Section 7.1.8, TechSpec Section 4.2
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 6: Backend API Layer
  # ════════════════════════════════════════════════════════════
  { "ref": "32",
    "title": "[EPIC 6][REF #32] Implement chat API endpoints + WebSocket streaming",
    "labels": ["backend", "api", "chat"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-10) | **Assignee:** E1
**Depends on:** REF #10, REF #18, REF #25
**Blocks:** REF #36

## Description
Implement the FastAPI routes and WebSocket endpoint for the chat interface.

## Acceptance Criteria
- [ ] `src/api/routes/chat.py`:
  - `POST /api/chat` — SSE stream; events: `assistant_message`, `stage_change`, `subscription_context`, `files_generated`, `approval_required`
  - `POST /api/chat/{conversation_id}/approve` — Human gate approval (H1 or H2) with optional comment
  - `POST /api/chat/{conversation_id}/reject` — Human gate rejection with feedback
  - `WS /ws/chat/{conversation_id}` — WebSocket for real-time streaming
- [ ] `POST /api/pipeline/start`, `GET /api/pipeline/status/{session_id}`
- [ ] `POST /api/pipeline/approve/h1` and `POST /api/pipeline/approve/h2`
- [ ] `src/api/schemas/chat.py` — Pydantic models for request/response/SSE events
- [ ] SSE event types: assistant_message, stage_change, subscription_context, files_generated, approval_required, deployment_status, plan_failure, deployment_complete
- [ ] Conversation and message persistence to database

## Tech Details
- Use FastAPI `StreamingResponse` with `text/event-stream` for SSE
- Ref: TechSpec Section 8.1, 8.2
""" },

  { "ref": "33",
    "title": "[EPIC 6][REF #33] Implement catalog API endpoints",
    "labels": ["backend", "api", "catalog"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-9) | **Assignee:** E4
**Depends on:** REF #8, REF #9, REF #10, REF #15
**Blocks:** REF #38

## Description
Implement the FastAPI routes for the self-service catalog: listing templates, template details, and deploying templates.

## Acceptance Criteria
- [ ] `src/api/routes/catalog.py`:
  - `GET /api/catalog` — List templates with keyword search + filters (complexity, iac_language)
  - `GET /api/catalog/{name}` — Template details + full parameter schema
  - `POST /api/catalog/{name}/deploy` — Deploy catalog template; returns deployment_id + session_id
- [ ] `src/api/schemas/catalog.py` — Pydantic request/response models
- [ ] Template search reads from `ITemplateRegistryPort.search()`
- [ ] Deploy endpoint triggers the catalog path workflow (REF #26)
- [ ] Returns 404 for unknown templates, 400 for missing/invalid parameters

## Tech Details
- Ref: TechSpec Section 8.1, 8.2, api-reference.md
""" },

  { "ref": "34",
    "title": "[EPIC 6][REF #34] Implement deployment + health + standards API endpoints",
    "labels": ["backend", "api"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-10) | **Assignee:** E4
**Depends on:** REF #10, REF #12
**Blocks:** REF #39

## Description
Implement FastAPI routes for deployment tracking, health checks, and standards viewing.

## Acceptance Criteria
- [ ] `src/api/routes/deployments.py`:
  - `GET /api/deployments/{id}` — Full deployment status (stage, PR info, plan status, file count, diagram URL, rework_iteration)
  - `GET /api/deployments/{id}/plan` — Plan output text
  - `GET /api/deployments/{id}/files` — Generated files with content
  - `GET /api/deployments/{id}/diagram` — Architecture diagram (Mermaid source + SVG URL)
- [ ] `src/api/routes/health.py` — `GET /api/health` (no auth): backend, DB, Foundry, MCP reachability
- [ ] `src/api/routes/standards.py` — `GET /api/standards` loads org standards from knowledge wiki
- [ ] `src/api/middleware/cors.py` — CORS via `CORS_ORIGINS` env var
- [ ] `src/api/middleware/auth.py` — JWT/Entra ID auth stub (passes all requests, TODO comment)
- [ ] Pydantic response models in `src/api/schemas/deployment.py`

## Tech Details
- Ref: TechSpec Section 8.1, 8.2, api-reference.md
""" },

  { "ref": "35",
    "title": "[EPIC 6][REF #35] Implement composition root and dependency injection",
    "labels": ["backend", "architecture"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E1
**Depends on:** REF #11, REF #12, REF #13, REF #14, REF #15, REF #16, REF #17, REF #18, REF #19, REF #20
**Blocks:** REF #32, REF #36

## Description
Implement the composition root (`src/main.py`) that wires all adapters, use cases, and routes together via constructor injection.

## Acceptance Criteria
- [ ] `src/main.py` with `create_app()` function
- [ ] All adapters instantiated: AzureOpenAIAdapter, TerraformAdapter, BicepAdapter, GitHubAdapter, PolicyAdapter, TemplateRegistryAdapter, SubscriptionDiscoveryAdapter, OpenTelemetryAdapter, PostgresAdapter
- [ ] `infra_providers` dict: `{"terraform": terraform_adapter, "bicep": bicep_adapter}`
- [ ] Use cases instantiated with port injection
- [ ] FastAPI app created with all routes registered
- [ ] Configuration loaded from `src/config.py` (env vars, Key Vault references)
- [ ] **Architectural invariant:** No domain or application layer module imports infrastructure directly
- [ ] Startup validation: checks required env vars, tests DB connection, logs MCP server availability

## Tech Details
- Ref: TechSpec Section 2.2
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 7: Frontend
  # ════════════════════════════════════════════════════════════
  { "ref": "36",
    "title": "[EPIC 7][REF #36] Scaffold frontend with Next.js + Tailwind + shadcn/ui",
    "labels": ["frontend", "foundation"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 1 (Day 1-2) | **Assignee:** E3
**Depends on:** REF #1
**Blocks:** REF #37, REF #38, REF #39, REF #40

## Description
Initialize the React/Next.js frontend with TypeScript, Tailwind CSS, and shadcn/ui. Set up routing, global state management, API client, and WebSocket client.

## Acceptance Criteria
- [ ] `frontend/` directory with Next.js 15+ app router
- [ ] TypeScript + Tailwind CSS + shadcn/ui configured
- [ ] Routes: `/`, `/chat`, `/chat/:conversationId`, `/catalog`, `/catalog/:templateName`, `/deployments/:id`, `/settings`
- [ ] `frontend/src/lib/api.ts` — Backend API client (fetch-based, configurable `NEXT_PUBLIC_API_URL`)
- [ ] `frontend/src/lib/ws.ts` — WebSocket client with reconnection and exponential backoff
- [ ] `frontend/src/lib/types.ts` — Shared TypeScript interfaces matching backend schemas
- [ ] Global state via Zustand: `AppState` with conversations, activeConversationId, activeDeployment, templates, catalogSearchQuery, settings, connectionStatus
- [ ] Landing page with two entry points: "Chat with InfraAgent" and "Self-Service Catalog"
- [ ] Dark/light theme support via Tailwind

## Tech Details
- Next.js app router (`app/` directory)
- Ref: TechSpec Section 10
""" },

  { "ref": "37",
    "title": "[EPIC 7][REF #37] Build Chat UI (ChatPanel + streaming + human gates)",
    "labels": ["frontend", "chat-ui"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 2 (Day 6-10) | **Assignee:** E3
**Depends on:** REF #32, REF #36
**Blocks:** REF #39, REF #41

## Description
Build the complete chat interface including message history, streaming responses, stage transitions, subscription discovery display, code generation display, and human gate approval modals.

## Acceptance Criteria
- [ ] `ChatPanel.tsx` — Full chat with message history, markdown rendering, syntax-highlighted code blocks
- [ ] `MessageBubble.tsx` — User and assistant bubbles with agent name labels
- [ ] `StreamingIndicator.tsx` — Animated indicator during LLM streaming
- [ ] `SubscriptionDiscoveryPanel.tsx` — Displays discovered subscription context inline
- [ ] **Stage transition visualization:** Progress bar showing all pipeline stages; current highlighted, completed checked, failed red
- [ ] **SSE event handling:** assistant_message, stage_change, subscription_context, files_generated, approval_required, plan_failure
- [ ] `ApprovalModal.tsx` — H1 (code + diagram review) and H2 (plan review) human gate UI
- [ ] `FileExplorer.tsx` — Tree view of generated `.tf`/`.bicep` files with syntax highlighting
- [ ] `DiagramViewer.tsx` — Renders Mermaid diagram as SVG with zoom/pan/export
- [ ] `useChat.ts` hook — Manages conversation state, SSE/WebSocket connection
- [ ] IaC language selector (Terraform / Bicep) in chat header
- [ ] Chat input: Enter to send, Shift+Enter for new line

## Tech Details
- SSE via `EventSource` or `fetch` with `ReadableStream`
- Mermaid rendering via `mermaid` npm package
- Ref: TechSpec Section 10.2, 10.3
""" },

  { "ref": "38",
    "title": "[EPIC 7][REF #38] Build Self-Service Catalog UI",
    "labels": ["frontend", "catalog-ui"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 7-10) | **Assignee:** E3
**Depends on:** REF #33, REF #36
**Blocks:** REF #41

## Description
Build the self-service catalog interface: searchable template grid, template detail view with parameter form, and one-click deploy.

## Acceptance Criteria
- [ ] `CatalogGrid.tsx` — Searchable grid of template cards: name, description, complexity badge (simple=green, moderate=yellow, complex=red), Azure service icons, IaC language tags
- [ ] `TemplateCard.tsx` — Card component with hover preview
- [ ] `TemplateDetail.tsx` — Full template detail: description, Azure services, complexity, version, author, approved_by
- [ ] `ParameterForm.tsx` — Dynamic form from `metadata.yaml`: integer (slider), string (dropdown for allowed_values), boolean (toggle); org-level params shown as read-only
- [ ] Deploy button: submits parameters + iac_language + target_repo → `POST /api/catalog/{name}/deploy`
- [ ] After deploy: redirects to `/deployments/{id}`
- [ ] `useCatalog.ts` hook
- [ ] Empty state for no search results
- [ ] Client-side parameter validation matching `metadata.yaml` rules

## Tech Details
- Ref: TechSpec Section 10.3
""" },

  { "ref": "39",
    "title": "[EPIC 7][REF #39] Build Deployment Tracker UI",
    "labels": ["frontend", "deployment-ui"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2 (Day 9-11) | **Assignee:** E3
**Depends on:** REF #34, REF #36
**Blocks:** REF #41

## Description
Build the deployment tracking page showing pipeline stage progress, PR link, plan output, and deployment result.

## Acceptance Criteria
- [ ] `DeploymentTracker.tsx` — Full deployment detail page at `/deployments/:id`
- [ ] `PipelineStages.tsx` — Visual horizontal stepper for all stages; current highlighted, completed checked, failed red
- [ ] PR section: link to GitHub PR, branch name, PR status
- [ ] Plan section: plan output with syntax highlighting, resource counts (create/modify/destroy)
- [ ] **Destructive change warning:** Prominent red banner if `resources_to_destroy > 0`
- [ ] Plan-failure rework indicator: Loop 2 iteration count, error category, CodeGen rework status
- [ ] Deploy section: deployment progress, success/failure status
- [ ] File explorer (reused from chat) for viewing generated code
- [ ] Diagram viewer (reused from chat) for architecture diagram
- [ ] Real-time updates via polling `GET /api/deployments/{id}` every 3-5 seconds
- [ ] `useDeployment.ts` hook

## Tech Details
- Plan output color coding: green for +create, yellow for ~modify, red for -destroy
- Ref: TechSpec Section 10.3
""" },

  { "ref": "40",
    "title": "[EPIC 7][REF #40] Build Settings page",
    "labels": ["frontend", "settings"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 9-10) | **Assignee:** E3
**Depends on:** REF #36

## Description
Build the settings page for configuring Azure subscription, GitHub repo, and connection details.

## Acceptance Criteria
- [ ] `/settings` page: Azure subscription ID, Azure tenant ID, GitHub repo (owner/name), default branch, IaC language preference
- [ ] GitHub PAT field (masked input, stored encrypted server-side)
- [ ] Connection test buttons: verify Azure subscription access, GitHub repo access, Foundry connectivity
- [ ] Connection status indicators on main layout header (green/red dots for Azure, GitHub, Foundry)
- [ ] Settings persisted via `POST /api/settings` → database `settings` table
- [ ] Settings loaded on app startup via `GET /api/settings`

## Tech Details
- Secrets (GitHub PAT) sent to backend for storage in Key Vault, never stored in browser
- Ref: TechSpec Section 10.1
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 8: Mermaid Diagram Rendering Pipeline
  # ════════════════════════════════════════════════════════════
  { "ref": "41",
    "title": "[EPIC 8][REF #41] Implement server-side Mermaid-to-SVG rendering",
    "labels": ["backend", "diagram", "frontend"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E3
**Depends on:** REF #19

## Description
Implement server-side Mermaid-to-SVG conversion so the PR Workflow Agent can commit a static SVG to `/docs/architecture/` in the target repo.

## Acceptance Criteria
- [ ] Install `@mermaid-js/mermaid-cli` (`mmdc`) as a backend dependency (or Node.js subprocess)
- [ ] `src/infrastructure/adapters/diagram_renderer.py` — `render_mermaid_to_svg(mermaid_code: str) -> str`
- [ ] Called by PR Workflow Agent before committing files — SVG added to the file list alongside IaC files
- [ ] SVG committed to `/docs/architecture/{deployment-id}.svg` in the PR
- [ ] Fallback: if `mmdc` unavailable, commit `.mermaid` file directly and log warning
- [ ] Unit test with sample Mermaid input

## Tech Details
- `mmdc -i input.mmd -o output.svg -t dark`
- May need Puppeteer/headless Chrome for server-side rendering
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 9: AI Search & Policy RAG
  # ════════════════════════════════════════════════════════════
  { "ref": "42",
    "title": "[EPIC 9][REF #42] Set up AI Search indexes for Policy RAG and template search",
    "labels": ["backend", "ai-search", "infrastructure"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 7-8) | **Assignee:** E5
**Depends on:** REF #6, REF #8, REF #9
**Blocks:** REF #27

## Description
Configure Azure AI Search indexes for the Standards Agent (Policy RAG) and the Self-Service Catalog (template search).

## Acceptance Criteria
- [ ] AI Search index `standards-policies` — Indexes `knowledge-wiki/standards/*.md`; fields: title, content, section, category
- [ ] AI Search index `templates` — Indexes `knowledge-wiki/templates/*/metadata.yaml`; fields: name, display_name, description, azure_services, complexity, iac_languages, tags, parameters (JSON), version
- [ ] `src/infrastructure/adapters/ai_search_adapter.py` — Adapter for querying AI Search indexes
- [ ] Indexer script or startup routine populates/refreshes indexes from the knowledge wiki
- [ ] CI step in wiki repo triggers index refresh when standards or templates are updated
- [ ] Falls back gracefully to direct file-read search if AI Search is unavailable

## Tech Details
- Use `azure-search-documents` SDK
- Supports keyword search (BM25) for templates and semantic search for policy RAG
- Ref: TechSpec Section 11
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 10: Integration & End-to-End
  # ════════════════════════════════════════════════════════════
  { "ref": "43",
    "title": "[EPIC 10][REF #43] End-to-end integration: Chat path (Demo 1)",
    "labels": ["integration", "e2e", "demo"],
    "body": """\
**Priority:** P0 | **Size:** XL | **Week:** 2-3 (Day 10-13) | **Assignee:** E1 + E3
**Depends on:** REF #24, REF #25, REF #27, REF #28, REF #29, REF #31, REF #32, REF #37
**Blocks:** REF #46

## Description
Wire everything together for the chat path end-to-end: message → Consulting Agent → subscription discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → plan → H2 → deploy.

## Acceptance Criteria
- [ ] User types "I need a 3-tier web app with App Service, SQL Database, and a VNet"
- [ ] Consulting Agent asks 2-3 clarifying questions and classifies project type
- [ ] Subscription discovery surfaces existing resources conversationally
- [ ] CodeGen generates modular IaC using AVM modules
- [ ] IaC Validation Pipeline passes (fmt + validate + lint)
- [ ] Standards validates naming/tags — passes
- [ ] Security scans — passes (no critical/high findings)
- [ ] H1 gate shows generated code + Mermaid architecture diagram
- [ ] PR created in target repo with structured description
- [ ] GitHub Actions runs plan; H2 gate shows plan output
- [ ] Deployment succeeds; all stage transitions visible in real-time
- [ ] **Target:** < 3 minutes from first message to open PR

## Tech Details
- This is Demo 1 from PRD Section 12.1
""" },

  { "ref": "44",
    "title": "[EPIC 10][REF #44] End-to-end integration: Catalog path (Demo 2)",
    "labels": ["integration", "e2e", "demo"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 11-13) | **Assignee:** E4 + E3
**Depends on:** REF #26, REF #29, REF #31, REF #33, REF #38
**Blocks:** REF #46

## Description
Wire everything together for the catalog path: browse catalog → select AKS template → fill parameters → subscription discovery → hydrate → validate → H1 → PR → plan → H2 → deploy.

## Acceptance Criteria
- [ ] User opens catalog, searches "AKS cluster"
- [ ] Template detail view shows parameters
- [ ] User fills parameters and clicks deploy
- [ ] Subscription discovery verifies target resource group, checks naming conflicts and quota
- [ ] Template hydrated with org naming/tags applied
- [ ] IaC Validation Pipeline runs
- [ ] H1 gate shows parameterized code; PR created, plan runs, H2 approval, deployment succeeds
- [ ] **Target:** < 1 minute from deploy click to open PR

## Tech Details
- This is Demo 2 from PRD Section 12.1
- Catalog path skips consulting, iterative codegen/standards/security loops
""" },

  { "ref": "45",
    "title": "[EPIC 10][REF #45] End-to-end integration: Plan failure + rework (Demo 3)",
    "labels": ["integration", "e2e", "demo"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 2-3 (Day 12-14) | **Assignee:** E4 + E2
**Depends on:** REF #31, REF #43
**Blocks:** REF #46

## Description
Wire and test the plan-failure rework loop: AKS request → code generated → plan fails (SKU unavailable) → Deploy Agent categorizes → CodeGen reworks → re-validates → new PR → plan succeeds → deploy.

## Acceptance Criteria
- [ ] User requests AKS cluster via chat; CodeGen generates Terraform
- [ ] Validation passes; H1 approved, PR created
- [ ] `terraform plan` fails: "VM size Standard_D4s_v3 not available in westeurope"
- [ ] Deploy Agent categorizes as `sku_unavailable` (fixable in code)
- [ ] CodeGen queries Azure MCP for available SKUs, updates VM size
- [ ] Code re-enters validation pipeline → passes; new PR created, plan succeeds
- [ ] H2 approval, deployment succeeds
- [ ] UI shows plan-failure rework iteration indicator (Loop 2 iteration 1 of 2)

## Tech Details
- This is Demo 3 from PRD Section 12.1; Loop 2 max = 2 iterations
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 11: Observability
  # ════════════════════════════════════════════════════════════
  { "ref": "46a",
    "title": "[EPIC 11][REF #46a] Implement observability adapter (OpenTelemetry + App Insights)",
    "labels": ["backend", "observability"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E1
**Depends on:** REF #4, REF #6

## Description
Implement the `IObservabilityPort` adapter wrapping OpenTelemetry for tracing, metrics, and logging. Export to Azure App Insights.

## Acceptance Criteria
- [ ] `src/infrastructure/adapters/otel_adapter.py` implementing `IObservabilityPort`
- [ ] `start_span(name, attributes)` — OpenTelemetry spans
- [ ] `record_metric(name, value, tags)` — Custom metrics
- [ ] `log(level, message, **kwargs)` — Structured logging
- [ ] Trace hierarchy: API route → use case → LLM call → MCP tool call → IaC validation step
- [ ] Key metrics: `infraagent.chat.latency`, `infraagent.subscription_discoveries`, `infraagent.generate.iterations`, `infraagent.generate.max_iterations_reached`, `infraagent.iac_validation.failures`, `infraagent.plan_rework.iterations`, `infraagent.plan_rework.category`, `infraagent.prs_created`, `infraagent.deployments_triggered/succeeded/failed`, `infraagent.token_usage`, `infraagent.mcp.call_latency`
- [ ] Export to Azure App Insights via `azure-monitor-opentelemetry-exporter`
- [ ] Graceful no-op if connection string not configured

## Tech Details
- Use `opentelemetry-api`, `opentelemetry-sdk`, `azure-monitor-opentelemetry-exporter`
- Ref: TechSpec Section 14
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 12: Polish & Demo Preparation
  # ════════════════════════════════════════════════════════════
  { "ref": "46",
    "title": "[EPIC 12][REF #46] Demo script rehearsal and edge case hardening",
    "labels": ["demo", "polish"],
    "body": """\
**Priority:** P0 | **Size:** L | **Week:** 3 (Day 13-15) | **Assignee:** ALL
**Depends on:** REF #43, REF #44, REF #45

## Description
Rehearse all 3 demo scenarios end-to-end against a real Azure subscription. Identify and fix edge cases, timing issues, and UI polish items.

## Acceptance Criteria
- [ ] Demo 1 (Chat path — 3-4 min) runs end-to-end against real Azure subscription
- [ ] Demo 2 (Catalog path — 1-2 min) runs end-to-end
- [ ] Demo 3 (Plan failure + rework — 2-3 min) runs end-to-end
- [ ] Subscription discovery surfaces real resources in demo subscription
- [ ] Architecture diagrams render correctly for all demo scenarios
- [ ] Edge cases handled: network timeouts, MCP unavailability, GitHub Actions delays, LLM rate limiting
- [ ] **Performance validation:** < 3 min chat path to PR; < 1 min catalog path to PR
- [ ] UI polished: loading states, error messages, stage transition animations
- [ ] Recording backup prepared (screen recording of successful demo run)
- [ ] Demo environment pre-seeded: Azure subscription has existing VNet, resource groups, naming patterns

## Tech Details
- Ref: PRD Section 12.1
""" },

  { "ref": "47",
    "title": "[EPIC 12][REF #47] UI polish and responsive design",
    "labels": ["frontend", "polish"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 3 (Day 13-14) | **Assignee:** E3
**Depends on:** REF #37, REF #38, REF #39

## Description
Final UI polish pass: loading states, error handling, responsive layout, keyboard shortcuts, and visual consistency.

## Acceptance Criteria
- [ ] Consistent loading skeletons on all data-fetching components
- [ ] Error boundaries with user-friendly error messages
- [ ] Responsive layout for 13" laptop screens (primary demo device)
- [ ] Keyboard shortcuts: Enter to send, Shift+Enter for new line
- [ ] Copy-to-clipboard on code blocks
- [ ] Proper empty states on all list views
- [ ] Favicon and page titles set
- [ ] Stage transition animations (smooth progress bar)
- [ ] Plan output color coding: green for create, yellow for modify, red for destroy
- [ ] Destructive change warning prominently displayed (red banner)
""" },

  { "ref": "48",
    "title": "[EPIC 12][REF #48] Update pitch deck and documentation",
    "labels": ["docs", "demo"],
    "body": """\
**Priority:** P0 | **Size:** S | **Week:** 3 (Day 14-15) | **Assignee:** E5
**Depends on:** REF #46

## Description
Update the hackathon pitch deck with final architecture screenshots, demo GIFs/screenshots, and metrics from demo runs.

## Acceptance Criteria
- [ ] Pitch deck updated with: actual architecture diagram, UI screenshots from all 3 demo paths, performance metrics
- [ ] README.md updated with current setup instructions
- [ ] Deviations from PRD/TechSpec documented (implemented vs. designed)
- [ ] API reference reflects actual implemented endpoints
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 13: P1 Stretch Features
  # ════════════════════════════════════════════════════════════
  { "ref": "49",
    "title": "[EPIC 13][REF #49] Template Curation Agent (post-deploy feedback loop)",
    "labels": ["agents", "knowledge-wiki", "p1-stretch"],
    "body": """\
**Priority:** P1 | **Size:** XL | **Week:** 3 (stretch) | **Assignee:** E5
**Depends on:** REF #43

## Description
Implement the Template Curation Agent that runs post-deployment to analyze deployed custom code, check novelty against existing wiki templates, generalize parameters, and propose a new template via PR.

## Acceptance Criteria
- [ ] Post-deploy trigger: after successful deployment via chat path
- [ ] Novelty check: compares deployed resources against existing wiki templates
- [ ] Parameter generalization: extracts hardcoded values into configurable parameters
- [ ] Generates `metadata.yaml` for the proposed template
- [ ] Opens PR to the knowledge wiki repo (not InfraAgent repo)
- [ ] **Human Gate H3:** Platform engineer reviews and approves the template PR
- [ ] Approved templates appear in catalog after submodule update
""" },

  { "ref": "50",
    "title": "[EPIC 13][REF #50] Conversation memory persistence",
    "labels": ["backend", "p1-stretch"],
    "body": """\
**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E1
**Depends on:** REF #10, REF #32

## Description
Persist chat history across sessions so users can return to previous conversations.

## Acceptance Criteria
- [ ] Conversations saved to PostgreSQL `conversations` + `messages` tables
- [ ] Chat UI shows conversation list sidebar with recent conversations
- [ ] User can click a previous conversation to reload history and continue
- [ ] Conversation title auto-generated from first user message
""" },

  { "ref": "51",
    "title": "[EPIC 13][REF #51] Cost estimation integration",
    "labels": ["backend", "p1-stretch"],
    "body": """\
**Priority:** P1 | **Size:** L | **Week:** 3 (stretch) | **Assignee:** E2
**Depends on:** REF #19

## Description
Integrate Infracost (Terraform) or Azure Pricing Calculator API to show estimated monthly cost before deployment.

## Acceptance Criteria
- [ ] For Terraform: run `infracost breakdown --path <dir> --format json` on generated code
- [ ] Cost estimate shown alongside plan output at H2 review
- [ ] Monthly cost breakdown by resource
""" },

  { "ref": "52",
    "title": "[EPIC 13][REF #52] Set Diff Analyzer for plan review",
    "labels": ["backend", "deploy", "p1-stretch"],
    "body": """\
**Priority:** P1 | **Size:** M | **Week:** 3 (stretch) | **Assignee:** E4
**Depends on:** REF #31

## Description
Filter false-positive diffs in Terraform plan output caused by AzureRM Set-type attribute reordering.

## Acceptance Criteria
- [ ] Categorize changes: 🟢 order-only (safe to ignore), 🟡 actual Set changes (review content), 🔴 resource replacement (check downtime impact)
- [ ] Frontend `PlanDiffViewer.tsx` shows filtered view by default with option to show all
- [ ] Relevant for Application Gateway backend pools, NSG security rules

## Tech Details
- Parse `terraform plan -json`, detect Set-type attributes, compare content ignoring order
- Ref: PRD Section 7.1.8
""" },

  { "ref": "53",
    "title": "[EPIC 13][REF #53] IaC language toggle mid-conversation",
    "labels": ["frontend", "p1-stretch"],
    "body": """\
**Priority:** P1 | **Size:** S | **Week:** 3 (stretch) | **Assignee:** E3
**Depends on:** REF #37

## Description
Allow user to switch between Terraform and Bicep mid-conversation.

## Acceptance Criteria
- [ ] Language toggle in chat header (Terraform / Bicep)
- [ ] Switching language re-triggers code generation in the new language
- [ ] Previous code shown as "previous version" in file explorer
""" },

  # ════════════════════════════════════════════════════════════
  # EPIC 14: Risk Mitigations
  # ════════════════════════════════════════════════════════════
  { "ref": "54",
    "title": "[EPIC 14][REF #54] Implement graceful degradation for MCP server unavailability",
    "labels": ["backend", "resilience"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 8-9) | **Assignee:** E1
**Depends on:** REF #22

## Description
When MCP servers are unavailable, agents should fall back to plain LLM generation with cached schemas rather than failing.

## Acceptance Criteria
- [ ] MCP health check on startup and periodically (every 60 seconds)
- [ ] When MCP is down, CodeGen generates code with warning: "Generated without live registry grounding — review carefully"
- [ ] `GenerateResult` includes `grounded: bool` flag
- [ ] Frontend surfaces "ungrounded" warning badge when `grounded=false`
- [ ] Cached provider schemas available as fallback (basic `azurerm` resources)
- [ ] Logged as warning metric: `infraagent.mcp.degraded_generations`
""" },

  { "ref": "55",
    "title": "[EPIC 14][REF #55] Implement Foundry Agent Service fallback orchestration",
    "labels": ["backend", "resilience"],
    "body": """\
**Priority:** P0 | **Size:** M | **Week:** 2 (Day 9-10) | **Assignee:** E1
**Depends on:** REF #23, REF #25

## Description
If Foundry Agent Service workflow API has limitations, implement a simpler fallback orchestration using direct agent calls.

## Acceptance Criteria
- [ ] `src/infrastructure/agents/simple_orchestrator.py` — Sequential pipeline using direct `AIProjectClient.agents` calls
- [ ] Same pipeline sequence: consult → codegen → validation → standards → security → H1 → PR → plan → H2 → deploy
- [ ] Same maker-checker loop logic (max 3 iterations)
- [ ] Same plan-failure rework logic (max 2 iterations)
- [ ] Human gates as simple async waits on approval endpoints
- [ ] Swappable via config flag: `USE_SIMPLE_ORCHESTRATOR=true`
- [ ] Passes the same integration tests as the Agent Framework orchestrator

## Tech Details
- Escape hatch if the Agent Framework graph workflow API proves too complex or buggy
""" },
]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Step 1: create labels ─────────────────────────────────────────────────
    print("=== Step 1: Ensuring labels exist ===")
    for name, color in LABELS:
        run(f'gh label create "{name}" --color "{color}" --repo {OWNER}/{REPO} --force')
        print(f"  label: {name}")

    # ── Step 2: load existing issues (to skip duplicates) ─────────────────────
    print("\n=== Step 2: Fetching existing issues ===")
    existing = get_existing_issues()
    print(f"  Found {len(existing)} existing issues")

    # ── Step 3: create issues, build ref → github_number map ─────────────────
    print(f"\n=== Step 3: Creating {len(ISSUES)} issues ===")
    ref_map: dict[str, int] = {}

    for idx, issue in enumerate(ISSUES, 1):
        ref  = issue["ref"]
        title = issue["title"]
        print(f"  [{idx:02d}/{len(ISSUES)}] {title[:70]}")

        number = create_issue(title, issue["body"], issue["labels"], existing)
        if number:
            ref_map[ref] = number
            add_to_project(number)
            print(f"           → #{number} (added to project)")
        time.sleep(0.4)   # gentle rate-limiting

    print(f"\n  ref_map built: {len(ref_map)} entries")

    # ── Step 4: patch bodies — replace REF #X with real #N ───────────────────
    print(f"\n=== Step 4: Patching cross-references in issue bodies ===")
    for issue in ISSUES:
        ref = issue["ref"]
        number = ref_map.get(ref)
        if not number:
            print(f"  SKIP REF #{ref} — not found in ref_map")
            continue

        patched = resolve_refs(issue["body"], ref_map)
        if patched != issue["body"]:
            patch_body(number, patched)
            print(f"  Patched #{number} (REF #{ref})")
        else:
            print(f"  No changes needed for #{number} (REF #{ref})")
        time.sleep(0.3)

    print("\n=== Done ===")
    print(f"Created/verified: {len(ref_map)} issues")
    print("All cross-references resolved to real GitHub issue numbers.")


if __name__ == "__main__":
    main()
