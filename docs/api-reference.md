# API Reference

Base URL: `http://localhost:8000`

## Health Check

### `GET /health`

Returns service status.

**Response** `200 OK`:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Chat with Consulting Agent

### `POST /api/chat`

Send a message to the Consulting Agent. The agent gathers infrastructure requirements through conversation, performs subscription discovery, classifies the project type, and produces a structured `RequirementsHandoff` when it has enough information.

**Request Body**:
```json
{
  "message": "I need a VNet with 3 subnets and a Key Vault in West Europe",
  "session_id": "",
  "iac_language": "bicep",
  "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `message` | string | *(required)* | User's natural language message |
| `session_id` | string | `""` (auto-generated) | Session ID for multi-turn conversation |
| `iac_language` | string | `"bicep"` | `"bicep"` or `"terraform"` |
| `subscription_id` | string | `""` | Target Azure subscription ID for subscription discovery |

**Response** `200 OK` (SSE stream):

```json
// Event: assistant_message
{
  "type": "assistant_message",
  "content": "Great, let me help you design that. A few questions...",
  "session_id": "a1b2c3d4-...",
  "stage": "consulting"
}

// Event: stage_change
{
  "type": "stage_change",
  "stage": "discovering_subscription",
  "message": "Connecting to Azure subscription to inventory existing resources..."
}

// Event: subscription_context
{
  "type": "subscription_context",
  "subscription_name": "Production-Sub-01",
  "resource_groups": ["rg-prod-web-westeurope", "rg-prod-data-westeurope"],
  "vnets": [{"name": "vnet-prod-westeurope", "address_space": ["10.0.0.0/16"]}],
  "naming_patterns": ["rg-{env}-{app}-{region}"],
  "message": "Found 2 resource groups, 1 VNet, detected naming pattern: rg-{env}-{app}-{region}"
}

// Event: stage_change (when code generation begins)
{
  "type": "stage_change",
  "stage": "generating",
  "message": "Generating Bicep code..."
}

// Event: stage_change (IaC validation pipeline)
{
  "type": "stage_change",
  "stage": "validating_iac",
  "message": "Running IaC validation pipeline (fmt → validate → lint)..."
}

// Event: files_generated
{
  "type": "files_generated",
  "files": [
    {"path": "modules/appService.bicep", "content": "...", "language": "bicep"}
  ],
  "diagram_url": "/api/deployments/{id}/diagram",
  "diagram_mermaid": "graph TD; ..."
}

