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

    @pytest.mark.asyncio
    async def test_format_check_failure(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"format failed"))
            mock_subprocess.return_value = mock_proc

            result = await adapter.format_check(sample_files)

            assert result.valid is False
            assert "format failed" in result.errors[0]


class TestValidate:
    @pytest.mark.asyncio
    async def test_validate_success(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(return_value=(b"{}", b""))
            mock_subprocess.return_value = mock_proc

            result = await adapter.validate(sample_files)

            assert result.valid is True
            assert result.errors == []

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

    @pytest.mark.asyncio
    async def test_lint_reads_stdout_and_stderr(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = mock.AsyncMock(
                return_value=(
                    b"main.bicep(1,1) : Error BCP035: from stdout",
                    b"main.bicep(2,1) : Warning BCP081: ignored",
                )
            )
            mock_subprocess.return_value = mock_proc

            result = await adapter.lint(sample_files)
            assert result.valid is False
            assert any("from stdout" in err for err in result.errors)


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
            assert "plan-1" not in adapter._plan_storage
            args = mock_subprocess.call_args.args
            assert list(args[:4]) == ["az", "deployment", "group", "create"]

    @pytest.mark.asyncio
    async def test_apply_invalid_plan_context(self, adapter: BicepInfraProviderAdapter) -> None:
        adapter._plan_storage["plan-2"] = {
            "resource_group": None,
            "deployment_name": "dep-test",
            "template_file": "/tmp/main.bicep",
            "parameters_file": None,
            "work_dir": "/tmp",
        }

        result = await adapter.apply("plan-2")
        assert result.success is False
        assert "missing required deployment fields" in result.errors[0]

    @pytest.mark.asyncio
    async def test_plan_cleans_tempdir_on_failure(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as root_tmp:
            fixed_tmp = Path(root_tmp) / "fixed-plan-dir"
            fixed_tmp.mkdir()

            with mock.patch("tempfile.mkdtemp", return_value=str(fixed_tmp)):
                with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
                    mock_proc = mock.AsyncMock()
                    mock_proc.returncode = 1
                    mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"plan failed"))
                    mock_subprocess.return_value = mock_proc

                    result = await adapter.plan(sample_files, {"resource_group": "rg-test"})

                    assert result.success is False
                    assert not fixed_tmp.exists()


class TestGetLanguage:
    def test_get_language(self, adapter: BicepInfraProviderAdapter) -> None:
        assert adapter.get_language() == "bicep"


class TestHelperMethods:
    def test_select_template_file_prefers_explicit_and_fallbacks(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path

        files = [Path("/tmp/other.bicep"), Path("/tmp/main.bicep")]
        assert adapter._select_template_file(files, {"template_file": "/tmp/custom.bicep"}) == Path("/tmp/custom.bicep")
        assert adapter._select_template_file(files, {"templateFile": "/tmp/custom2.bicep"}) == Path("/tmp/custom2.bicep")
        assert adapter._select_template_file(files, {}) == Path("/tmp/main.bicep")
        assert adapter._select_template_file([Path("/tmp/first.bicep")], {}) == Path("/tmp/first.bicep")

    def test_write_parameters_file_paths(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            assert adapter._write_parameters_file({}, tmpdir) is None

            explicit = adapter._write_parameters_file({"parameters": {"x": {"value": "y"}}}, tmpdir)
            assert explicit is not None
            explicit_data = json.loads(explicit.read_text(encoding="utf-8"))
            assert explicit_data["parameters"]["x"]["value"] == "y"

            filtered = adapter._write_parameters_file(
                {"resource_group": "rg", "deploymentName": "dep", "project": "demo"},
                tmpdir,
            )
            assert filtered is not None
            filtered_data = json.loads(filtered.read_text(encoding="utf-8"))
            assert "resource_group" not in filtered_data["parameters"]
            assert "deploymentName" not in filtered_data["parameters"]
            assert filtered_data["parameters"]["project"]["value"] == "demo"
