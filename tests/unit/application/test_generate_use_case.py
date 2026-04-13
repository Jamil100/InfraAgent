from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.ports.infra_provider_port import ValidationResult
from src.application.ports.llm_port import LLMResponse
from src.application.ports.policy_engine_port import PolicyResult, PolicyViolation
from src.application.ports.template_registry_port import HydratedTemplate, TemplateMetadata
from src.application.use_cases.generate import GenerateUseCase
from src.domain.models.models import GeneratedFile, IaCLanguage


def _template_metadata() -> TemplateMetadata:
    return TemplateMetadata(
        name="webapp",
        description="web app template",
        azure_services=["compute"],
        complexity="simple",
        iac_languages=["bicep"],
        parameters=[],
        tags=[],
        version="1.0.0",
    )


@pytest.mark.asyncio
async def test_run_custom_path_success() -> None:
    llm = Mock()
    llm.complete_with_tools = AsyncMock(
        return_value=LLMResponse(
            content='```json\n{"files":[{"path":"infra/main.bicep","content":"resource x"}]}\n```'
        )
    )
    llm.complete = AsyncMock(return_value=LLMResponse(content="graph TD\nA-->B"))

    policy = Mock()
    policy.validate_naming = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_tags = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_security = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))

    provider = Mock()
    provider.format_check = AsyncMock(return_value=ValidationResult(valid=True))
    provider.validate = AsyncMock(return_value=ValidationResult(valid=True))
    provider.lint = AsyncMock(
        return_value=ValidationResult(valid=True, warnings=["deprecated attribute"])
    )

    templates = Mock()
    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    tool_executor = Mock(return_value={})

    result = await use_case.run_custom_path(
        requirements="create a vnet",
        language=IaCLanguage.BICEP,
        conversation_history=[],
        mcp_tool_executor=tool_executor,
    )

    assert len(result.files) == 1
    assert result.standards_passed is True
    assert result.security_passed is True
    assert result.iteration_count == 1
    assert result.diagram_mermaid == "graph TD\nA-->B"
    assert result.violations == [
        {
            "checker": "iac_validation",
            "severity": "warning",
            "resource": "",
            "file": "",
            "line": 0,
            "message": "deprecated attribute",
            "remediation": "",
        }
    ]
    llm.complete_with_tools.assert_awaited_once()
    llm.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_custom_path_stops_after_max_iterations() -> None:
    llm = Mock()
    llm.complete_with_tools = AsyncMock(
        return_value=LLMResponse(
            content='```json\n{"files":[{"path":"infra/main.bicep","content":"resource x"}]}\n```'
        )
    )
    llm.complete = AsyncMock(return_value=LLMResponse(content="graph TD\nA-->B"))

    policy = Mock()
    policy.validate_naming = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_tags = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_security = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))

    provider = Mock()
    provider.format_check = AsyncMock(return_value=ValidationResult(valid=False, errors=["fmt failed"]))
    provider.validate = AsyncMock(return_value=ValidationResult(valid=True))
    provider.lint = AsyncMock(return_value=ValidationResult(valid=True))

    templates = Mock()
    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    result = await use_case.run_custom_path(
        requirements="create a vnet",
        language=IaCLanguage.BICEP,
        conversation_history=[],
        mcp_tool_executor=Mock(return_value={}),
    )

    assert result.iteration_count == 3
    assert result.standards_passed is False
    assert result.security_passed is False
    assert len(result.violations) == 3
    assert all(v["checker"] == "iac_validation" for v in result.violations)
    policy.validate_naming.assert_not_called()
    policy.validate_tags.assert_not_called()
    policy.validate_security.assert_not_called()


@pytest.mark.asyncio
async def test_run_iac_validation_pipeline_runs_in_deterministic_order() -> None:
    call_order: list[str] = []

    llm = Mock()
    policy = Mock()
    templates = Mock()
    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    async def _format_check(files: list[dict[str, str]]) -> ValidationResult:
        if not files:
            pytest.fail("format_check should receive files")
        call_order.append("format_check")
        return ValidationResult(valid=True)

    async def _validate(files: list[dict[str, str]]) -> ValidationResult:
        if not files:
            pytest.fail("validate should receive files")
        call_order.append("validate")
        return ValidationResult(valid=True)

    async def _lint(files: list[dict[str, str]]) -> ValidationResult:
        if not files:
            pytest.fail("lint should receive files")
        call_order.append("lint")
        return ValidationResult(valid=True)

    provider = Mock()
    provider.format_check = AsyncMock(side_effect=_format_check)
    provider.validate = AsyncMock(side_effect=_validate)
    provider.lint = AsyncMock(side_effect=_lint)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    files = [GeneratedFile(path="infra/main.bicep", content="resource x")]

    result = await use_case._run_iac_validation_pipeline(provider, files, IaCLanguage.BICEP)

    assert result["passed"] is True
    assert call_order == ["format_check", "validate", "lint"]


