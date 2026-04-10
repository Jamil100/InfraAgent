# Developer Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 20+ | Frontend runtime |
| **uv** | latest | Package manager (replaces pip/venv) |
| **Azure CLI** | latest | Authentication + subscription access |
| **Docker Desktop** | latest | Terraform MCP Server |
| **.NET SDK** | 9.0+ | Bicep MCP Server |
| **Git** | latest | Source control |
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

### 1. Clone the Repository

```bash
git clone https://github.com/<org>/terrabot.git
cd "Terraformers Anonymous"
```

### 2. Install Backend Dependencies

```bash
cd backend
uv sync
```

This creates a `.venv` automatically and installs all dependencies from `pyproject.toml`.

For development extras (pytest, ruff):

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
MODEL_DEPLOYMENT_NAME=gpt-4o

# Azure — get from az account show
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_TENANT_ID=<your-tenant-id>

# GitHub — create a fine-grained PAT with repo permissions
GITHUB_TOKEN=ghp_<your-token>
GITHUB_REPO_OWNER=<org-or-user>
GITHUB_REPO_NAME=terrabot
GITHUB_TARGET_BRANCH=main

# MCP Servers — leave blank to skip; set when running MCP servers locally
# MCP_BICEP_URL=http://localhost:5007/mcp
# MCP_TERRAFORM_URL=http://localhost:5008/mcp
# MCP_AZURE_URL=http://localhost:5009/mcp

# Deployment — leave blank to stop pipeline at PR; set to enable the deploy stage
# DEPLOY_RESOURCE_GROUP=rg-infraagent-dev
# DEPLOY_LOCATION=eastus
```

### 4. Authenticate with Azure

```bash
az login
az account set --subscription <your-subscription-id>
```

This enables `DefaultAzureCredential` used by the backend.

### 5. Run the Backend

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

Verify: `http://localhost:8000/health` should return `{"status": "ok", "version": "0.1.0"}`.

### 6. Set Up and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Verify: `http://localhost:3000` should open the InfraAgent chat interface.

The frontend expects the backend to be running at `http://localhost:8000`. To override, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## MCP Server Setup

MCP servers are configured in `.vscode/mcp.json` and used both by Copilot Chat (locally) and eventually by Foundry-hosted agents (remote HTTP).

### Bicep MCP Server

```bash
dotnet tool install -g Microsoft.BicepMcp
```

Start it (runs on port 5007 by default):

```bash
bicep-mcp
```

The `.vscode/mcp.json` connects to `http://localhost:5007/mcp`.

### Terraform MCP Server

Requires Docker Desktop running:

```bash
docker pull hashicorp/terraform-mcp-server:0.5.1
```

The server launches automatically via `.vscode/mcp.json` when Copilot invokes it.

### Azure MCP Server

```bash
uv tool install msmcp-azure
```

Or via the **Azure MCP** VS Code extension (installs automatically).

The server launches via the `msmcp-azure` command in `.vscode/mcp.json`.

## Connecting to AI Toolkit

1. Open the **AI Toolkit** sidebar in VS Code
2. Under **My Resources** → **Microsoft Foundry Resources**, click **Set Default Project**
3. Select (or create) your Foundry project
4. Verify connection: expand **Connected Resources** — you should see your model deployments

### Using Model Playground

1. AI Toolkit → **Model Playground**
2. Select a deployed model (e.g., `gpt-4o`)
3. Paste agent system prompts from `backend/src/agents/prompts/` to iterate on them
4. Test with sample infrastructure requests

### Using Agent Inspector

1. AI Toolkit → **Agent Inspector**
2. Connect to a running agent's thread to view conversation history
3. Useful for debugging agent JSON output parsing issues

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

### Docker not available for Terraform MCP

Ensure Docker Desktop is running. On Windows, check WSL2 backend is enabled.

### Foundry project not appearing in AI Toolkit

1. Sign in to Azure in VS Code (Accounts icon in the sidebar)
2. Ensure your account has `Cognitive Services User` role on the Foundry resource
3. Refresh the AI Toolkit sidebar
