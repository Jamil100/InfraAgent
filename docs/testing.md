# Testing Strategy

## Overview

InfraAgent testing follows a layered approach aligned with the clean architecture:

| Layer | What | How |
|---|---|---|
| **Unit** | Domain models, JSON parsing, prompt loading | pytest, no network |
| **Agent mock** | Agent adapters with mocked Foundry client | pytest-asyncio, mock responses |
| **Integration** | Full pipeline with mock agents | pytest-asyncio, all ports mocked |
| **API** | FastAPI endpoints | httpx + TestClient |
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

## Unit Tests

Test domain logic with no external dependencies.

### Model Validation

```python
# tests/test_models.py
from src.core.models import RequirementsHandoff, IaCLanguage

def test_requirements_defaults():
    req = RequirementsHandoff(project_name="test")
    assert req.iac_language == IaCLanguage.BICEP
    assert req.azure_region == "westeurope"
    assert req.environment == "dev"

def test_requirements_serialization():
    req = RequirementsHandoff(
        project_name="contoso",
        resources_needed=["Microsoft.Network/virtualNetworks"],
    )
    data = req.model_dump(mode="json")
    assert data["project_name"] == "contoso"
```

### JSON Parsing

```python
# tests/test_parsing.py
from src.agents.codegen import _parse_codegen_response

def test_parse_codegen_valid():
    text = '```json\n{"files": [{"path": "main.bicep", "content": "param x string"}], "mermaid_diagram": "", "explanation": "test"}\n```'
    result = _parse_codegen_response(text)
    assert len(result.files) == 1
    assert result.files[0].path == "main.bicep"

def test_parse_codegen_no_json():
    result = _parse_codegen_response("No JSON here")
    assert len(result.files) == 0
    assert "No JSON" in result.explanation
```

## Agent Mock Tests

Test agent adapters with a mocked Foundry client.

```python
# tests/test_codegen_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.codegen import CodeGenAgent
from src.core.models import RequirementsHandoff

@pytest.mark.asyncio
async def test_codegen_generates_files():
    # Mock Foundry client
    client = AsyncMock()
    agent = MagicMock(id="agent-123")

    # Mock thread + message + run
    client.agents.create_thread.return_value = MagicMock(id="thread-1")
    client.agents.create_run.return_value = MagicMock(
        status="completed", last_error=None
    )
    client.agents.get_run.return_value = MagicMock(status="completed")
    client.agents.list_messages.return_value = MagicMock(
        data=[MagicMock(
            role="agent",
            content=[MagicMock(text=MagicMock(
                value='```json\n{"files": [{"path": "main.bicep", "content": "param x string"}], "mermaid_diagram": "", "explanation": "test"}\n```'
            ))]
        )]
    )

    codegen = CodeGenAgent(client, agent)
    reqs = RequirementsHandoff(project_name="test", resources_needed=["vnet"])
    result = await codegen.generate(reqs)

    assert len(result.files) == 1
    assert result.files[0].path == "main.bicep"
```

## Integration Tests

Test the full pipeline with all ports mocked.

```python
# tests/test_pipeline.py
import pytest
from src.services.pipeline import OrchestratorPipeline
from src.core.models import *

class MockCodeGen:
    async def generate(self, reqs, feedback=None):
        return CodeGenOutput(
            files=[GeneratedFile(path="main.bicep", content="param x string")],
            explanation="mock",
        )

class MockStandards:
    async def check(self, files):
        return []  # No findings

class MockSecurity:
    async def scan(self, files):
        return []

class MockSCM:
    async def create_branch(self, name): return "sha123"
    async def commit_files(self, branch, files, msg): return branch
    async def create_pr(self, branch, title, body): return "https://github.com/test/pr/1"

@pytest.mark.asyncio
async def test_pipeline_happy_path():
    pipeline = OrchestratorPipeline(MockCodeGen(), MockStandards(), MockSecurity(), MockSCM())
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

## API Tests

Test FastAPI endpoints with httpx TestClient.

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

## Evaluation Framework

For measuring agent output quality beyond unit tests, use the **AI Toolkit evaluation framework**.

### When to Evaluate

- After changing a system prompt
- After switching models
- Before a demo or submission

### Evaluation Metrics

| Metric | Agent | How |
|---|---|---|
| **Requirements completeness** | Consulting | Does the `RequirementsHandoff` capture all user intent? |
| **Code correctness** | CodeGen | Does `bicep build` succeed on generated files? |
| **AVM compliance** | CodeGen | Are AVM modules used where available? |
| **Finding accuracy** | Standards/Security | Do findings match known issues in test code? |
| **False positive rate** | Standards/Security | How often do agents flag correct code? |

### Running Evaluations

Use the AI Toolkit's evaluation tooling:

1. **AI Toolkit sidebar** → **Evaluation**
2. Create a test dataset (input/expected-output pairs)
3. Run the evaluation against your agent
4. Review metrics and traces

See the AI Toolkit documentation for detailed setup.

## File Organization

```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # Domain model unit tests
│   ├── test_parsing.py         # JSON parsing tests
│   ├── test_codegen_agent.py   # CodeGen agent mock tests
│   ├── test_pipeline.py        # Pipeline integration tests
│   └── test_api.py             # FastAPI endpoint tests
```
