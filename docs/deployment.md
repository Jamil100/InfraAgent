# Deployment & CI/CD Guide

## Deployment Architecture

```mermaid
graph LR
    Local[Local Dev] --> Docker[Docker Container]
    Docker --> ACR[Azure Container Registry]
    ACR --> AppService[Azure App Service\nBackend]
    ACR --> SWA[Static Web App\nFrontend]
    ACR --> ACA[Azure Container Apps\nMCP Servers]
    ACR --> Foundry[Foundry Hosted Agents]
    Bicep[infra/*.bicep] -->|az deployment| Azure[Azure Resources]
```

## Azure Infrastructure (Self-Deployment)

InfraAgent's own infrastructure is deployed via **Bicep** — dogfooding the platform. The Bicep modules are in `infra/`.

### Required Azure Resources

| Resource | SKU / Tier | Purpose |
|---|---|---|
| Azure AI Foundry Resource | AIServices (S0) | Agent runtime, model deployments |
| Azure AI Foundry Project | — | Agent workspace with ModelRouter |
| Azure OpenAI Deployments | GPT-4o (GlobalStandard), GPT-4o-mini (GlobalStandard) | Agent model inference (via ModelRouter) |
| Azure App Service | B2 (hackathon) | Python backend hosting |
| Azure Static Web Apps | Free | React frontend hosting |
| Azure PostgreSQL Flexible Server | Burstable B1ms | Conversations, deployments, settings |
| Azure Key Vault | Standard | Secrets (GitHub PAT, API tokens) |
| Azure AI Search | Basic | Policy RAG for Standards Agent, template search for catalog |
| Azure Functions | Consumption | MCP server hosting (tfsec, Checkov) |
| Azure App Insights + Log Analytics | — | Observability (traces, metrics, logs) |
| Azure Storage Account | Standard LRS | Function app storage, generated artifacts |
| Azure Container Apps Environment | — | Remote MCP server hosting |

### Estimated Cost (Hackathon — 3 weeks)

| Resource | Monthly Estimate |
|---|---|
| AI Foundry + GPT-4o (pay-per-token) | ~$50–100 (demo usage) |
| App Service B2 | ~$55 |
| PostgreSQL Flexible B1ms | ~$25 |
| AI Search Basic | ~$75 |
| Everything else (Functions, Storage, SWA, App Insights) | ~$20 |
| **Total** | **~$225–275/month** |

### Deploy InfraAgent Infrastructure

```bash
# Deploy all Azure resources via Bicep
az deployment group create \
  --resource-group rg-infraagent-dev \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam

# Bicep modules in infra/modules/:
# foundry.bicep      — AI Foundry resource + project
# postgres.bicep     — PostgreSQL Flexible Server
# appService.bicep   — App Service for backend
# staticWebApp.bicep — Static Web App for frontend
# keyVault.bicep     — Key Vault for secrets
# aiSearch.bicep     — AI Search for Policy RAG
# functionApp.bicep  — Azure Functions for MCP hosting
# monitoring.bicep   — App Insights + Log Analytics
```

---

## Local Development

```bash
# Terminal 1 — Backend
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

- Backend: `http://localhost:8000` (uses `DefaultAzureCredential` — authenticate via `az login`)
- Frontend: `http://localhost:3000`

### Git Submodule Setup (Knowledge Wiki)

The knowledge wiki is a separate repo consumed via git submodule. After cloning:

```bash
git submodule update --init --recursive
```

This populates `knowledge-wiki/` with templates, skills, and standards.

---

## Environment Variables

Create `.env` from `.env.example` and configure all variables:

