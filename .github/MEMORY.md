# InfraAgent Development Memory

## Project Overview
- **Project:** InfraAgent - AI-powered multi-agent IaC generation on Azure AI Foundry
- **Timeline:** 3 weeks (April 2026), 5 engineers, 55 total issues (50 P0, 5 P1)
- **Working Directory:** `c:\Users\malbouha\Documents\Capgemini\Projects\InfraAgent\InfraAgent`

## Completed Work

### Issue #13: Implement Terraform CLI Adapter (IInfraProviderPort) ✅
**Status:** COMPLETE
**Approach:** Full async adapter implementing IInfraProviderPort with plan/apply coupling using UUID-based temp directories

**Key Accomplishments:**
- Created `src/infrastructure/adapters/terraform_adapter.py` (549 lines) with TerraformInfraProviderAdapter class
- Implemented all 6 methods per IInfraProviderPort interface:
  1. `format_check(files)` - runs `terraform fmt -check` → ValidationResult
  2. `validate(files)` - runs `terraform init -backend=false` + `terraform validate -json` → ValidationResult
  3. `lint(files)` - runs `tflint` (optional, graceful if missing) → ValidationResult
  4. `plan(files, variables)` - runs `terraform plan -json -out=tfplan` → PlanResult with resource counts
  5. `apply(plan_id)` - runs `terraform apply` using stored plan → ApplyResult
  6. `get_language()` - returns "terraform" (non-async)
- 5 helper methods for CLI execution and output parsing:
  - `_write_files()` - atomic file placement to temp directories
  - `_write_tfvars()` - JSON variable encoding with jsonDecode()
  - `_parse_tf_plan_json()` - counts create/update/delete actions from JSON output
  - `_parse_tf_validate_json()` - extracts diagnostics with severity levels
  - `_parse_tflint_output()` - parses lint warnings/errors from text output
- UUID-based temp directory storage for plan→apply coupling (stateless, resilient cleanup)
- JSON-based terraform.tfvars generation (no dependencies, type-safe)
- Comprehensive error handling: FileNotFoundError, JSON parsing errors, graceful CLI fallback
- Exit code logic per Terraform spec: fmt(0/3), validate(0), plan(0/2), apply(0)

**Testing & Verification:**
- 40+ unit test cases using mocked subprocess execution
- Coverage: success paths, error paths, CLI not installed, malformed JSON
- Manual verification of all core functionality passed ✓
- All dataclass integration tests verified
- Test file: `tests/unit/infrastructure/adapters/test_terraform_adapter.py` (457 lines)

**Architectural Decisions (ADR-006):**
- Plan storage: UUID-temp dirs (MVP-appropriate, can upgrade to persistent storage later)
- tflint: Optional (graceful warning if not installed per stretch goal)
- Variables: JSON-based with jsonDecode() (simple, no extra dependencies)
- Types: Dataclass ports vs Pydantic domain (clean architecture per ADR-003)

**Files Changed:**
- `src/infrastructure/adapters/terraform_adapter.py` - New adapter (549 lines)
- `src/infrastructure/adapters/__init__.py` - Export adapter
- `tests/unit/infrastructure/adapters/test_terraform_adapter.py` - Unit tests (457 lines)
- `docs/decisions/ADR-006-unified-iac-provider-with-terraform.md` - Architectural decision record

**Dependencies:**
- Depends on: Issue #4 ✅ (IInfraProviderPort interface + dataclasses)
- Blocks: Issue #15, Issue #24, Issue #32
- External: Terraform CLI must be installed on system (not in Python requirements)

### Issue #4: Define All Port Interfaces (Application Layer Contracts) ✅
**Status:** COMPLETE
**Approach:** Implemented all 12 ports and 16 dataclasses per TechSpec 2.1, using dual-support pattern

**Key Accomplishments:**
- Rewrote `src/application/ports/ports.py` (~500 lines) with complete TechSpec 2.1 compliance
- **7 new ports from TechSpec:**
  1. `ILLMCompletionPort` - LLM provider abstraction with ModelRouter task profiles
  2. `IInfraProviderPort` - Unified Terraform+Bicep interface (replaces split design)
  3. `ISourceControlPort` - Extended with workflow trigger & pipeline status methods
  4. `IPolicyEnginePort` - Policy validation (naming, tags, security)
  5. `ITemplateRegistryPort` - Knowledge wiki abstraction
  6. `IObservabilityPort` - OpenTelemetry wrapper
  7. `ISubscriptionDiscoveryPort` - Extended with SKU/quota checks
