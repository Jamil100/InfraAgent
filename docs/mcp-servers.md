# MCP Server Reference

InfraAgent uses four MCP (Model Context Protocol) servers to ground AI agents with real-time data from IaC ecosystems, Azure, and GitHub operations.

## Server Overview

| MCP Server | Source | Tools | Auth Type | Used By |
|---|---|---|---|---|
| **Bicep MCP** | Azure/bicep (built-in) | 10 (schemas, AVM, diagnostics, best practices) | API key | CodeGen, Standards, Security |
| **Terraform MCP** | hashicorp/terraform-mcp-server | 35 (registry, modules, policies, workspaces) | API key | CodeGen, Security |
| **Azure MCP** | microsoft/mcp (GA 1.0) | 43+ (resource mgmt, Key Vault, AKS, networking) | Entra ID | Consulting, CodeGen, Deploy |
| **GitHub MCP** | github/github-mcp-server | PR, branch, workflow tools | API key (PAT) | PR Workflow, Deploy, Standards, Template Curation |

## Agent-to-MCP Mapping

| Agent | MCP Servers | Purpose |
|---|---|---|
| Orchestrator | None | Uses agent-to-agent handoff |
| Consulting | Azure MCP | Subscription discovery, resource queries, quota checks |
| CodeGen | Terraform MCP, Bicep MCP, Azure MCP | Live provider schemas, AVM module lookup, resource validation |
| Standards | GitHub MCP | Policy repo access for standards enforcement |
| Security | None | Uses function tools (tfsec, Checkov via Azure Functions) |
| PR Workflow | GitHub MCP | Branch creation, file commits, PR creation, CI/CD monitoring |
| Deploy | GitHub MCP, Azure MCP | Workflow triggering, plan/apply monitoring, deployment operations |
| Template Curation | GitHub MCP | PR creation to knowledge wiki repo |

## Configuration

### Environment Variables

```env
# Set these to enable MCP tools for agents (leave blank to disable)
MCP_BICEP_URL=http://localhost:5007/mcp
MCP_TERRAFORM_URL=http://localhost:5008/mcp
MCP_AZURE_URL=http://localhost:5009/mcp
MCP_GITHUB_URL=http://localhost:5010/mcp
```

### VS Code / Copilot Configuration

MCP servers are configured in `.vscode/mcp.json` for local VS Code / Copilot use:

```json
{
  "servers": {
    "bicep":     { "type": "http",  "url": "http://localhost:5007/mcp" },
    "terraform": { "type": "stdio", "command": "docker", "args": ["run", "-i", "--rm", "hashicorp/terraform-mcp-server:0.5.1", "-toolsets=registry,terraform"] },
    "azure":     { "type": "stdio", "command": "msmcp-azure" },
    "github":    { "type": "stdio", "command": "docker", "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"] }
  }
}
```

---

## Bicep MCP Server

**Source**: Azure/bicep repository (Microsoft)
**Version**: Ships with Bicep CLI v0.42.1+
**Transport**: HTTP (`http://localhost:5007/mcp`)
**Auth**: API key

### Installation

```bash
dotnet tool install -g Microsoft.BicepMcp
bicep-mcp  # starts on port 5007
```

### Key Tools

| Tool | Description | Use in InfraAgent |
|---|---|---|
| `bicep/getSchema` | Get resource type schema with properties and constraints | CodeGen validates resource definitions |
| `bicep/build` | Compile .bicep to ARM JSON — catches syntax and type errors | IaC Validation Pipeline |
| `bicep/format` | Auto-format Bicep files | IaC Validation Pipeline (pre-review cleanup) |
| `bicep/lint` | Run linter rules (security, best practice) | IaC Validation Pipeline + Standards checks |
| `bicep/getModules` | List available AVM modules from registry | CodeGen uses AVM-first strategy |
| `bicep/bestPractices` | Get Bicep best practices guidance | CodeGen quality improvement |
| `bicep/diagnostics` | Get diagnostics for Bicep files | Standards + Security validation |

