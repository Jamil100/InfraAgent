# InfraAgent Development Memory

## Project Overview
- **Project:** InfraAgent - AI-powered multi-agent IaC generation on Azure AI Foundry
- **Timeline:** 3 weeks (April 2026), 5 engineers, 55 total issues (50 P0, 5 P1)
- **Working Directory:** `c:\Users\malbouha\Documents\Capgemini\Projects\InfraAgent\InfraAgent`

## Completed Work

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
1. **Issue #2-#4:** Domain layer (models, policies, ports)
2. **Issue #5-#6:** Infrastructure adapters (IaC parser, Bicep)
3. **Issue #7:** CI/CD pipelines
4. **Issue #8-#9:** Knowledge wiki setup and templates
5. **Issue #10:** Database schema and migrations

## User Preferences
- Command style: Direct, concise, action-oriented
- Documentation: Clear, structured
- Git usage: Commits with proper messages, preserve history
- Testing: Strict type checking (mypy), code formatting (ruff)