// Event: approval_required
{
  "type": "approval_required",
  "gate": "h1_code_review",
  "deployment_id": "uuid",
  "message": "Please review the generated code and architecture diagram."
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session ID (use in subsequent requests) |
| `reply` | string | Agent's text response (non-streaming fallback) |
| `stage` | string | Current pipeline stage |
| `requirements_ready` | boolean | `true` when agent has produced structured requirements |
| `project_type` | string \| null | Classified project type: `"demo"`, `"production"`, `"enterprise"`, `"regulated"` |
| `pipeline_state` | object \| null | Full `PipelineState` snapshot (see Data Models) |

**Flow**:
1. First call: omit `session_id` — one is generated and returned
2. Optionally provide `subscription_id` to trigger subscription discovery
3. Continue chatting with the same `session_id` until `requirements_ready: true`
4. Then call `POST /api/pipeline/start` to kick off code generation

---

## Start Pipeline

### `POST /api/pipeline/start`

Starts the pipeline as a **background task** and returns immediately. The pipeline runs asynchronously; poll `/api/pipeline/status/{session_id}` or connect via WebSocket for real-time updates.

**Prerequisite**: Complete a `/api/chat` session until `requirements_ready: true`.

**Request Body**:
```json
{
  "session_id": "a1b2c3d4-..."
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | *(required)* Session ID from a completed chat |

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-...",
  "status": "started",
  "message": "Pipeline started in background. Poll /api/pipeline/status/{session_id} for progress."
}
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session ID not found — call `/api/chat` first |
| `400` | No requirements yet — complete the consulting chat |
| `409` | Pipeline already running for this session |

---

## Pipeline Status

### `GET /api/pipeline/status/{session_id}`

Check the current state of a pipeline run. Poll this endpoint after calling `POST /api/pipeline/start`.

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-...",
  "has_requirements": true,
  "pipeline_running": true,
  "h1_approved": null,
  "h2_approved": null,
  "pipeline_state": {
    "stage": "standards",
    "iteration": 2,
    "project_type": "production",
    "pr_url": "",
    "files": [...],
    "findings": [...],
    "plan_output": null,
    "plan_error_category": null,
    "plan_rework_iteration": 0,
    "diagram_mermaid": "graph TD; ...",
    "subscription_context": {...},
    "error": ""
  }
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session ID |
| `has_requirements` | boolean | Whether a `RequirementsHandoff` exists for this session |
| `pipeline_running` | boolean | `true` while the background task is still executing |
| `h1_approved` | boolean \| null | `null` = gate not yet reached; `true`/`false` = decision |
| `h2_approved` | boolean \| null | `null` = gate not yet reached; `true`/`false` = decision |
| `pipeline_state` | object \| null | Full `PipelineState` snapshot (see Data Models) |

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session not found |

---

## Human Gate Approvals

### `POST /api/pipeline/approve/h1`

Approve or reject the **H1 code review gate** (approve generated code + architecture diagram before PR creation).

**Request Body**:
```json
{
  "session_id": "a1b2c3d4-...",
  "approved": true,
  "comment": "LGTM — naming conventions are correct"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `session_id` | string | *(required)* | Session ID |
| `approved` | boolean | *(required)* | `true` to approve and proceed to PR; `false` to reject |
| `comment` | string | `""` | Optional reviewer comment logged with the pipeline state |

**Response** `200 OK`:
```json
{ "ok": true }
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session not found |

---

### `POST /api/pipeline/approve/h2`

Approve or reject the **H2 plan review gate** (approve the `what-if`/`terraform plan` output before deployment).

**Request Body**:
```json
{
  "session_id": "a1b2c3d4-...",
  "approved": true,
  "comment": "Plan looks correct — no unexpected deletions"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `session_id` | string | *(required)* | Session ID |
| `approved` | boolean | *(required)* | `true` to proceed to deployment; `false` to fail the pipeline |
| `comment` | string | `""` | Optional reviewer comment |

**Response** `200 OK`:
```json
{ "ok": true }
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session not found |

---

## Self-Service Catalog

### `GET /api/catalog`

List templates from the knowledge wiki. Supports keyword search and filtering.

**Query Parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | `""` | Keyword search (e.g., "AKS cluster", "3-tier web app") |
| `complexity` | string | `""` | Filter by complexity: `"simple"`, `"moderate"`, `"complex"` |
| `iac_language` | string | `""` | Filter by language: `"terraform"`, `"bicep"` |

**Response** `200 OK`:
```json
{
  "templates": [
    {
      "name": "aks-cluster",
      "display_name": "Azure Kubernetes Service Cluster",
      "description": "Production-ready AKS cluster with managed identity, Azure CNI, and monitoring.",
      "azure_services": ["Azure Kubernetes Service", "Azure Container Registry", "Azure Monitor"],
      "complexity": "moderate",
      "iac_languages": ["terraform", "bicep"],
      "tags": ["kubernetes", "containers", "aks"],
      "version": "1.2.0"
    }
  ]
}
```

---

### `GET /api/catalog/{name}`

Get template details including parameter schema.

**Response** `200 OK`:
```json
{
  "name": "aks-cluster",
  "display_name": "Azure Kubernetes Service Cluster",
  "description": "Production-ready AKS cluster with managed identity, Azure CNI, and monitoring.",
  "azure_services": ["Azure Kubernetes Service", "Azure Container Registry", "Azure Monitor"],
  "complexity": "moderate",
  "iac_languages": ["terraform", "bicep"],
  "version": "1.2.0",
  "parameters": [
    {
      "name": "node_count",
      "type": "integer",
      "default": 3,
      "description": "Number of worker nodes in the default node pool",
      "validation": { "min": 1, "max": 100 }
    },
    {
      "name": "vm_size",
      "type": "string",
      "default": "Standard_D4s_v5",
      "description": "VM SKU for worker nodes",
      "validation": { "allowed_values": ["Standard_D2s_v5", "Standard_D4s_v5", "Standard_D8s_v5"] }
    }
  ]
}
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Template not found in knowledge wiki |

---

### `POST /api/catalog/{name}/deploy`

Deploy a catalog template. Hydrates the template with user parameters and org-level standards, runs the IaC Validation Pipeline, and enters the shared deployment pipeline (PR → Plan → Deploy).

**Request Body**:
```json
{
  "template_name": "aks-cluster",
  "iac_language": "terraform",
  "parameters": {
    "node_count": 5,
    "vm_size": "Standard_D4s_v5",
    "kubernetes_version": "1.29",
    "enable_monitoring": true
  },
  "target_repo": "org/infra-deployments",
  "target_branch": "main",
  "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

| Field | Type | Description |
|---|---|---|
| `template_name` | string | *(required)* Template name from catalog |
| `iac_language` | string | *(required)* `"bicep"` or `"terraform"` |
| `parameters` | object | *(required)* Template-specific parameters |
| `target_repo` | string | GitHub repo for PR creation (default from settings) |
| `target_branch` | string | Base branch for PR (default: `"main"`) |
| `subscription_id` | string | Azure subscription for lightweight discovery (naming conflicts, quota check) |

**Response** `200 OK`:
```json
{
  "deployment_id": "uuid",
  "session_id": "uuid",
  "status": "hydrating",
  "message": "Template 'aks-cluster' is being hydrated with your parameters..."
}
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Template not found |
| `400` | Missing required parameters or invalid parameter values |

---

## Deployments

### `GET /api/deployments/{id}`

Get deployment status and metadata.

**Response** `200 OK`:
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "path": "catalog_template",
  "iac_language": "terraform",
  "stage": "awaiting_plan_review",
  "project_type": "production",
  "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "template_name": "aks-cluster",
  "pr": {
    "number": 42,
    "url": "https://github.com/org/repo/pull/42",
    "state": "open"
  },
  "plan": {
    "status": "completed",
    "resources_to_create": 8,
    "resources_to_modify": 0,
    "resources_to_destroy": 0,
    "error_category": null,
    "rework_iteration": 0
  },
  "diagram_url": "/api/deployments/uuid/diagram",
  "files_count": 5,
  "iteration_count": 1,
  "created_at": "2026-04-09T10:30:00Z",
  "updated_at": "2026-04-09T10:32:15Z"
}
```

---

### `GET /api/deployments/{id}/plan`

Get the plan/what-if output for a deployment.

**Response** `200 OK`:
```json
{
  "deployment_id": "uuid",
  "plan_output": "Terraform will perform the following actions:\n  + azurerm_resource_group.main\n  ...",
  "plan_status": "completed",
  "error_category": null,
  "rework_iteration": 0
}
```

---

### `GET /api/deployments/{id}/files`

Get generated IaC files for a deployment.

**Response** `200 OK`:
```json
{
  "deployment_id": "uuid",
  "files": [
    { "path": "infra/main.bicep", "content": "targetScope = 'resourceGroup'\n...", "language": "bicep" },
    { "path": "infra/modules/vnet.bicep", "content": "param name string\n...", "language": "bicep" }
  ]
}
```

---

### `GET /api/deployments/{id}/diagram`

Get the auto-generated architecture diagram.

**Response** `200 OK`:
```json
{
  "deployment_id": "uuid",
  "mermaid": "graph TD;\n  RG[Resource Group] --> VNet\n  RG --> KV[Key Vault]",
  "svg_url": "/api/deployments/uuid/diagram.svg"
}
```

---

## Standards

### `GET /api/standards`

Load current organizational standards (naming conventions, required tags, policies).

**Response** `200 OK`:
```json
{
  "naming_rules": [
    {
      "resource_type": "azurerm_resource_group",
      "pattern": "rg-{env}-{app}-{region}",
      "example": "rg-prod-web-eastus"
    }
  ],
  "required_tags": [
    { "name": "environment", "enforcement": "required", "description": "Deployment stage (dev, staging, prod)" },
    { "name": "owner", "enforcement": "required", "description": "Team or individual responsible" },
    { "name": "cost-center", "enforcement": "required", "description": "Finance cost allocation code" }
  ]
}
```

---

## WebSocket — Real-Time Updates

### `WS /ws/chat/{conversation_id}`

WebSocket connection for real-time streaming of chat messages and pipeline status updates. Provides SSE-style events during the pipeline run.

**Event Types**:

| Event Type | Description |
|---|---|
| `assistant_message` | Streaming text from agents |
| `stage_change` | Pipeline stage transition |
| `subscription_context` | Subscription discovery results |
| `files_generated` | Generated IaC code blocks + diagram |
| `approval_required` | Human gate reached (H1 or H2) |
| `deployment_status` | Plan/apply progress updates |
| `plan_failure` | Plan failure with error category and rework status |
| `deployment_complete` | Final success/failure status |

---

## Pipeline Stages

The `stage` field in pipeline responses uses these values:

| Stage | Description |
|---|---|
| `consulting` | Gathering requirements via conversational chat |
| `discovering_subscription` | Connecting to Azure subscription to inventory resources |
| `codegen` | Generating IaC code (AVM-first) |
| `validating_iac` | Deterministic CLI validation (`bicep build`/`lint`, `terraform fmt`/`validate`) |
| `standards` | Running standards checks (naming, tagging, structure) |
| `security` | Running security scan (tfsec/Checkov) |
| `human_review_code` | Awaiting H1 code review approval |
| `pr_created` | PR successfully created |
| `plan` | Running plan/what-if |
| `reworking_plan_failure` | Plan failed — CodeGen is reworking code (Loop 2) |
| `human_review_plan` | Awaiting H2 plan review approval |
| `deploying` | Applying infrastructure |
| `deployed` | Successfully deployed |
| `failed` | Pipeline error |
| `cancelled` | Pipeline cancelled by user |

---

## Data Models

### RequirementsHandoff

Produced by the Consulting Agent when it has gathered enough information:

```json
{
  "project_name": "contoso-webapp",
  "description": "Web app with VNet and Key Vault",
  "iac_language": "bicep",
  "project_type": "production",
  "azure_region": "westeurope",
  "environment": "dev",
  "resources_needed": ["Microsoft.Network/virtualNetworks", "Microsoft.KeyVault/vaults"],
  "constraints": ["Must use managed identity"],
  "subscription_context": {
    "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "subscription_name": "Production-Sub-01",
    "resource_groups": ["rg-prod-web-westeurope"],
    "existing_vnets": [{"name": "vnet-prod-westeurope", "address_space": ["10.0.0.0/16"]}],
    "naming_patterns": ["rg-{env}-{app}-{region}"],
    "quotas": {"Microsoft.Compute/virtualMachines": {"used": 10, "limit": 50}}
  }
}
```

### ValidationFinding

Returned by the IaC Validation Pipeline, Standards Agent, and Security Agent:

```json
{
  "checker": "security",
  "severity": "error",
  "resource": "storageAccount",
  "file": "infra/modules/storage.bicep",
  "line": 12,
  "message": "Storage account allows public blob access",
  "remediation": "Set allowBlobPublicAccess to false"
}
```

### CodeGenOutput

Returned by the CodeGen agent (internal, surfaced via pipeline response):

```json
{
  "files": [
    { "path": "infra/main.bicep", "content": "targetScope = 'resourceGroup'\n..." },
    { "path": "infra/modules/vnet.bicep", "content": "param name string\n..." }
  ],
  "mermaid_diagram": "graph LR\n  RG[Resource Group] --> VNet\n  RG --> KV[Key Vault]",
  "explanation": "Generated VNet with 3 subnets and a Key Vault using AVM modules."
}
```

### PlanFailureAnalysis

Returned by the Deploy Agent when a plan fails (used in Loop 2 rework):

```json
{
  "category": "sku_unavailable",
  "error_message": "VM size Standard_D4s_v3 not available in westeurope",
  "is_fixable_in_code": true,
  "suggested_fix": "Query Azure MCP for alternative SKUs/regions",
  "rework_iteration": 1
}
```

Plan failure categories: `resource_conflict`, `sku_unavailable`, `quota_exceeded`, `auth_failure`, `provider_mismatch`, `module_error`, `unknown`.

---

## Authentication

The backend uses `DefaultAzureCredential` for Azure services. No API keys are needed for the REST API itself (MVP). Future: add Entra ID bearer token (JWT) authentication.

## CORS

Configured via `CORS_ORIGINS` environment variable (comma-separated). Default: `http://localhost:3000`.