### AVM Module Reference

Azure Verified Modules are referenced as:
```bicep
module vnet 'br/public:avm/res/network/virtual-network:0.5.1' = {
  name: 'vnet-deploy'
  params: { ... }
}
```

Pattern: `br/public:avm/res/{provider}/{resource}:{version}`

Resolve latest versions via MCR endpoint: `https://mcr.microsoft.com/v2/bicep/avm/res/{service}/{resource}/tags/list`

---

## Terraform MCP Server

**Source**: [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server)
**Version**: 0.5.1
**Transport**: stdio (Docker) or StreamableHTTP
**Auth**: API key (for remote deployment); optional HCP Terraform token for private modules

### Installation

```bash
docker pull hashicorp/terraform-mcp-server:0.5.1
```

Launches automatically via `.vscode/mcp.json` when invoked.

### Toolsets

| Toolset | Tools | Use in InfraAgent |
|---|---|---|
| `registry` (default) | `providerLookup`, `resourceUsage`, `moduleSearch`, `moduleDetails`, `dataSourceLookup` | CodeGen looks up provider schemas and AVM Terraform modules |
| `terraform` | `plan`, `validate`, `apply`, `init` | IaC Validation Pipeline + Deploy Agent |
| `registry-private` | Same as registry but for private modules | Future: organization module catalog |

### Key Tools for AVM-First Strategy

| Tool | Description |
|---|---|
| `moduleSearch` | Search for AVM modules with query `avm-res-` |
| `moduleDetails` | Get module inputs, outputs, and version info |
| `providerLookup` | Look up provider resource schemas |
| `resourceUsage` | Get resource usage examples from registry |

Resolve latest AVM versions via Terraform Registry API: `https://registry.terraform.io/v1/modules/Azure/{module}/azurerm/versions`

### Configuration Options

```json
"args": [
  "run", "-i", "--rm",
  "-e", "TF_TOKEN_app_terraform_io=<token>",
  "hashicorp/terraform-mcp-server:0.5.1",
  "-toolsets=registry,terraform"
]
```

---

## Azure MCP Server

