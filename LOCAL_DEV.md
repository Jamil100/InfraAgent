# Local Development Setup Guide

Complete guide for getting InfraAgent running on your machine — from zero to a working backend + frontend with all credentials configured.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone & Install Dependencies](#2-clone--install-dependencies)
3. [Configure Credentials & Environment Variables](#3-configure-credentials--environment-variables)
   - [Azure AI Foundry — Project Endpoint](#azure-ai-foundry--project-endpoint)
   - [Azure Subscription & Tenant ID](#azure-subscription--tenant-id)
   - [GitHub Personal Access Token](#github-personal-access-token)
   - [MCP Servers (Optional)](#mcp-servers-optional)
   - [Deploy Stage (Optional)](#deploy-stage-optional)
   - [Full .env Reference](#full-env-reference)
4. [Authenticate with Azure CLI](#4-authenticate-with-azure-cli)
5. [Run the Backend](#5-run-the-backend)
6. [Run the Frontend](#6-run-the-frontend)
7. [Verify Everything Works](#7-verify-everything-works)
8. [MCP Server Setup (Optional)](#8-mcp-server-setup-optional)
9. [Troubleshooting](#9-troubleshooting)
10. [Useful Links](#10-useful-links)

---

## 1. Prerequisites

Install the following tools before proceeding. All are free.

| Tool | Min Version | Download |
|---|---|---|
| **Python** | 3.11+ | https://www.python.org/downloads/ |
| **uv** (Python package manager) | latest | https://docs.astral.sh/uv/getting-started/installation/ |
| **Node.js** | 20+ | https://nodejs.org/en/download |
| **Azure CLI** | latest | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| **Git** | latest | https://git-scm.com/downloads |

**Optional** (only needed if you want MCP tool grounding for agents — see [Section 8](#8-mcp-server-setup-optional)):

| Tool | Purpose | Download |
|---|---|---|
| **.NET SDK 9+** | Bicep MCP server | https://dotnet.microsoft.com/en-us/download |
| **Docker Desktop** | Terraform MCP server | https://www.docker.com/products/docker-desktop/ |

---

## 2. Clone & Install Dependencies

```bash
# Clone the repo
git clone https://github.com/Jamil100/InfraAgent.git
cd InfraAgent

# Install backend dependencies (creates .venv automatically)
cd backend
uv sync

# Install frontend dependencies
cd ../frontend
npm install
```

> **Windows note**: if `uv` is not found after install, restart your terminal or run
> `$env:PATH += ";$env:USERPROFILE\.local\bin"` in PowerShell.

---

## 3. Configure Credentials & Environment Variables

Copy the example env file to create your local `.env` at the **repo root**:

```bash
# From the repo root
cp .env.example .env        # macOS / Linux
copy .env.example .env      # Windows CMD
Copy-Item .env.example .env # Windows PowerShell
```

Open `.env` in your editor and fill in each value. The sections below explain exactly where to find each one.

---

### Azure AI Foundry — Project Endpoint

| Variable | Description |
|---|---|
| `PROJECT_ENDPOINT` | Your Foundry project's API endpoint |
| `MODEL_DEPLOYMENT_NAME` | Name or registry path of your deployed chat model |

**Where to find the Project Endpoint:**

1. Go to the [Azure AI Foundry portal](https://ai.azure.com) and sign in
2. Open your **project** (or create one: Home → **+ New project**)
3. In the left sidebar click **Overview**
4. Copy the **Project endpoint** — it looks like:
   ```
   https://my-hub.services.ai.azure.com/api/projects/my-project
   ```

**Where to find / create the model deployment:**

1. Inside your Foundry project, go to **My assets → Models + endpoints**
2. Click **+ Deploy model** → **Deploy base model** → search for `gpt-5.4-mini`
3. Accept defaults → **Deploy**
4. Use the full azureml registry path as your `MODEL_DEPLOYMENT_NAME` (see value below), or the short deployment name shown on the card

> **Role needed**: Your Azure account must have **Azure AI Developer** (or **Cognitive Services User**) on the Foundry resource.
> Assign it at: [portal.azure.com → your AI Services resource → Access control (IAM)](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/overview)

```env
PROJECT_ENDPOINT=https://<your-hub>.services.ai.azure.com/api/projects/<your-project>
MODEL_DEPLOYMENT_NAME=azureml://registries/azure-openai/models/gpt-5.4-mini/versions/2026-03-17
```

---

### Azure Subscription & Tenant ID

| Variable | Description |
|---|---|
| `AZURE_SUBSCRIPTION_ID` | The GUID of your Azure subscription |
| `AZURE_TENANT_ID` | The GUID of your Azure Active Directory tenant |

**Option A — Azure portal:**

1. Go to [portal.azure.com](https://portal.azure.com)
2. **Subscription ID**: search **Subscriptions** in the top bar → click your subscription → copy the **Subscription ID** on the Overview page
   Direct link: https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade
3. **Tenant ID**: search **Microsoft Entra ID** → click **Overview** → copy **Tenant ID**
   Direct link: https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/Overview

**Option B — Azure CLI (fastest):**

```bash
az login
az account show --query "{subscriptionId:id, tenantId:tenantId}" -o table
```

```env
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> These are used by the subscription discovery adapter (listing existing resource groups and VNets) and by the deploy adapter if enabled. The backend uses `DefaultAzureCredential` — no client secret is needed, just `az login` (see [Section 4](#4-authenticate-with-azure-cli)).

---

### GitHub Personal Access Token

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | PAT with repo read/write permissions |
| `GITHUB_REPO_OWNER` | GitHub org or username that owns the repo |
| `GITHUB_REPO_NAME` | Repository name (without `.git`) |
| `GITHUB_TARGET_BRANCH` | Base branch that PRs will target |

InfraAgent creates branches, commits generated IaC files, and opens pull requests using the GitHub REST API.

**Create a fine-grained token (recommended):**

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token → Fine-grained personal access token**
3. Fill in:
   - **Token name**: `infraagent-local`
   - **Expiration**: 90 days (or your org's policy)
   - **Resource owner**: your org or account
   - **Repository access**: **Only select repositories** → choose your target repo
4. Under **Repository permissions**, set:
   | Permission | Level |
   |---|---|
   | Contents | **Read and write** |
   | Pull requests | **Read and write** |
   | Metadata | Read-only (auto-selected) |
5. Click **Generate token** — copy the value immediately (shown only once)

> **Classic token alternative**: [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)** → check the `repo` scope.
> Docs: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

```env
GITHUB_TOKEN=github_pat_xxxxxxxxxxxx
GITHUB_REPO_OWNER=Jamil100
GITHUB_REPO_NAME=InfraAgent
GITHUB_TARGET_BRANCH=main
```

---

### MCP Servers (Optional)

MCP servers give agents real-time access to provider schemas, AVM documentation, and live Azure resource data. Leave these blank to skip — agents work without them.

```env
MCP_BICEP_URL=http://localhost:5007/mcp
MCP_TERRAFORM_URL=http://localhost:8080/mcp
MCP_AZURE_URL=http://localhost:5009/mcp
```

See [Section 8](#8-mcp-server-setup-optional) for how to start each server.

---

### Deploy Stage (Optional)

By default the pipeline stops after opening a PR. Set these to enable actual deployment (`az deployment group create` / `terraform apply`):

```env
DEPLOY_RESOURCE_GROUP=rg-infraagent-dev
DEPLOY_LOCATION=eastus
```

The resource group must already exist. Create it with:

```bash
az group create --name rg-infraagent-dev --location eastus
```

Your CLI identity must have **Contributor** on this resource group. Assign it at:
[portal.azure.com → Resource group → Access control (IAM) → Add role assignment](https://portal.azure.com/#view/Microsoft_Azure_Resources/ResourceGroupMenuBlade/~/overview)

---

### Full `.env` Reference

```env
# ── Azure AI Foundry ──────────────────────────────────────────────────────────
PROJECT_ENDPOINT=https://<hub>.services.ai.azure.com/api/projects/<project>
MODEL_DEPLOYMENT_NAME=azureml://registries/azure-openai/models/gpt-5.4-mini/versions/2026-03-17

# ── Azure ─────────────────────────────────────────────────────────────────────
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN=github_pat_xxxxxxxxxxxx
GITHUB_REPO_OWNER=Jamil100
GITHUB_REPO_NAME=InfraAgent
GITHUB_TARGET_BRANCH=main

# ── MCP Servers (optional — leave blank to disable) ───────────────────────────
MCP_BICEP_URL=
MCP_TERRAFORM_URL=
MCP_AZURE_URL=

# ── Deploy Stage (optional — leave blank to stop pipeline at PR) ──────────────
DEPLOY_RESOURCE_GROUP=
DEPLOY_LOCATION=eastus

# ── App ───────────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## 4. Authenticate with Azure CLI

The backend uses `DefaultAzureCredential` from `azure-identity`. For local dev this picks up your Azure CLI session automatically — no service principal or client secret needed.

```bash
az login
```

A browser window opens. Sign in with the account that has access to your Foundry project and Azure subscription.

If you have multiple subscriptions, pin the one you want:

```bash
az account set --subscription <your-subscription-id>

# Confirm
az account show
```

**Required role assignments summary:**

| Role | Where | Why |
|---|---|---|
| Azure AI Developer (or Cognitive Services User) | AI Foundry resource | Call agents and models |
| Reader | Subscription | List resource groups and VNets |
| Contributor | Target resource group | Deploy IaC (only if `DEPLOY_RESOURCE_GROUP` is set) |

> If you created the Foundry project yourself you likely already have Owner, which covers all of the above.

---

## 5. Run the Backend

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

`--reload` watches for file changes and restarts automatically. Expected output:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verify:**

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

**Interactive API docs** (auto-generated by FastAPI):
http://localhost:8000/docs

---

## 6. Run the Frontend

Open a **second terminal**:

```bash
cd frontend
npm run dev
```

Runs on **http://localhost:3000** with Turbopack hot-reload.

The frontend talks to the backend at `http://localhost:8000` by default. To override, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Open http://localhost:3000 — you should see the InfraAgent chat interface.

---

## 7. Verify Everything Works

Run through this checklist once both processes are running:

| # | Check | How |
|---|---|---|
| 1 | Backend health | `curl http://localhost:8000/health` → `{"status":"ok"}` |
| 2 | API docs | Open http://localhost:8000/docs — all routes visible |
| 3 | Frontend loads | Open http://localhost:3000 — chat UI renders |
| 4 | Chat works | Type a message → Consulting agent replies |
| 5 | Requirements ready | After a few turns `requirements_ready: true` — **Launch Pipeline** button activates |
| 6 | Pipeline starts | Click **Launch Pipeline** → pipeline monitor page opens, stages begin advancing |
| 7 | H1 gate | Pipeline pauses at **H1: Code Review** — approve in the UI to continue |
| 8 | PR created | After H1 approval a PR appears in your GitHub repo |
| 9 | H2 gate (if deploy set) | Pipeline pauses at **H2: Plan Review** — approve to trigger deployment |

---

## 8. MCP Server Setup (Optional)

Skip this section if you left all `MCP_*_URL` variables blank.

### Bicep MCP Server

Gives CodeGen and Standards agents real-time access to AVM module schemas and Bicep documentation.

Requires .NET SDK 9+.

```bash
# Install globally
dotnet tool install -g Microsoft.BicepMcp

# Run (starts on port 5007)
bicep-mcp
```

```env
MCP_BICEP_URL=http://localhost:5007/mcp
```

More info: https://github.com/Azure/bicep-mcp

---

### Terraform MCP Server

Gives CodeGen and Security agents access to Terraform provider schemas.

Requires Docker Desktop running.

```bash
docker pull hashicorp/terraform-mcp-server:latest
docker run -p 8080:8080 hashicorp/terraform-mcp-server:latest
```

```env
MCP_TERRAFORM_URL=http://localhost:8080/mcp
```

More info: https://github.com/hashicorp/terraform-mcp-server

---

### Azure MCP Server

Gives the Consulting agent live visibility into your Azure subscription.

```bash
# Install
uv tool install msmcp-azure

# Run (starts on port 5009)
msmcp-azure
```

Or install the **Azure MCP** VS Code extension — it starts and manages the server automatically.

```env
MCP_AZURE_URL=http://localhost:5009/mcp
```

More info: https://github.com/Azure/azure-mcp

---

## 9. Troubleshooting

### `uv: command not found`

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installing.

---

### `DefaultAzureCredential` fails / 401 from Azure

```bash
az login --tenant <your-tenant-id>
az account set --subscription <your-subscription-id>
az account show
```

Check you haven't accidentally set `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` env vars in your shell — those override CLI credentials.

---

### Foundry 404 / `PROJECT_ENDPOINT` errors

- Verify the format: `https://<hub>.services.ai.azure.com/api/projects/<project>`
  — the hub name and project name are **separate** path segments
- Copy the value directly from [ai.azure.com](https://ai.azure.com) → your project → **Overview**
- Ensure your account has **Azure AI Developer** on the Foundry resource:
  [portal.azure.com → your AI Services resource → Access control (IAM)](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/overview)

---

### GitHub 422 on PR creation

Ensure `GITHUB_TOKEN` has **Contents: Read and write** on the target repo. Verify at:
https://github.com/settings/tokens → click your token → check Repository permissions.

---

### Frontend `ECONNREFUSED` / cannot reach backend

- Ensure the backend is running (`uv run uvicorn main:app --reload --port 8000`)
- Check `CORS_ORIGINS=http://localhost:3000` is set in `.env`
- If you changed the backend port, set `NEXT_PUBLIC_API_URL=http://localhost:<port>` in `frontend/.env.local`

---

### `npm run dev` fails — cannot find module

```bash
cd frontend
npm install
npm run dev
```

---

### Port already in use

```powershell
# Windows PowerShell — find and kill process on a port
$port = 8000   # or 3000
$pid = (netstat -ano | Select-String ":$port\s" | Select-Object -First 1) -replace '.*\s(\d+)$','$1'
Stop-Process -Id $pid -Force
```

---

## 10. Useful Links

| Resource | URL |
|---|---|
| Azure AI Foundry portal | https://ai.azure.com |
| Azure portal | https://portal.azure.com |
| Azure subscriptions list | https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade |
| Microsoft Entra ID (Tenant ID) | https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/Overview |
| AI Foundry role assignments | https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/overview |
| GitHub token settings | https://github.com/settings/tokens |
| GitHub PAT docs (fine-grained) | https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token |
| Azure CLI install | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| uv install | https://docs.astral.sh/uv/getting-started/installation/ |
| Node.js download | https://nodejs.org/en/download |
| .NET SDK download | https://dotnet.microsoft.com/en-us/download |
| Docker Desktop | https://www.docker.com/products/docker-desktop/ |
| Bicep MCP | https://github.com/Azure/bicep-mcp |
| Terraform MCP Server | https://github.com/hashicorp/terraform-mcp-server |
| Azure MCP | https://github.com/Azure/azure-mcp |
