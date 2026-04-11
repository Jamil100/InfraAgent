# Testing Strategy

## Overview

InfraAgent testing follows a layered approach aligned with the clean architecture:

| Layer | What | How |
|---|---|---|
| **Unit** | Domain models, policies, JSON parsing, prompt loading | pytest, no network, no mocks |
| **Agent mock** | Agent adapters with mocked Foundry client | pytest-asyncio, mock responses |
| **Integration** | Full pipeline with mock agents (both paths) | pytest-asyncio, all ports mocked |
| **API** | FastAPI endpoints (chat, catalog, deployments) | httpx + TestClient |
| **E2E** | Full pipeline against real Foundry + GitHub | pytest-asyncio, real services |
| **Evaluation** | Agent output quality at scale | AI Toolkit evaluation framework |

## Setup

```bash
cd backend
uv sync --extra dev
```

Run all tests:
```bash
uv run pytest
```

Run with verbose output:
```bash
uv run pytest -v --tb=short
```

Run by layer:
```bash
uv run pytest tests/unit/ -v              # Fast, no deps
uv run pytest tests/integration/ -v        # Mocked ports
uv run pytest tests/api/ -v               # FastAPI TestClient
uv run pytest tests/e2e/ -v -m "not slow" # E2E (requires Azure + GitHub)
```

Run with coverage:
```bash
uv run pytest --cov=src --cov-report=html --cov-report=xml
```

---

## Unit Tests

Test domain logic with no external dependencies. These are pure functions — no mocks needed.

### Model Validation

```python
# tests/unit/domain/test_models.py
from src.core.models import RequirementsHandoff, IaCLanguage, ProjectType

def test_requirements_defaults():
    req = RequirementsHandoff(project_name="test")
    assert req.iac_language == IaCLanguage.BICEP
    assert req.azure_region == "westeurope"
    assert req.environment == "dev"
    assert req.project_type == ProjectType.PRODUCTION

def test_requirements_serialization():
    req = RequirementsHandoff(
        project_name="contoso",
        project_type=ProjectType.ENTERPRISE,
        resources_needed=["Microsoft.Network/virtualNetworks"],
    )
    data = req.model_dump(mode="json")
    assert data["project_name"] == "contoso"
    assert data["project_type"] == "enterprise"

def test_requirements_with_subscription_context():
    req = RequirementsHandoff(
        project_name="test",
        subscription_context={
            "subscription_id": "xxx",
            "resource_groups": ["rg-prod-web"],
            "existing_vnets": [{"name": "vnet-prod", "address_space": ["10.0.0.0/16"]}],
            "naming_patterns": ["rg-{env}-{app}-{region}"],
        },
    )
    assert len(req.subscription_context["resource_groups"]) == 1
```

### Naming Policy

```python
# tests/unit/domain/test_naming_policy.py
from src.domain.policies.naming_policy import validate_resource_name

def test_valid_resource_group_name():
    valid, error = validate_resource_name("azurerm_resource_group", "rg-prod-web-eastus")
    assert valid is True
    assert error is None

def test_invalid_resource_group_name():
    valid, error = validate_resource_name("azurerm_resource_group", "my-resource-group")
    assert valid is False
    assert "rg-{env}-{app}-{region}" in error

def test_unknown_resource_type_allowed():
    valid, _ = validate_resource_name("azurerm_unknown_resource", "anything")
    assert valid is True  # No rule → allow
```

### Tagging Policy

```python
# tests/unit/domain/test_tagging_policy.py
from src.domain.policies.tagging_policy import validate_tags

def test_all_required_tags_present():
    tags = {"environment": "prod", "owner": "team-infra", "cost-center": "CC-001"}
    violations = validate_tags(tags)
    assert violations == []

def test_missing_required_tags():
    tags = {"environment": "prod"}
    violations = validate_tags(tags)
    assert len(violations) == 2  # missing owner and cost-center
    assert any("owner" in v for v in violations)
    assert any("cost-center" in v for v in violations)
```

### Standards Service

