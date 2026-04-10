# MCP Server Reference

InfraAgent uses three MCP (Model Context Protocol) servers to ground AI agents with real-time data from IaC ecosystems and Azure.

## Configuration

All MCP servers are configured in `.vscode/mcp.json` for local VS Code / Copilot use:

```json
{
  "servers": {
    "bicep":     { "type": "http",  "url": "http://localhost:5007/mcp" },
    "terraform": { "type": "stdio", "command": "docker", "args": ["run", "-i", "--rm", "hashicorp/terraform-mcp-server:0.5.1", "-toolsets=registry,terraform"] },
    "azure":     { "type": "stdio", "command": "msmcp-azure" }
  }
}
```

## Bicep MCP Server

**Source**: Azure/bicep repository (Microsoft)
**Version**: Ships with Bicep CLI v0.42.1+
**Transport**: HTTP (`http://localhost:5007/mcp`)

### Installation

```bash
dotnet tool install -g Microsoft.BicepMcp
bicep-mcp  # starts on port 5007
```

### Key Tools

| Tool | Description | Use in InfraAgent |
|---|---|---|
| `bicep/getSchema` | Get resource type schema with properties and constraints | CodeGen validates resource definitions |
| `bicep/build` | Compile .bicep to ARM JSON — catches syntax and type errors | Deterministic validation pipeline |
| `bicep/format` | Auto-format Bicep files | Pre-review cleanup |
| `bicep/lint` | Run linter rules (security, best practice) | Standards + Security checks |
| `bicep/getModules` | List available AVM modules from registry | CodeGen uses AVM-first strategy |

### AVM Module Reference

Azure Verified Modules are referenced as:
```bicep
module vnet 'br/public:avm/res/network/virtual-network:0.5.1' = {
  name: 'vnet-deploy'
  params: { ... }
}
```

Pattern: `br/public:avm/res/{provider}/{resource}:{version}`

## Terraform MCP Server

**Source**: [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server)
**Version**: 0.5.1
**Transport**: stdio (Docker) or StreamableHTTP

### Installation

```bash
docker pull hashicorp/terraform-mcp-server:0.5.1
```

Launches automatically via `.vscode/mcp.json` when invoked.

### Toolsets

| Toolset | Tools | Use in InfraAgent |
|---|---|---|
| `registry` (default) | `providerLookup`, `resourceUsage`, `moduleSearch`, `moduleDetails`, `dataSourceLookup` | CodeGen looks up provider schemas and AVM Terraform modules |
| `terraform` | `plan`, `validate`, `apply`, `init` | IaC validation pipeline + Deploy agent |
| `registry-private` | Same as registry but for private modules | Future: organization module catalog |

### Configuration Options

```json
"args": [
  "run", "-i", "--rm",
  "-e", "TF_TOKEN_app_terraform_io=<token>",
  "hashicorp/terraform-mcp-server:0.5.1",
  "-toolsets=registry,terraform"
]
```

## Azure MCP Server

**Source**: [microsoft/mcp](https://github.com/microsoft/mcp) (GA 1.0)
**Note**: Previously at `Azure/azure-mcp` — archived February 2026, moved to `microsoft/mcp`
**Transport**: stdio (local) or container (remote)

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
| **Networking** | VNets, NSGs, Load Balancers, DNS | CodeGen + Security checks |
| **Storage** | Storage Accounts, Blob, File, Queue, Table | CodeGen |
| **Databases** | SQL, Cosmos DB, PostgreSQL | CodeGen |
| **Security** | Key Vault, Defender, Entra ID | Security agent context |
| **AI** | Foundry, OpenAI, Cognitive Services | Agent management |
| **Architecture** | Cloud Architect, WAF guidance | Consulting Agent best practices |

### Especially Useful Tools

| Tool | Description |
|---|---|
| `azure/listSubscriptions` | Discover user's Azure subscriptions |
| `azure/listResourceGroups` | List existing resource groups in a subscription |
| `azure/cloudArchitect` | Get architecture recommendations (WAF-aligned) |
| `azure/bicepSchema` | Bicep resource schema validation |
| `azure/azureTerraformBestPractices` | Terraform-specific Azure guidance |

## Foundry Remote Deployment

For Foundry-hosted agents, MCP servers **must be remote HTTP** (not localhost/stdio). Requirements:

| Server | Remote Strategy |
|---|---|
| **Bicep MCP** | Deploy as Azure Container App with HTTP transport (port 5007) |
| **Terraform MCP** | Deploy as Azure Container App (Docker image supports StreamableHTTP) |
| **Azure MCP** | Deploy via `pip install msmcp-azure` in the agent container, or as a separate Container App |

**Constraint**: Foundry imposes a **100-second MCP timeout** — long-running plan/apply operations may need to be handled outside MCP.

## Adding a New MCP Server

1. Add the server config to `.vscode/mcp.json`
2. Document it in this file
3. If used by Foundry-hosted agents, plan the remote HTTP deployment
4. Reference the server's tools in the relevant agent's system prompt