**Source**: [microsoft/mcp](https://github.com/microsoft/mcp) (GA 1.0)
**Note**: Previously at `Azure/azure-mcp` — archived February 2026, moved to `microsoft/mcp`
**Transport**: stdio (local) or container (remote)
**Auth**: Entra ID (managed identity or `DefaultAzureCredential`)

### Installation

```bash
uv tool install msmcp-azure
# or
pip install msmcp-azure
```

Also available as a VS Code extension.

### Service Areas (43+)

| Category | Services | Use in InfraAgent |
|---|---|---|
| **Resource Management** | Subscriptions, Resource Groups, Deployments | Subscription discovery for Consulting Agent |
| **Compute** | VMs, App Service, Container Apps, AKS | CodeGen resource validation |
| **Networking** | VNets, NSGs, Load Balancers, DNS | CodeGen + subscription discovery (CIDR conflict avoidance) |
| **Storage** | Storage Accounts, Blob, File, Queue, Table | CodeGen |
| **Databases** | SQL, Cosmos DB, PostgreSQL | CodeGen |
| **Security** | Key Vault, Defender, Entra ID | Security Agent context |
| **AI** | Foundry, OpenAI, Cognitive Services | Agent management |
| **Architecture** | Cloud Architect, WAF guidance | Consulting Agent best practices |

### Key Tools for Subscription Discovery

| Tool | Description | Used For |
|---|---|---|
| `azure/listSubscriptions` | Discover user's Azure subscriptions | Initial subscription selection |
| `azure/listResourceGroups` | List existing resource groups in a subscription | Consulting Agent context |
| `azure/listResources` | List resources in a resource group | Existing infrastructure inventory |
| `azure/getVNetTopology` | Get VNet/subnet address spaces | CIDR conflict avoidance |
| `azure/checkQuotas` | Check compute quotas in a region | SKU/quota availability |
| `azure/cloudArchitect` | Get architecture recommendations (WAF-aligned) | Consulting Agent pattern recommendations |
| `azure/azureTerraformBestPractices` | Terraform-specific Azure guidance | CodeGen quality improvement |

---

## GitHub MCP Server

**Source**: [github/github-mcp-server](https://github.com/github/github-mcp-server)
**Transport**: stdio (Docker) or HTTP
**Auth**: API key (GitHub Personal Access Token with `repo` and `workflow` scopes)

### Installation

```bash
docker pull ghcr.io/github/github-mcp-server
```

Or run via `.vscode/mcp.json`:

```json
{
  "github": {
    "type": "stdio",
    "command": "docker",
    "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "<pat>"
    }
  }
}
```

### Key Tools

| Tool | Description | Agent Consumer |
|---|---|---|
| `create_branch` | Create a feature branch from base | PR Workflow Agent |
| `commit_files` | Commit files atomically to a branch | PR Workflow Agent |
| `create_pull_request` | Open a PR with title, body, head/base branches | PR Workflow Agent |
| `list_workflows` | List GitHub Actions workflows in a repo | Deploy Agent |
| `trigger_workflow` | Trigger a workflow dispatch (plan/apply) | Deploy Agent |
| `get_workflow_run` | Get workflow run status and output | Deploy Agent |
| `get_file_contents` | Read file from repo | Standards Agent (policy files) |
| `search_repositories` | Search repos | Template Curation Agent |

### Required PAT Scopes

- `repo` — Full control of private repositories (branch, commit, PR)
- `workflow` — Trigger and monitor GitHub Actions workflows

---

## Custom MCP Servers (tfsec, Checkov)

The Security Agent uses **function tools** (not MCP) backed by Azure Functions. These expose `run_tfsec` and `run_checkov` as HTTP-callable functions.

```bash
# Deploy security scanning functions
az functionapp create \
  --name infraagent-security-tools \
  --resource-group <rg> \
  --runtime python \
  --functions-version 4 \
  --os-type Linux

# Function definitions:
# run_tfsec(files: GeneratedFile[]) → SecurityFinding[]
# run_checkov(files: GeneratedFile[]) → SecurityFinding[]
```

If you need to expose these as MCP servers (e.g., for use by Foundry-hosted agents), use the Azure Functions MCP binding extensions to wrap them as MCP tools.

---

## Foundry Remote Deployment

For Foundry-hosted agents, MCP servers **must be remote HTTP** (not localhost/stdio).

| Server | Remote Strategy | Auth |
|---|---|---|
| **Bicep MCP** | Azure Container App (port 5007) | API key |
| **Terraform MCP** | Azure Container App (StreamableHTTP) | API key |
| **Azure MCP** | Azure Container App or `pip install` in agent container | Entra ID (managed identity) |
| **GitHub MCP** | Azure Container App (HTTP) | API key (PAT from Key Vault) |
| **tfsec/Checkov** | Azure Functions | Function key |

**Constraint**: Foundry imposes a **100-second MCP timeout** — long-running operations (plan/apply) may need to be handled outside MCP via GitHub Actions CI/CD.

---

## Adding a New MCP Server

1. Add the server config to `.vscode/mcp.json` (local development)
2. Add the `MCP_<NAME>_URL` environment variable to `.env.example`
3. Add the agent-to-server mapping in `backend/src/agents/factory.py` (`_AGENT_MCP_SERVERS`)
4. Document the server in this file with tools, auth type, and agent consumers
5. If used by Foundry-hosted agents, plan the remote HTTP deployment (Azure Container App or Functions)
6. Reference the server's tools in the relevant agent's system prompt
7. Update [setup.md](setup.md) with installation instructions