```python
# tests/unit/domain/test_standards_service.py
from src.domain.services.standards_service import validate_standards

def test_all_standards_pass():
    resources = [
        {"type": "azurerm_resource_group", "name": "rg-prod-web-eastus",
         "tags": {"environment": "prod", "owner": "team", "cost-center": "CC-001"}}
    ]
    result = validate_standards(resources)
    assert result.passed is True
    assert result.violations == []

def test_naming_violation():
    resources = [
        {"type": "azurerm_resource_group", "name": "bad-name",
         "tags": {"environment": "prod", "owner": "team", "cost-center": "CC-001"}}
    ]
    result = validate_standards(resources)
    assert result.passed is False
    assert result.violations[0].category == "naming"

def test_tagging_violation():
    resources = [
        {"type": "azurerm_resource_group", "name": "rg-prod-web-eastus",
         "tags": {}}
    ]
    result = validate_standards(resources)
    assert result.passed is False
    assert any(v.category == "tagging" for v in result.violations)
```

### JSON Parsing

```python
# tests/unit/test_parsing.py
from src.agents.codegen import _parse_codegen_response

def test_parse_codegen_valid():
    text = '```json\n{"files": [{"path": "main.bicep", "content": "param x string"}], "mermaid_diagram": "graph TD; A-->B", "explanation": "test"}\n```'
    result = _parse_codegen_response(text)
    assert len(result.files) == 1
    assert result.files[0].path == "main.bicep"
    assert result.mermaid_diagram == "graph TD; A-->B"

def test_parse_codegen_no_json():
    result = _parse_codegen_response("No JSON here")
    assert len(result.files) == 0
    assert "No JSON" in result.explanation

def test_parse_codegen_with_avm_modules():
    text = '```json\n{"files": [{"path": "main.bicep", "content": "module vnet \'br/public:avm/res/network/virtual-network:0.5.1\'"}], "mermaid_diagram": "", "explanation": "Used AVM"}\n```'
    result = _parse_codegen_response(text)
    assert "avm" in result.files[0].content
```

### Plan Failure Categorization

```python
# tests/unit/domain/test_plan_failure.py
from src.application.use_cases.generate import GenerateUseCase

def test_categorize_sku_unavailable():
    uc = GenerateUseCase.__new__(GenerateUseCase)
    analysis = uc._categorize_plan_failure(
        "Error: VM size Standard_D4s_v3 not available in westeurope", 1
    )
    assert analysis.category == "sku_unavailable"
    assert analysis.is_fixable_in_code is True

def test_categorize_quota_exceeded():
    uc = GenerateUseCase.__new__(GenerateUseCase)
    analysis = uc._categorize_plan_failure(
        "Error: Exceeded vCPU quota for Standard_D family", 1
    )
    assert analysis.category == "quota_exceeded"
    assert analysis.is_fixable_in_code is False

def test_categorize_resource_conflict():
    uc = GenerateUseCase.__new__(GenerateUseCase)
    analysis = uc._categorize_plan_failure(
        "Error: Resource group rg-prod-web already exists", 1
    )
    assert analysis.category == "resource_conflict"
    assert analysis.is_fixable_in_code is True

def test_categorize_auth_failure():
    uc = GenerateUseCase.__new__(GenerateUseCase)
    analysis = uc._categorize_plan_failure(
        "Error: Authorization failed for subscription", 1
    )
    assert analysis.category == "auth_failure"
    assert analysis.is_fixable_in_code is False
```

---

## Agent Mock Tests

Test agent adapters with a mocked Foundry client.

### CodeGen Agent

```python
# tests/unit/agents/test_codegen_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.codegen import CodeGenAgent
from src.core.models import RequirementsHandoff

@pytest.mark.asyncio
async def test_codegen_generates_files():
    client = AsyncMock()
    agent = MagicMock(id="agent-123")

    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(status="completed", last_error=None)
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(
                value='```json\n{"files": [{"path": "main.bicep", "content": "param x string"}], "mermaid_diagram": "graph TD; A", "explanation": "test"}\n```'
            ))]
        )]
    )

    codegen = CodeGenAgent(client, agent)
    reqs = RequirementsHandoff(project_name="test", resources_needed=["vnet"])
    result = await codegen.generate(reqs)

    assert len(result.files) == 1
    assert result.files[0].path == "main.bicep"
    assert result.mermaid_diagram is not None

@pytest.mark.asyncio
async def test_codegen_with_feedback():
    client = AsyncMock()
    agent = MagicMock(id="agent-123")

    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(status="completed", last_error=None)
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(
                value='```json\n{"files": [{"path": "main.bicep", "content": "fixed code"}], "mermaid_diagram": "", "explanation": "Fixed naming"}\n```'
            ))]
        )]
    )

    codegen = CodeGenAgent(client, agent)
    reqs = RequirementsHandoff(project_name="test")
    feedback = [{"checker": "standards", "severity": "error", "message": "Bad naming"}]
    result = await codegen.generate(reqs, feedback=feedback)

    assert len(result.files) == 1
    assert "fixed" in result.files[0].content
```