```env
# Azure AI Foundry
PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<project-id>
MODEL_DEPLOYMENT_NAME=<model-router-or-deployment-name>

# Azure Subscription
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_TENANT_ID=<tenant-id>

# GitHub
GITHUB_TOKEN=ghp_<fine-grained-pat>
GITHUB_REPO_OWNER=<org-or-user>
GITHUB_REPO_NAME=<repo>
GITHUB_TARGET_BRANCH=main

# MCP Servers (leave blank to disable)
MCP_BICEP_URL=http://localhost:5007/mcp
MCP_TERRAFORM_URL=http://localhost:5008/mcp
MCP_AZURE_URL=http://localhost:5009/mcp
MCP_GITHUB_URL=http://localhost:5010/mcp

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/infraagent

# Key Vault
KEY_VAULT_URI=https://<vault-name>.vault.azure.net/

# AI Search (Policy RAG + template search)
AI_SEARCH_ENDPOINT=https://<search-name>.search.windows.net
AI_SEARCH_INDEX=standards-policies

# Deployment (leave blank to stop pipeline at PR)
DEPLOY_RESOURCE_GROUP=rg-infraagent-dev
DEPLOY_LOCATION=eastus

# CORS
CORS_ORIGINS=http://localhost:3000
```

---

## Database Setup

InfraAgent uses Azure PostgreSQL Flexible Server for conversations, deployments, and settings.

### Local Development

```bash
# Start PostgreSQL locally (Docker)
docker run -d --name infraagent-postgres \
  -e POSTGRES_USER=infraagent \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=infraagent \
  -p 5432:5432 \
  postgres:16

# Set DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://infraagent:devpassword@localhost:5432/infraagent
```

### Run Migrations

```bash
cd backend
uv run alembic upgrade head
```

The database schema includes tables for: `conversations`, `messages`, `deployments`, `generated_files`, `settings`, and `audit_log`. See the Tech Spec Section 9 for full schema.

---

## Docker Containerization

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY main.py .
COPY src/ src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build & Test Locally

```bash
cd backend
docker build -t infraagent-backend:dev .
docker run -p 8000:8000 --env-file ../.env infraagent-backend:dev
```

---

## Azure Container Registry

```bash
# Create ACR (one-time)
az acr create --name infraagentacr --resource-group <rg> --sku Basic

# Build & push
az acr login --name infraagentacr
docker tag infraagent-backend:dev infraagentacr.azurecr.io/infraagent-backend:latest
docker push infraagentacr.azurecr.io/infraagent-backend:latest
```

---

## Foundry Hosted Agent Deployment

Deploy agents to Azure AI Foundry Agent Service using the AI Toolkit:

### Via VS Code

1. Open Command Palette (`Ctrl+Shift+P`)
2. Run **Microsoft Foundry: Deploy Hosted Agent**
3. Select your Foundry project
4. Point to the Dockerfile
5. AI Toolkit builds → pushes to ACR → deploys to Foundry

### Via SDK

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint="<project-endpoint>",
    credential=DefaultAzureCredential(),
)

# Register agents with ModelRouter task profiles
# See backend/src/infrastructure/agents/registry.py
```

### Requirements for Foundry Hosted Agents

- **Linux AMD64** containers only
- Max **5 replicas**
- MCP servers must be **remote HTTP** (not localhost/stdio)
- **100-second timeout** for MCP tool calls
- Container must expose an HTTP server (agent-as-server pattern)
- Billing: pay-per-use (started April 1, 2026)

---

## MCP Server Remote Deployment

For Foundry-hosted agents to access MCP servers, deploy them as Azure Container Apps with appropriate authentication.

### Bicep MCP

```bash
az containerapp create \
  --name bicep-mcp \
  --resource-group <rg> \
  --environment <env> \
  --image <acr>/bicep-mcp:latest \
  --target-port 5007 \
  --ingress external
# Auth: API key (set via container app secrets)
```

### Terraform MCP

```bash
az containerapp create \
  --name terraform-mcp \
  --resource-group <rg> \
  --environment <env> \
  --image hashicorp/terraform-mcp-server:0.5.1 \
  --target-port 8080 \
  --ingress external \
  --args "-transport=http"
# Auth: API key
```

### Azure MCP

```bash
az containerapp create \
  --name azure-mcp \
  --resource-group <rg> \
  --environment <env> \
  --image <acr>/azure-mcp:latest \
  --target-port 8080 \
  --ingress external
# Auth: Entra ID (managed identity)
```

### GitHub MCP

```bash
az containerapp create \
  --name github-mcp \
  --resource-group <rg> \
  --environment <env> \
  --image <acr>/github-mcp:latest \
  --target-port 8080 \
  --ingress external
