---
description: "Generate Bicep infrastructure code using AVM-first strategy for Azure resources."
tools:
  - azure-mcp/bicepschema
  - azure-mcp/search
---

# Generate Bicep

Generate production-ready Bicep code for the following infrastructure request.

## Requirements

- **Project name**: {{projectName}}
- **Resources**: {{resources}}
- **Azure region**: {{region}}
- **Environment**: {{environment}}

## Rules

1. **Call `azure-mcp/bicepschema`** first to validate resource schemas
2. Use **Azure Verified Modules** (`br/public:avm/res/{provider}/{resource}:{version}`) wherever available
3. Generate this file structure:
   ```
   infra/
   ├── main.bicep          # Orchestration
   ├── main.bicepparam      # Parameters
   └── modules/
       └── {resource}.bicep  # One module per resource group
   ```
4. All resources MUST have tags: `environment`, `project`, `managed-by: infraagent`
5. Use parameterized names: `{env}-{project}-{resource}`
6. Output all resource IDs and endpoints
7. Never hardcode secrets — use Key Vault references or `@secure()`
8. Minimum TLS 1.2
9. Prefer managed identities over keys/connection strings
10. Include a Mermaid architecture diagram as a comment