### Standards Agent

```python
# tests/unit/agents/test_standards_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.reviewers import StandardsAgent
from src.core.models import GeneratedFile

@pytest.mark.asyncio
async def test_standards_no_findings():
    client = AsyncMock()
    agent = MagicMock(id="standards-agent")

    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(status="completed", last_error=None)
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(value='```json\n[]\n```'))]
        )]
    )

    standards = StandardsAgent(client, agent)
    files = [GeneratedFile(path="main.bicep", content="param x string")]
    findings = await standards.check(files)
    assert findings == []

@pytest.mark.asyncio
async def test_standards_detects_naming_violation():
    client = AsyncMock()
    agent = MagicMock(id="standards-agent")

    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(status="completed", last_error=None)
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(
                value='```json\n[{"checker": "standards", "severity": "error", "resource": "vnet", "file": "main.bicep", "line": 5, "message": "Name does not follow convention", "remediation": "Use vnet-{env}-{region}-{seq}"}]\n```'
            ))]
        )]
    )

    standards = StandardsAgent(client, agent)
    files = [GeneratedFile(path="main.bicep", content="resource vnet ...")]
    findings = await standards.check(files)
    assert len(findings) == 1
    assert findings[0].severity == "error"
```

### Security Agent

```python
# tests/unit/agents/test_security_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.reviewers import SecurityAgent
from src.core.models import GeneratedFile

@pytest.mark.asyncio
async def test_security_detects_public_access():
    client = AsyncMock()
    agent = MagicMock(id="security-agent")

    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(status="completed", last_error=None)
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(
                value='```json\n[{"checker": "security", "severity": "error", "resource": "storageAccount", "file": "modules/storage.bicep", "line": 12, "message": "Public blob access enabled", "remediation": "Set allowBlobPublicAccess to false"}]\n```'
            ))]
        )]
    )

    security = SecurityAgent(client, agent)
    files = [GeneratedFile(path="modules/storage.bicep", content="resource sa ...")]
    findings = await security.scan(files)
    assert len(findings) == 1
    assert findings[0].checker == "security"
```

---

## Integration Tests

Test the full pipeline with all ports mocked. Covers both the chat path and catalog path.

### Chat Path — Happy Path

```python
# tests/integration/test_pipeline_chat.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockCodeGen:
    async def generate(self, reqs, feedback=None):
        return CodeGenOutput(
            files=[GeneratedFile(path="main.bicep", content="param x string")],
            mermaid_diagram="graph TD; A-->B",
            explanation="mock",
        )

class MockValidation:
    async def validate(self, files, language):
        return {"passed": True, "errors": [], "warnings": []}

class MockStandards:
    async def check(self, files):
        return []

class MockSecurity:
    async def scan(self, files):
        return []

class MockSCM:
    async def create_branch(self, name): return "sha123"
    async def commit_files(self, branch, files, msg): return branch
    async def create_pr(self, branch, title, body): return "https://github.com/test/pr/1"

@pytest.mark.asyncio
async def test_pipeline_happy_path():
    pipeline = OrchestratorPipeline(
        MockCodeGen(), MockValidation(), MockStandards(), MockSecurity(), MockSCM()
    )
    reqs = RequirementsHandoff(project_name="test")
    request = InfraRequest(user_message="test", session_id="sess-1")

    states = []
    async for state in pipeline.run(reqs, request):
        states.append(state)

    final = states[-1]
    assert final.stage == PipelineStage.PR_CREATED
    assert final.pr_url == "https://github.com/test/pr/1"
    assert final.loop1_iteration == 1
```

### Chat Path — Maker-Checker Loop