# Auth: API key (GitHub PAT from Key Vault)
```

### Custom MCP Servers (tfsec, Checkov)

Custom MCP servers for security scanning are hosted on Azure Functions using MCP binding extensions:

```bash
az functionapp create \
  --name infraagent-security-mcp \
  --resource-group <rg> \
  --runtime python \
  --functions-version 4 \
  --os-type Linux
# Exposes run_tfsec and run_checkov as function tools
```

---

## GitHub Actions CI/CD

### Pipeline Overview

```mermaid
graph LR
    Trigger([push / PR]) --> Lint[Lint + Format]
    Lint --> Test[Unit + Integration Tests]
    Test --> Build[Docker Build]
    Build -->|main branch only| Deploy[Deploy to Azure]
    Build -->|main branch only| Submodule[Validate Wiki Submodule]
```

### Workflow File

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive  # Knowledge wiki submodule

      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true

      - name: Install dependencies
        working-directory: backend
        run: uv sync --extra dev

      - name: Lint
        working-directory: backend
        run: uv run ruff check .

      - name: Format check
        working-directory: backend
        run: uv run ruff format --check .

      - name: Type check
        working-directory: backend
        run: uv run mypy src/

      - name: Test
        working-directory: backend
        run: uv run pytest -v --tb=short --cov=src --cov-report=xml

  build:
    needs: lint-and-test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push to ACR
        working-directory: backend
        run: |
          az acr login --name infraagentacr
          docker build -t infraagentacr.azurecr.io/infraagent-backend:${{ github.sha }} .
          docker push infraagentacr.azurecr.io/infraagent-backend:${{ github.sha }}

  deploy-infra:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Deploy InfraAgent infrastructure
        run: |
          az deployment group create \
            --resource-group rg-infraagent-dev \
            --template-file infra/main.bicep \
            --parameters infra/parameters/dev.bicepparam
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON for `az login` |
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |
| `ARM_SUBSCRIPTION_ID` | Target Azure subscription (for generated IaC deploys) |
| `ARM_TENANT_ID` | Azure tenant ID |
| `ARM_CLIENT_ID` | Service principal client ID |
| `ARM_CLIENT_SECRET` | Service principal secret |

---

## Environment Promotion

| Environment | Branch | Trigger | Foundry Project | Database |
|---|---|---|---|---|
| **dev** | feature branches | PR (lint + test only) | Dev sandbox | Local PostgreSQL |
| **staging** | main | Push to main (build + deploy) | Staging project | Azure PostgreSQL (staging) |
| **prod** | release tags | Manual approval | Production project | Azure PostgreSQL (prod) |

---

## Key Vault Setup

All secrets are stored in Azure Key Vault — never in code, environment variables, or database.

| Secret | Key Vault Name | Purpose |
|---|---|---|
| GitHub PAT | `github-pat` | PR creation, CI/CD triggering |
| Azure OpenAI API Key | `aoai-api-key` | Foundry inference (Managed Identity preferred) |
| Foundry connection string | `foundry-connection` | Agent Service access |
| PostgreSQL connection | `postgres-connection` | Database access (Managed Identity preferred) |
| MCP API keys | `mcp-bicep-key`, `mcp-terraform-key`, `mcp-github-key` | MCP server authentication |

```bash
# Create Key Vault
az keyvault create \
  --name kv-infraagent-dev \
  --resource-group <rg> \
  --enable-rbac-authorization true \
  --enable-purge-protection true

# Store a secret
az keyvault secret set \
  --vault-name kv-infraagent-dev \
  --name github-pat \
  --value "ghp_..."
```

---

## AI Search Setup

Azure AI Search provides Policy RAG for the Standards Agent and keyword search for the Self-Service Catalog.

```bash
# Create AI Search resource
az search service create \
  --name infraagent-search \
  --resource-group <rg> \
  --sku basic

# Index standards policies from knowledge-wiki/standards/
# Index template metadata from knowledge-wiki/templates/*/metadata.yaml
```

Indexing is configured via the backend at startup or via a CI pipeline that runs when the knowledge wiki submodule is updated.