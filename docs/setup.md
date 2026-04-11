# Developer Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 20+ | Frontend runtime |
| **uv** | latest | Package manager (replaces pip/venv) |
| **Azure CLI** | latest | Authentication + subscription access |
| **Docker Desktop** | latest | Terraform MCP Server, GitHub MCP Server, local PostgreSQL |
| **.NET SDK** | 9.0+ | Bicep MCP Server |
| **Git** | latest | Source control + submodule support |
| **VS Code** | latest | IDE |

### VS Code Extensions (required)

| Extension | Purpose |
|---|---|
| **Azure AI Toolkit** | Foundry agent management, Model Playground, Agent Inspector |
| **GitHub Copilot** + **Copilot Chat** | AI pair programming + custom agents/prompts |
| **Python** (ms-python) | Python language support |
| **Bicep** (ms-azuretools) | Bicep language support + MCP server |
| **Azure Tools** | Azure resource management |

### VS Code Extensions (recommended)

| Extension | Purpose |
|---|---|
| **Ruff** | Python linting + formatting |
| **Docker** | Container management |
| **Terraform** (HashiCorp) | Terraform language support |

## Step-by-Step Setup

### 1. Clone the Repository (with Knowledge Wiki Submodule)

```bash
git clone https://github.com/<org>/terrabot.git
cd "Terraformers Anonymous"

# Initialize the knowledge wiki submodule
git submodule update --init --recursive
```

This populates `knowledge-wiki/` with templates, skills, standards, and patterns from the separate wiki repo.

### 2. Install Backend Dependencies

```bash
cd backend
uv sync
```

This creates a `.venv` automatically and installs all dependencies from `pyproject.toml`.

For development extras (pytest, ruff, mypy):

```bash
uv sync --extra dev
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Azure AI Foundry — get from AI Toolkit > Microsoft Foundry Resources > your project
PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-id>
MODEL_DEPLOYMENT_NAME=<model-router-endpoint-or-deployment-name>

# Azure — get from az account show
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_TENANT_ID=<your-tenant-id>

# GitHub — create a fine-grained PAT with repo + workflow permissions
GITHUB_TOKEN=ghp_<your-token>
GITHUB_REPO_OWNER=<org-or-user>
GITHUB_REPO_NAME=terrabot
GITHUB_TARGET_BRANCH=main

# Database — local PostgreSQL for development
DATABASE_URL=postgresql+asyncpg://infraagent:devpassword@localhost:5432/infraagent

# MCP Servers — leave blank to skip; set when running MCP servers locally
# MCP_BICEP_URL=http://localhost:5007/mcp
# MCP_TERRAFORM_URL=http://localhost:5008/mcp
# MCP_AZURE_URL=http://localhost:5009/mcp
# MCP_GITHUB_URL=http://localhost:5010/mcp

# AI Search — for Policy RAG and template search (optional for local dev)
# AI_SEARCH_ENDPOINT=https://<search-name>.search.windows.net
# AI_SEARCH_INDEX=standards-policies

# Key Vault — for production secrets (optional for local dev)
# KEY_VAULT_URI=https://<vault-name>.vault.azure.net/

# Deployment — leave blank to stop pipeline at PR; set to enable the deploy stage
# DEPLOY_RESOURCE_GROUP=rg-infraagent-dev
# DEPLOY_LOCATION=eastus
```

### 4. Set Up Local Database

InfraAgent uses PostgreSQL for conversations, deployments, and settings.

```bash
# Start PostgreSQL via Docker
docker run -d --name infraagent-postgres \
  -e POSTGRES_USER=infraagent \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=infraagent \
  -p 5432:5432 \
  postgres:16

# Verify connection
docker exec infraagent-postgres pg_isready -U infraagent
```

Run database migrations:

```bash
cd backend
uv run alembic upgrade head
```

### 5. Authenticate with Azure

```bash
az login
az account set --subscription <your-subscription-id>
```

This enables `DefaultAzureCredential` used by the backend for Foundry, Azure MCP, and other Azure services.

### 6. Run the Backend

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

Verify: `http://localhost:8000/health` should return `{"status": "ok", "version": "0.1.0"}`.

### 7. Set Up and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Verify: `http://localhost:3000` should open the InfraAgent interface with Chat and Self-Service Catalog entry points.

The frontend expects the backend at `http://localhost:8000`. To override, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 8. Run Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v --tb=short

# Run only unit tests (fast, no external deps)
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

See [testing.md](testing.md) for the full testing strategy.

## MCP Server Setup

MCP servers are configured in `.vscode/mcp.json` and used both by Copilot Chat (locally) and eventually by Foundry-hosted agents (remote HTTP). All four servers are optional for local development — agents degrade gracefully when MCP is unavailable.

### Bicep MCP Server

```bash
dotnet tool install -g Microsoft.BicepMcp
```

Start it (runs on port 5007 by default):

```bash
bicep-mcp
```

Set in `.env`: `MCP_BICEP_URL=http://localhost:5007/mcp`

### Terraform MCP Server

Requires Docker Desktop running:

```bash
docker pull hashicorp/terraform-mcp-server:0.5.1
```

The server launches automatically via `.vscode/mcp.json` when Copilot invokes it. For backend use, start it manually:

```bash
docker run -p 5008:8080 hashicorp/terraform-mcp-server:0.5.1 -transport=http
```

Set in `.env`: `MCP_TERRAFORM_URL=http://localhost:5008/mcp`

### Azure MCP Server

```bash
uv tool install msmcp-azure
```

Or via the **Azure MCP** VS Code extension (installs automatically). The server launches via the `msmcp-azure` command in `.vscode/mcp.json`.

For backend use, start it as an HTTP server:

```bash
msmcp-azure --transport http --port 5009
```

Set in `.env`: `MCP_AZURE_URL=http://localhost:5009/mcp`

### GitHub MCP Server

Requires Docker Desktop running:

```bash
docker pull ghcr.io/github/github-mcp-server
```

Start it with your GitHub PAT:

```bash
docker run -p 5010:8080 \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_<your-token> \
  ghcr.io/github/github-mcp-server
```

Set in `.env`: `MCP_GITHUB_URL=http://localhost:5010/mcp`

The PAT needs `repo` and `workflow` scopes. See [mcp-servers.md](mcp-servers.md) for full details.

## Connecting to AI Toolkit

1. Open the **AI Toolkit** sidebar in VS Code
2. Under **My Resources** → **Microsoft Foundry Resources**, click **Set Default Project**
3. Select (or create) your Foundry project
4. Verify connection: expand **Connected Resources** — you should see your model deployments

### ModelRouter Setup

InfraAgent uses Azure AI Foundry **ModelRouter** for automatic model selection. Agents declare task profiles (e.g., `complex-reasoning`, `code-generation`) instead of specific model names. ModelRouter routes requests to the optimal model based on cost, capability, and availability.

Ensure your Foundry project has these model deployments available:

| Model | Deployment Type | Used By (via ModelRouter) |
|---|---|---|
| GPT-4o | GlobalStandard | Consulting, CodeGen, Deploy, Orchestrator |
| GPT-4o-mini | GlobalStandard | Standards, Security, PR Workflow |

ModelRouter is configured at the Foundry project level. The `MODEL_DEPLOYMENT_NAME` env var should point to the ModelRouter endpoint or a specific deployment for fallback.

### Using Model Playground

1. AI Toolkit → **Model Playground**
2. Select a deployed model (e.g., GPT-4o)
3. Paste agent system prompts from `backend/src/agents/prompts/` to iterate on them
4. Test with sample infrastructure requests

### Using Agent Inspector

1. AI Toolkit → **Agent Inspector**
2. Connect to a running agent's thread to view conversation history
3. Useful for debugging agent JSON output parsing issues

## Knowledge Wiki

The knowledge wiki is a **separate GitHub repository** containing reusable IaC templates, domain skills, organizational standards, and architecture patterns. It's consumed by InfraAgent as a git submodule at `knowledge-wiki/`.

### Structure

```
knowledge-wiki/
├── templates/          # Pre-validated IaC templates (shown in Self-Service Catalog)
│   ├── aks-cluster/
│   │   ├── metadata.yaml
│   │   ├── terraform/
│   │   └── bicep/
│   └── 3-tier-web-app/
├── skills/             # Domain skills for the Consulting Agent
│   ├── general-azure/
│   └── foundry-ads-session/
├── standards/          # Organizational policies (naming, tagging)
│   ├── naming.md
│   ├── tagging.md
│   └── policies.md
└── patterns/           # Architecture decision records
    └── adr/
```

### Updating the Wiki

```bash
# Pull latest wiki content
git submodule update --remote knowledge-wiki

# Commit the updated submodule reference
git add knowledge-wiki
git commit -m "chore: update knowledge wiki to latest"
```

The wiki repo has its own CI pipeline that validates template syntax (`terraform validate` / `bicep build`) and metadata schema before merge.

## Troubleshooting

### `uv sync` fails

```bash
# Ensure uv is installed
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
```

### `DefaultAzureCredential` authentication errors

```bash
# Re-authenticate
az login --tenant <your-tenant-id>
az account set --subscription <your-subscription-id>

# Verify
az account show
```

### Bicep MCP not connecting

```bash
# Check if it's running
curl http://localhost:5007/mcp

# Restart
bicep-mcp
```

### Docker not available for Terraform/GitHub MCP

Ensure Docker Desktop is running. On Windows, check WSL2 backend is enabled.

### PostgreSQL connection refused

```bash
# Check if container is running
docker ps | grep infraagent-postgres

# Start if stopped
docker start infraagent-postgres

# Check logs
docker logs infraagent-postgres
```

### Database migration errors

```bash
# Reset database (warning: drops all data)
docker exec infraagent-postgres psql -U infraagent -c "DROP DATABASE infraagent;"
docker exec infraagent-postgres psql -U infraagent -c "CREATE DATABASE infraagent;"
cd backend && uv run alembic upgrade head
```

### Knowledge wiki submodule empty

```bash
# Initialize submodule
git submodule update --init --recursive

# If the wiki repo URL has changed
git submodule sync
git submodule update --init --recursive
```

### Foundry project not appearing in AI Toolkit

1. Sign in to Azure in VS Code (Accounts icon in the sidebar)
2. Ensure your account has `Cognitive Services User` role on the Foundry resource
3. Refresh the AI Toolkit sidebar