@pytest.mark.asyncio
async def test_run_catalog_path_hydrates_template_and_validates_syntax_only() -> None:
    llm = Mock()
    policy = Mock()

    templates = Mock()
    templates.hydrate = AsyncMock(
        return_value=HydratedTemplate(
            files=[{"path": "infra/main.bicep", "content": "resource x"}],
            metadata=_template_metadata(),
            applied_standards={},
        )
    )

    provider = Mock()
    provider.validate = AsyncMock(return_value=ValidationResult(valid=False, errors=["syntax error"]))
    provider.format_check = AsyncMock(return_value=ValidationResult(valid=True))
    provider.lint = AsyncMock(return_value=ValidationResult(valid=True))

    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    result = await use_case.run_catalog_path(
        template_name="webapp",
        language=IaCLanguage.BICEP,
        parameters={"name": "demo"},
        standards={"tags": {"managed-by": "infraagent"}},
    )

    assert len(result.files) == 1
    assert result.iteration_count == 1
    assert result.standards_passed is True
    assert result.security_passed is True
    assert len(result.violations) == 1
    assert result.violations[0]["checker"] == "syntax_validation"
    policy.validate_naming.assert_not_called()
    policy.validate_tags.assert_not_called()
    policy.validate_security.assert_not_called()


@pytest.mark.asyncio
async def test_run_custom_path_retries_when_codegen_returns_no_files() -> None:
    llm = Mock()
    llm.complete_with_tools = AsyncMock(return_value=LLMResponse(content="not-json"))
    llm.complete = AsyncMock(return_value=LLMResponse(content="graph TD\nA-->B"))

    policy = Mock()
    policy.validate_naming = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_tags = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_security = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))

    provider = Mock()
    provider.format_check = AsyncMock(return_value=ValidationResult(valid=True))
    provider.validate = AsyncMock(return_value=ValidationResult(valid=True))
    provider.lint = AsyncMock(return_value=ValidationResult(valid=True))

    templates = Mock()
    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    result = await use_case.run_custom_path(
        requirements="create a vnet",
        language=IaCLanguage.BICEP,
        conversation_history=[],
        mcp_tool_executor=Mock(return_value={}),
    )

    assert result.iteration_count == 3
    assert result.files == []
    assert result.standards_passed is False
    assert result.security_passed is False
    assert len(result.violations) == 3
    assert all(v["checker"] == "codegen" for v in result.violations)
    assert llm.complete_with_tools.await_count == 3
    provider.format_check.assert_not_called()
    provider.validate.assert_not_called()
    provider.lint.assert_not_called()
    policy.validate_naming.assert_not_called()
    policy.validate_tags.assert_not_called()
    policy.validate_security.assert_not_called()


@pytest.mark.asyncio
async def test_run_custom_path_maps_policy_severity_to_supported_values() -> None:
    llm = Mock()
    llm.complete_with_tools = AsyncMock(
        return_value=LLMResponse(
            content='```json\n{"files":[{"path":"infra/main.bicep","content":"resource x"}]}\n```'
        )
    )
    llm.complete = AsyncMock(return_value=LLMResponse(content="graph TD\nA-->B"))

    policy = Mock()
    policy.validate_naming = AsyncMock(
        return_value=PolicyResult(
            passed=False,
            violations=[
                PolicyViolation(
                    resource="vnet1",
                    policy="naming",
                    severity="high",
                    expected="env-project-vnet",
                    actual="badname",
                    remediation="Fix naming",
                )
            ],
        )
    )
    policy.validate_tags = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))
    policy.validate_security = AsyncMock(return_value=PolicyResult(passed=True, violations=[]))

    provider = Mock()
    provider.format_check = AsyncMock(return_value=ValidationResult(valid=True))
    provider.validate = AsyncMock(return_value=ValidationResult(valid=True))
    provider.lint = AsyncMock(return_value=ValidationResult(valid=True))

    templates = Mock()
    obs = Mock()
    obs.start_span = Mock(return_value=None)
    obs.record_metric = Mock(return_value=None)
    obs.log = Mock(return_value=None)

    use_case = GenerateUseCase(
        llm=llm,
        policy=policy,
        templates=templates,
        infra_providers={"bicep": provider},
        observability=obs,
    )

    result = await use_case.run_custom_path(
        requirements="create a vnet",
        language=IaCLanguage.BICEP,
        conversation_history=[],
        mcp_tool_executor=Mock(return_value={}),
    )

    assert result.iteration_count == 3
    assert any(v["checker"] == "standards" and v["severity"] == "error" for v in result.violations)
