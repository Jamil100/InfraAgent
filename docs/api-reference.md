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

Send a message to the Consulting Agent. The agent gathers infrastructure requirements through conversation and produces a structured `RequirementsHandoff` when it has enough information.

**Request Body**:
```json
{
  "message": "I need a VNet with 3 subnets and a Key Vault in West Europe",
  "session_id": "",
  "iac_language": "bicep"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `message` | string | *(required)* | User's natural language message |
| `session_id` | string | `""` (auto-generated) | Session ID for multi-turn conversation |
| `iac_language` | string | `"bicep"` | `"bicep"` or `"terraform"` |

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-...",
  "reply": "I'll create a VNet with 3 subnets...\n\n```json\n{...}\n```",
  "stage": "consulting",
  "requirements_ready": true,
  "pipeline_state": null
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session ID (use in subsequent requests) |
| `reply` | string | Agent's text response |
| `stage` | string | Always `"consulting"` for this endpoint |
| `requirements_ready` | boolean | `true` when agent has produced structured requirements |
| `pipeline_state` | object \| null | Reserved for future use |

**Flow**:
1. First call: omit `session_id` — one is generated and returned
2. Continue chatting with the same `session_id` until `requirements_ready: true`
3. Then call `POST /api/pipeline/start` to kick off code generation

---

## Start Pipeline

### `POST /api/pipeline/start`

Executes the full pipeline: CodeGen → Standards + Security review loop → PR creation.

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
  "stage": "pr_created",
  "pr_url": "https://github.com/org/repo/pull/42",
  "files_generated": 4,
  "findings": 2,
  "error": ""
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session ID |
| `stage` | string | Final pipeline stage (see Pipeline Stages below) |
| `pr_url` | string | GitHub PR URL (empty if failed before PR) |
| `files_generated` | integer | Number of IaC files generated |
| `findings` | integer | Total validation findings (errors + warnings + info) |
| `error` | string | Error message if `stage` is `"failed"` |

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session ID not found — call `/api/chat` first |
| `400` | No requirements yet — complete the consulting chat |
| `500` | Pipeline produced no output |

---

## Pipeline Status

### `GET /api/pipeline/status/{session_id}`

Check the current state of a session.

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-...",
  "has_requirements": true
}
```

**Error Responses**:

| Status | When |
|---|---|
| `404` | Session not found |

---

## Pipeline Stages

The `stage` field in pipeline responses uses these values:

| Stage | Description |
|---|---|
| `consulting` | Gathering requirements |
| `codegen` | Generating IaC code |
| `standards` | Running standards checks |
| `security` | Running security scan |
| `human_review_code` | Awaiting H1 code review approval |
| `pr_created` | PR successfully created |
| `plan` | Running plan/what-if |
| `human_review_plan` | Awaiting H2 plan review approval |
| `deploying` | Applying infrastructure |
| `deployed` | Successfully deployed |
| `failed` | Pipeline error |

---

## Data Models

### RequirementsHandoff

Produced by the Consulting Agent when it has gathered enough information:

```json
{
  "project_name": "contoso-webapp",
  "description": "Web app with VNet and Key Vault",
  "iac_language": "bicep",
  "azure_region": "westeurope",
  "environment": "dev",
  "resources_needed": ["Microsoft.Network/virtualNetworks", "Microsoft.KeyVault/vaults"],
  "constraints": ["Must use managed identity"],
  "subscription_context": {
    "subscription_id": "",
    "resource_groups": [],
    "existing_vnets": [],
    "naming_patterns": []
  }
}
```

### ValidationFinding

Returned by Standards and Security agents:

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

---

## Authentication

The backend uses `DefaultAzureCredential` for Azure services. No API keys are needed for the REST API itself (MVP). Future: add Azure AD bearer token authentication.

## CORS

Configured via `CORS_ORIGINS` environment variable (comma-separated). Default: `http://localhost:3000`.