- **5 legacy ports retained:** `ICodeGenPort`, `IValidationPort`, `IStandardsPort`, `ISecurityPort`, `IDeployPort`
- **16 dataclasses:** All with proper field defaults using stdlib `@dataclass` decorator
- Updated `src/application/ports/__init__.py` with all 28 public exports

**Architectural Decision (Dual-Support Pattern):**
- **Ports layer:** Uses dataclasses (canonical contracts, per TechSpec)
- **Domain/Infrastructure layers:** Continue using Pydantic models
- **Boundary conversion:** Deferred to adapter issues; zero breaking changes to existing code

**Verification:**
- All 12 ports abstract ✓ (raise TypeError on instantiation)
- All 16 dataclasses instantiate correctly ✓
- All 28 symbols exported via `__init__.py` ✓
- TechSpec 2.1 full compliance verified ✓

### Issue #1: Initialize Monorepo with Clean Architecture ✅
**Status:** COMPLETE
**Approach:** Consolidated `backend/src/` → `src/` at root level for true monorepo structure

**Key Accomplishments:**
- Clean architecture structure per TechSpec Section 11:
  - `src/domain/` - Pure business logic (models, policies, services)
  - `src/application/` - Use cases and port ABCs
  - `src/infrastructure/` - Adapters, agents, MCP configuration
  - `src/api/` - FastAPI routes and schemas
  - `src/prompts/` - Agent system prompts (4 markdown files)
  - `tests/` - Unit, integration, fixtures structure

- Configuration files created:
  - `pyproject.toml` - Python 3.12, new deps (sqlalchemy[asyncio], asyncpg, alembic, mypy)
  - `ruff.toml` - Code linting rules
  - `mypy.ini` - Strict type checking
  - `Dockerfile` - Python 3.12-slim + FastAPI
  - `docker-compose.yml` - Backend service only (postgres deferred to #10)

- Code migration: 34 Python files + 4 prompts moved and imported updated
- All files compile successfully (Python 3.12)
- 26 __init__.py files created across package structure

**Dependencies Added:**
- Runtime: sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings
- Dev: mypy

**Deferred to Future Issues:**
- Bicep modules → Issue #6
- CI/CD workflows → Issue #7

## Architecture Decisions

### Backend Consolidation
- **Decision:** MOVE `backend/src/` to `src/` at root
- **Rationale:** True monorepo consolidation, cleaner architecture, single source of truth
- **Note:** Old `backend/` directory retained for reference, can be deleted after testing

### Import Structure
All imports updated to new clean architecture paths:
- `src.adapters.*` → `src.infrastructure.adapters.*`
- `src.agents.*` → `src.infrastructure.agents.*`
- `src.core.models` → `src.domain.models.models`
- `src.core.ports` → `src.application.ports.ports`
- `src.services.*` → `src.domain.services.*`

## Critical Path
```
#1 → #4 → #11 → #18 → #23 → #25 → #32 → #43 → #46
     ↓
#13/#14 → #19 → #24 → #27/#28 → #43
     ↓
#12 → #20 → #29/#31 → #44/#45
     ↓
#8 → #9 → #15 → #33 → #38/#44
```

## File Locations
- **Plan:** `C:\Users\malbouha\.claude\plans\flickering-gathering-parasol.md`
- **GitHub Issues:** InfraAgent/GITHUB_ISSUES.md (55 issues total)
- **Technical Spec:** InfraAgent/docs/ (v2.0)

## Next Issues to Implement
1. **Issue #2-#3:** Domain layer (models, policies)
2. **Issue #5:** IaC parser for HCL/Bicep resource extraction
3. **Issue #14:** Bicep CLI adapter (blocked by #4, parallel to #13) → unblocked now
4. **Issue #15:** Bicep self-deployment infrastructure (blocks #24)
5. **Issue #6:** Bicep modules as AVM references
6. **Issue #7:** CI/CD pipelines

## User Preferences
- Command style: Direct, concise, action-oriented
- Documentation: Clear, structured
- Git usage: Commits with proper messages, preserve history
- Testing: Strict type checking (mypy), code formatting (ruff)
