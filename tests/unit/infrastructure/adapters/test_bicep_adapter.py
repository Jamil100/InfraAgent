"""Unit tests for BicepInfraProviderAdapter."""

from __future__ import annotations

import json
from unittest import mock

import pytest

from src.infrastructure.adapters.bicep_adapter import BicepInfraProviderAdapter


@pytest.fixture
def adapter() -> BicepInfraProviderAdapter:
    return BicepInfraProviderAdapter()


@pytest.fixture
def sample_files() -> list[dict]:
    return [
        {"path": "main.bicep", "content": "targetScope = 'resourceGroup'\n"},
    ]


class TestFormatCheck:
    @pytest.mark.asyncio
    async def test_format_check_success(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_proc

            result = await adapter.format_check(sample_files)

            assert result.valid is True
            assert result.errors == []
            assert result.warnings == []
            args = mock_subprocess.call_args.args
            assert list(args[:3]) == ["bicep", "format", "--verify"]


class TestValidate:
    @pytest.mark.asyncio
    async def test_validate_failure(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"build failed"))
            mock_subprocess.return_value = mock_proc

            result = await adapter.validate(sample_files)

            assert result.valid is False
            assert result.errors
            args = mock_subprocess.call_args.args
            assert list(args[:4]) == ["bicep", "build", "--stdout", "--no-restore"]


class TestLint:
    @pytest.mark.asyncio
    async def test_lint_ignores_configured_codes(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            output = "\n".join(
                [
                    "main.bicep(1,1) : Warning BCP081: ignored",
                    "main.bicep(2,1) : Warning BCP187: ignored",
                ]
            )
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", output.encode()))
            mock_subprocess.return_value = mock_proc

            result = await adapter.lint(sample_files)

            assert result.valid is True
            assert result.errors == []

    @pytest.mark.asyncio
    async def test_lint_reports_bcp035(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            output = "main.bicep(2,1) : Error BCP035: required property missing"
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", output.encode()))
            mock_subprocess.return_value = mock_proc

            result = await adapter.lint(sample_files)

            assert result.valid is False
            assert any("BCP035" in err for err in result.errors)


class TestPlanApply:
    @pytest.mark.asyncio
    async def test_plan_uses_what_if(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(
                return_value=(
                    json.dumps({"changes": [{"changeType": "Create"}, {"changeType": "Modify"}]}).encode(),
                    b"",
                )
            )
            mock_subprocess.return_value = mock_proc

            result = await adapter.plan(sample_files, {"resource_group": "rg-test", "deployment_name": "dep-test"})

            assert result.success is True
            assert result.resources_to_create == 1
            assert result.resources_to_modify == 1
            args = mock_subprocess.call_args.args
            assert list(args[:4]) == ["az", "deployment", "group", "what-if"]
            assert len(adapter._plan_storage) == 1
            stored = next(iter(adapter._plan_storage.values()))
            assert stored["resource_group"] == "rg-test"
            assert stored["deployment_name"] == "dep-test"
            assert stored["template_file"] is not None
            assert stored["work_dir"] is not None

    @pytest.mark.asyncio
    async def test_apply_uses_group_create(self, adapter: BicepInfraProviderAdapter) -> None:
        adapter._plan_storage["plan-1"] = {
            "resource_group": "rg-test",
            "deployment_name": "dep-test",
            "template_file": "/tmp/main.bicep",
            "parameters_file": None,
            "work_dir": "/tmp",
        }

        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(return_value=(b'{"properties":{}}', b""))
            mock_subprocess.return_value = mock_proc

            result = await adapter.apply("plan-1")

            assert result.success is True
            args = mock_subprocess.call_args.args
            assert list(args[:4]) == ["az", "deployment", "group", "create"]


class TestGetLanguage:
    def test_get_language(self, adapter: BicepInfraProviderAdapter) -> None:
        assert adapter.get_language() == "bicep"