```python
# tests/integration/test_pipeline_loop.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockCodeGenWithRetry:
    def __init__(self):
        self.call_count = 0

    async def generate(self, reqs, feedback=None):
        self.call_count += 1
        return CodeGenOutput(
            files=[GeneratedFile(path="main.bicep", content=f"iteration {self.call_count}")],
            mermaid_diagram="", explanation="mock",
        )

class MockStandardsWithErrors:
    def __init__(self):
        self.call_count = 0

    async def check(self, files):
        self.call_count += 1
        if self.call_count <= 1:
            return [ValidationFinding(
                checker="standards", severity="error", resource="vnet",
                file="main.bicep", line=1, message="Bad naming",
                remediation="Fix it",
            )]
        return []  # Pass on second attempt

@pytest.mark.asyncio
async def test_pipeline_retries_on_standards_failure():
    codegen = MockCodeGenWithRetry()
    standards = MockStandardsWithErrors()
    pipeline = OrchestratorPipeline(codegen, MockValidation(), standards, MockSecurity(), MockSCM())
    reqs = RequirementsHandoff(project_name="test")
    request = InfraRequest(user_message="test", session_id="sess-1")

    states = []
    async for state in pipeline.run(reqs, request):
        states.append(state)

    assert codegen.call_count == 2  # Retried once
    assert states[-1].stage == PipelineStage.PR_CREATED
```

### Chat Path — IaC Validation Failure

```python
# tests/integration/test_pipeline_iac_validation.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockValidationFail:
    def __init__(self):
        self.call_count = 0

    async def validate(self, files, language):
        self.call_count += 1
        if self.call_count <= 1:
            return {"passed": False, "errors": ["Validate: missing required provider"], "warnings": []}
        return {"passed": True, "errors": [], "warnings": []}

@pytest.mark.asyncio
async def test_pipeline_retries_on_iac_validation_failure():
    codegen = MockCodeGenWithRetry()
    validation = MockValidationFail()
    pipeline = OrchestratorPipeline(codegen, validation, MockStandards(), MockSecurity(), MockSCM())
    reqs = RequirementsHandoff(project_name="test")
    request = InfraRequest(user_message="test", session_id="sess-1")

    states = []
    async for state in pipeline.run(reqs, request):
        states.append(state)

    assert codegen.call_count == 2
    assert validation.call_count == 2
    assert states[-1].stage == PipelineStage.PR_CREATED
```

### Catalog Path

```python
# tests/integration/test_pipeline_catalog.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockTemplateRegistry:
    async def hydrate(self, name, language, parameters, standards):
        return HydratedTemplate(
            files=[{"path": "main.tf", "content": "resource ..."}],
            metadata=TemplateMetadata(name="aks-cluster", azure_services=["AKS"]),
            applied_standards={"naming": "applied"},
        )

@pytest.mark.asyncio
async def test_catalog_path_happy():
    pipeline = OrchestratorPipeline(
        MockCodeGen(), MockValidation(), MockStandards(), MockSecurity(), MockSCM(),
        template_registry=MockTemplateRegistry(),
    )
    request = CatalogDeployRequest(
        template_name="aks-cluster", iac_language="terraform",
        parameters={"node_count": 3}, session_id="sess-1",
    )

    states = []
    async for state in pipeline.run_catalog(request):
        states.append(state)

    final = states[-1]
    assert final.stage == PipelineStage.PR_CREATED
```

### Plan-Failure Rework (Loop 2)

```python
# tests/integration/test_pipeline_plan_rework.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockDeployWithPlanFailure:
    def __init__(self):
        self.plan_count = 0

    async def plan(self, files, variables):
        self.plan_count += 1
        if self.plan_count <= 1:
            return PlanResult(
                success=False,
                output="Error: VM size Standard_D4s_v3 not available in westeurope",
                resources_to_create=0, resources_to_modify=0, resources_to_destroy=0,
            )
        return PlanResult(success=True, output="Plan: 5 to add", resources_to_create=5,
                          resources_to_modify=0, resources_to_destroy=0)

@pytest.mark.asyncio
async def test_plan_failure_triggers_rework():
    deploy = MockDeployWithPlanFailure()
    pipeline = OrchestratorPipeline(
        MockCodeGen(), MockValidation(), MockStandards(), MockSecurity(), MockSCM(),
        deploy=deploy,
    )
    reqs = RequirementsHandoff(project_name="test")
    request = InfraRequest(user_message="test", session_id="sess-1")

    states = []
    async for state in pipeline.run(reqs, request):
        states.append(state)

    assert deploy.plan_count == 2  # Plan retried after rework
    stage_names = [s.stage.value for s in states]
    assert "reworking_plan_failure" in stage_names
```

