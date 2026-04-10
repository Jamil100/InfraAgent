# InfraAgent — Copilot Instructions

## Project Context

InfraAgent is a multi-agent platform built for the Capgemini Microsoft Global Partner Hackathon 2026. It converts natural-language infrastructure requests into production-ready, standards-compliant IaC (Bicep primary, Terraform secondary) via an AI-powered pipeline on Azure AI Foundry.

## Architecture

- **Clean architecture** (ports & adapters): domain models in `core/models.py`, port interfaces in `core/ports.py`, adapters implement ports
- **Pipeline**: `OrchestratorPipeline` in `services/pipeline.py` drives stages: Consulting → CodeGen ↔ Review Loop (max 3×) → Human Gate H1 → PR
- **Agents**: Foundry-hosted agents created via `agents/factory.py` with markdown system prompts in `agents/prompts/`
- **API**: FastAPI backend in `backend/` with routes in `api/routes.py`

## Code Conventions

- **Python 3.11+** with `from __future__ import annotations`
- **Async/await** for all I/O operations
- **Pydantic v2** for all data models (use `BaseModel`, `Field`, `model_dump`)
- **Type hints** on all function signatures
- **Ruff** for linting and formatting
- **uv** for dependency management (`pyproject.toml`, not `requirements.txt`)

## Key Patterns

- Agents return structured JSON in markdown fences (` ```json ... ``` `) parsed into Pydantic models
- Never hardcode model names — use `settings.model_deployment` which points to ModelRouter
- Port interfaces are ABCs in `core/ports.py` — new external integrations must implement a port
- `ValidationFinding` is the universal format for all review feedback (standards, security, validation)
- `PipelineState` tracks full run state and is yielded at each stage transition

## IaC Generation Rules

- **Bicep-first**: Default to Bicep; only generate Terraform if `iac_language == "terraform"`
- **AVM-first**: Use Azure Verified Modules (`br/public:avm/res/...`) wherever available
- **Required tags**: `environment`, `project`, `managed-by: infraagent` on all resources
- **No hardcoded secrets**: Use Key Vault references or `@secure()` decorator
- **Parameterized names**: `{env}-{project}-{resource}` pattern

## File Organization

```
backend/src/
├── config.py          # Settings from env vars
├── core/              # Domain models + port interfaces (zero deps)
├── agents/            # Foundry agent implementations + system prompts
├── adapters/          # External integration adapters (GitHub, etc.)
├── services/          # Pipeline orchestration
└── api/               # FastAPI routes + dependencies
```

## Stack

| Layer | Technology |
|---|---|
| AI Platform | Azure AI Foundry Agent Service |
| Framework | Microsoft Agent Framework (`agent-framework`) |
| Backend | Python · FastAPI · uvicorn |
| IaC | Bicep (primary) · Terraform (deferred) |
| MCP | Bicep MCP · Terraform MCP · Azure MCP |
| Auth | `DefaultAzureCredential` via `azure-identity` |
| SCM | GitHub REST API |
| Deps | uv + pyproject.toml |

## Documentation

- Architecture: `docs/architecture.md`
- Setup: `docs/setup.md`
- Agents: `docs/agents.md`
- API: `docs/api-reference.md`
- MCP Servers: `docs/mcp-servers.md`
- ADRs: `docs/decisions/`
