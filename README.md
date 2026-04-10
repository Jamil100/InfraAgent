# InfraAgent

> AI-powered multi-agent platform that converts natural language infrastructure requests into production-ready, standards-compliant IaC (Bicep & Terraform). Built on Azure AI Foundry.

## Architecture

```
User → Chat UI → Consulting Agent → CodeGen Agent ↔ Review Loop → PR → Plan → Deploy
                                        ↕ (max 3 iterations)
                              Standards Agent + Security Agent
```

**Agents**: Consulting · CodeGen · Standards · Security · PR Workflow · Deploy  
**Review Loop**: CodeGen → Standards + Security checks → fix errors → retry (max 3×)  
**Human Gates**: H1 (code review before PR), H2 (plan review before deploy)

## Quick Start

```bash
# 1. Clone & setup
cd backend
uv sync

# 2. Configure
cp ../.env.example ../.env
# Edit .env with your Foundry endpoint, Azure subscription, and GitHub token

# 3. Run
uv run uvicorn main:app --reload --port 8000
```

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/chat` | POST | Chat with the Consulting Agent |
| `/api/pipeline/start` | POST | Kick off CodeGen → Review → PR pipeline |
| `/api/pipeline/status/{id}` | GET | Check pipeline status |

## Project Structure

```
backend/
├── main.py                    # FastAPI entry point
├── pyproject.toml             # Dependencies (uv)
└── src/
    ├── config.py              # Environment configuration
    ├── core/
    │   ├── models.py          # Domain models (PipelineState, etc.)
    │   └── ports.py           # Port interfaces (ABC)
    ├── agents/
    │   ├── factory.py         # Agent creation via Foundry SDK
    │   ├── consulting.py      # Requirements gathering
    │   ├── codegen.py         # IaC code generation
    │   ├── reviewers.py       # Standards + Security review
    │   └── prompts/           # System prompts (markdown)
    ├── services/
    │   └── pipeline.py        # Orchestrator pipeline
    ├── adapters/
    │   └── github_adapter.py  # GitHub REST API integration
    └── api/
        ├── routes.py          # FastAPI routes
        └── dependencies.py    # Shared DI (Foundry client)
```

## Tech Stack

- **AI**: Azure AI Foundry Agent Service + ModelRouter
- **Backend**: Python · FastAPI · azure-ai-projects SDK
- **IaC**: Bicep (primary) · Terraform (secondary)
- **MCP Servers**: Bicep MCP · Terraform MCP · Azure MCP
- **Source Control**: GitHub REST API for branches, commits, PRs

## Team — Terraformers Anonymous

Built for the Capgemini Microsoft Global Partner Hackathon 2026.

## License

Apache 2.0 — see [LICENSE](LICENSE)