---

## Subscription Discovery Tests

```python
# tests/integration/test_subscription_discovery.py
import pytest
from unittest.mock import AsyncMock
from src.infrastructure.adapters.subscription_discovery_adapter import AzureSubscriptionDiscoveryAdapter

@pytest.mark.asyncio
async def test_discovery_returns_resource_groups():
    adapter = AzureSubscriptionDiscoveryAdapter(credential=AsyncMock())
    # Mock Azure management client responses
    adapter._resource_client = AsyncMock()
    adapter._resource_client.resource_groups.list.return_value = [
        MagicMock(name="rg-prod-web-westeurope", location="westeurope"),
    ]

    context = await adapter.discover("test-subscription-id")
    assert "rg-prod-web-westeurope" in context.resource_groups

@pytest.mark.asyncio
async def test_discovery_detects_naming_patterns():
    adapter = AzureSubscriptionDiscoveryAdapter(credential=AsyncMock())
    adapter._resource_client = AsyncMock()
    adapter._resource_client.resource_groups.list.return_value = [
        MagicMock(name="rg-prod-web-westeurope"),
        MagicMock(name="rg-prod-api-westeurope"),
        MagicMock(name="rg-dev-web-westeurope"),
    ]

    context = await adapter.discover("test-subscription-id")
    assert any("rg-{env}-{app}-{region}" in p for p in context.naming_patterns)
```

---

## API Tests

Test FastAPI endpoints with httpx TestClient.

```python
# tests/api/test_api.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_chat_creates_session():
    resp = client.post("/api/chat", json={
        "message": "I need a VNet",
        "iac_language": "bicep",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["stage"] == "consulting"

def test_catalog_list():
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "templates" in data

def test_catalog_template_detail():
    resp = client.get("/api/catalog/aks-cluster")
    assert resp.status_code in (200, 404)  # 404 if wiki not populated

def test_pipeline_start_without_session():
    resp = client.post("/api/pipeline/start", json={"session_id": "nonexistent"})
    assert resp.status_code == 404

def test_standards_endpoint():
    resp = client.get("/api/standards")
    assert resp.status_code == 200
    data = resp.json()
    assert "naming_rules" in data
    assert "required_tags" in data
```

---

## E2E Tests

Full pipeline tests against real Foundry + GitHub. These are slow and require Azure authentication.

```python
# tests/e2e/test_chat_to_deploy.py
import pytest

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_chat_path_end_to_end():
    """
    Full E2E: Chat → Consulting → Subscription Discovery → CodeGen → 
    IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy
    
    Requires:
    - Azure credentials (az login)
    - Foundry project with model deployments
    - GitHub PAT with repo + workflow scopes
    - Target Azure subscription
    """
    # 1. Start consulting conversation
    # 2. Provide infrastructure requirements
    # 3. Wait for requirements_ready
    # 4. Start pipeline
    # 5. Auto-approve H1
    # 6. Verify PR created
    # 7. Wait for plan completion
    # 8. Auto-approve H2
    # 9. Wait for deployment
    # 10. Verify resources exist in Azure
    pass  # Implementation follows pipeline integration pattern with real clients

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_catalog_path_end_to_end():
    """
    Full E2E: Catalog → Template Hydrate → Validate → H1 → PR → Plan → H2 → Deploy
    """
    pass

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_plan_failure_rework_end_to_end():
    """
    Full E2E: Chat → CodeGen → Plan fails → Rework → New PR → Plan succeeds → Deploy
    """
    pass
```

---

## Evaluation Framework

For measuring agent output quality beyond unit tests, use the **AI Toolkit evaluation framework**.

### When to Evaluate

- After changing a system prompt
- After switching models or ModelRouter profiles
- Before a demo or submission
- When adding a new domain skill to the knowledge wiki

