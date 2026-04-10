# Deployment & CI/CD Guide

## Deployment Stages

```
Local Dev → Docker Container → Azure Container Registry → Foundry Hosted Agent
                                                        → Azure Container Apps (MCP servers)
```

## Local Development

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

Uses `DefaultAzureCredential` — authenticate via `az login`.

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

## Azure Container Registry

```bash
# Create ACR (one-time)
az acr create --name infraagentacr --resource-group <rg> --sku Basic

# Build & push
az acr login --name infraagentacr
docker tag infraagent-backend:dev infraagentacr.azurecr.io/infraagent-backend:latest
docker push infraagentacr.azurecr.io/infraagent-backend:latest
```

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

# Deploy agent container
# (follow microsoft-foundry skill patterns for Docker → ACR → Foundry)
```

### Requirements for Foundry Hosted Agents

- **Linux AMD64** containers only
- Max **5 replicas**
- MCP servers must be **remote HTTP** (not localhost/stdio)
- **100-second timeout** for MCP tool calls
- Container must expose an HTTP server (agent-as-server pattern)
- Billing: pay-per-use (started April 1, 2026)

## MCP Server Remote Deployment

For Foundry-hosted agents to access MCP servers, deploy them as Azure Container Apps:

### Bicep MCP

```bash
# Container image with Bicep MCP
az containerapp create \
  --name bicep-mcp \
  --resource-group <rg> \
  --environment <env> \
  --image <acr>/bicep-mcp:latest \
  --target-port 5007 \
  --ingress external
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
```

## GitHub Actions CI/CD

### Pipeline Overview

```
push/PR → lint → test → build → deploy (main only)
```

### Workflow File

Create `.github/workflows/ci.yml`:

```yaml
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

      - name: Test
        working-directory: backend
        run: uv run pytest -v --tb=short

  build:
    needs: lint-and-test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push to ACR
        working-directory: backend
        run: |
          az acr login --name infraagentacr
          docker build -t infraagentacr.azurecr.io/infraagent-backend:${{ github.sha }} .
          docker push infraagentacr.azurecr.io/infraagent-backend:${{ github.sha }}
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON for `az login` |
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |

## Environment Promotion

| Environment | Branch | Trigger | Foundry Project |
|---|---|---|---|
| **dev** | feature branches | PR (lint + test only) | Dev sandbox |
| **staging** | main | Push to main (build + deploy) | Staging project |
| **prod** | release tags | Manual approval | Production project |