### Evaluation Metrics

| Metric | Agent | How |
|---|---|---|
| **Requirements completeness** | Consulting | Does the `RequirementsHandoff` capture all user intent? |
| **Project type accuracy** | Consulting | Is the project classified correctly (demo/prod/enterprise/regulated)? |
| **Subscription discovery quality** | Consulting | Are existing resources surfaced accurately? |
| **Code correctness** | CodeGen | Does `bicep build` / `terraform validate` succeed on generated files? |
| **AVM compliance** | CodeGen | Are AVM modules used where available? |
| **Secret safety** | CodeGen | Are secrets handled correctly (no hardcoding, Key Vault refs)? |
| **File structure compliance** | CodeGen | Does output follow the defined file structure conventions? |
| **Diagram accuracy** | CodeGen | Does the Mermaid diagram reflect all resources in the IaC code? |
| **Finding accuracy** | Standards/Security | Do findings match known issues in test code? |
| **False positive rate** | Standards/Security | How often do agents flag correct code? |

### Example Golden Dataset

```jsonl
{"input": {"project_name": "test-vnet", "resources_needed": ["Microsoft.Network/virtualNetworks"]}, "expected": {"has_vnet": true, "uses_avm": true, "has_nsg": true, "naming_valid": true}}
{"input": {"project_name": "test-aks", "resources_needed": ["Microsoft.ContainerService/managedClusters"]}, "expected": {"has_aks": true, "uses_avm": true, "has_acr": true, "has_monitoring": true}}
{"input": {"project_name": "test-webapp", "resources_needed": ["Microsoft.Web/sites", "Microsoft.Sql/servers"]}, "expected": {"has_app_service": true, "has_sql": true, "has_keyvault": true, "secrets_safe": true}}
```

### Running Evaluations

```python
# tests/evaluation/test_codegen_quality.py
from azure.ai.evaluation import evaluate

results = evaluate(
    data="tests/evaluation/golden/codegen_cases.jsonl",
    evaluators={
        "validity": terraform_validity_evaluator,
        "standards": standards_compliance_evaluator,
        "security": security_scan_evaluator,
        "avm_compliance": avm_usage_evaluator,
    },
    model=codegen_agent,
)
assert results["validity"]["pass_rate"] > 0.95
assert results["standards"]["pass_rate"] == 1.0
assert results["avm_compliance"]["pass_rate"] > 0.80
```

Or use the AI Toolkit UI:

1. **AI Toolkit sidebar** → **Evaluation**
2. Create a test dataset (input/expected-output pairs)
3. Run the evaluation against your agent
4. Review metrics and traces

---

## File Organization

```
backend/
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_models.py              # Domain model unit tests
│   │   │   ├── test_naming_policy.py        # Naming convention rules
│   │   │   ├── test_tagging_policy.py       # Required tags rules
│   │   │   ├── test_standards_service.py    # Standards orchestration
│   │   │   └── test_plan_failure.py         # Plan failure categorization
│   │   ├── agents/
│   │   │   ├── test_codegen_agent.py        # CodeGen agent mock tests
│   │   │   ├── test_standards_agent.py      # Standards agent mock tests
│   │   │   └── test_security_agent.py       # Security agent mock tests
│   │   └── test_parsing.py                  # JSON parsing tests
│   ├── integration/
│   │   ├── test_pipeline_chat.py            # Chat path pipeline tests
│   │   ├── test_pipeline_catalog.py         # Catalog path pipeline tests
│   │   ├── test_pipeline_loop.py            # Maker-checker loop tests
│   │   ├── test_pipeline_iac_validation.py  # IaC validation pipeline tests
│   │   ├── test_pipeline_plan_rework.py     # Plan-failure rework loop tests
│   │   ├── test_subscription_discovery.py   # Subscription discovery adapter tests
│   │   └── test_github_adapter.py           # GitHub adapter tests
│   ├── api/
│   │   └── test_api.py                      # FastAPI endpoint tests
│   ├── e2e/
│   │   └── test_chat_to_deploy.py           # Full pipeline E2E tests
│   └── evaluation/
│       ├── golden/
│       │   └── codegen_cases.jsonl           # Golden dataset for evaluation
│       └── test_codegen_quality.py           # Agent quality evaluation
```