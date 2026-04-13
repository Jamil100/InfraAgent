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

    @pytest.mark.asyncio
    async def test_lint_non_diagnostic_failure_is_error(self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"fatal: lint crashed"))
            mock_subprocess.return_value = mock_proc

            result = await adapter.lint(sample_files)
            assert result.valid is False
            assert any("lint crashed" in err for err in result.errors)


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
    async def test_plan_parses_stdout_json_when_stderr_present(
        self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]
    ) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(
                return_value=(
                    json.dumps({"changes": [{"changeType": "Create"}, {"changeType": "Delete"}]}).encode(),
                    b"warning from stderr",
                )
            )
            mock_subprocess.return_value = mock_proc

            result = await adapter.plan(sample_files, {"resource_group": "rg-test"})
            assert result.success is True
            assert result.resources_to_create == 1
            assert result.resources_to_destroy == 1
            assert "warning from stderr" in result.output

    @pytest.mark.asyncio
    async def test_plan_accepts_deployment_name_camel_case(
        self, adapter: BicepInfraProviderAdapter, sample_files: list[dict]
    ) -> None:
        with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = mock.AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = mock.AsyncMock(return_value=(json.dumps({"changes": []}).encode(), b""))
            mock_subprocess.return_value = mock_proc

            result = await adapter.plan(sample_files, {"resource_group": "rg-test", "deploymentName": "dep-camel"})
            assert result.success is True
            stored = next(iter(adapter._plan_storage.values()))
            assert stored["deployment_name"] == "dep-camel"

    @pytest.mark.asyncio
    async def test_apply_uses_group_create(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "bicep_plan_success"
            work_dir.mkdir()
            adapter._plan_storage["plan-1"] = {
                "resource_group": "rg-test",
                "deployment_name": "dep-test",
                "template_file": "/tmp/main.bicep",
                "parameters_file": None,
                "work_dir": str(work_dir),
            }

            with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_proc = mock.AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = mock.AsyncMock(return_value=(b'{"properties":{}}', b""))
                mock_subprocess.return_value = mock_proc

                result = await adapter.apply("plan-1")

                assert result.success is True
                assert "plan-1" not in adapter._plan_storage
                assert not work_dir.exists()
                assert result.resources_created == []
                args = mock_subprocess.call_args.args
                assert list(args[:4]) == ["az", "deployment", "group", "create"]

    @pytest.mark.asyncio
    async def test_apply_invalid_plan_context(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "bicep_plan_invalid"
            work_dir.mkdir()
            adapter._plan_storage["plan-2"] = {
                "resource_group": None,
                "deployment_name": "dep-test",
                "template_file": "/tmp/main.bicep",
                "parameters_file": None,
                "work_dir": str(work_dir),
            }

            result = await adapter.apply("plan-2")
            assert result.success is False
            assert "missing required deployment fields" in result.errors[0]
            assert "plan-2" not in adapter._plan_storage
            assert not work_dir.exists()

    @pytest.mark.asyncio
    async def test_apply_failure_cleans_up_storage_and_directory(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "bicep_plan_failure"
            work_dir.mkdir()
            adapter._plan_storage["plan-3"] = {
                "resource_group": "rg-test",
                "deployment_name": "dep-test",
                "template_file": "/tmp/main.bicep",
                "parameters_file": None,
                "work_dir": str(work_dir),
            }

            with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_proc = mock.AsyncMock()
                mock_proc.returncode = 1
                mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"apply failed"))
                mock_subprocess.return_value = mock_proc

                result = await adapter.apply("plan-3")

            assert result.success is False
            assert "plan-3" not in adapter._plan_storage
            assert not work_dir.exists()

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

    def test_write_files_rejects_unsafe_paths(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            with pytest.raises(ValueError):
                adapter._write_files([{"path": "../escape.bicep", "content": "x"}], tmpdir)
            with pytest.raises(ValueError):
                adapter._write_files([{"path": "/etc/passwd", "content": "x"}], tmpdir)

    @pytest.mark.asyncio
    async def test_apply_parses_created_resources_from_stdout(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "bicep_plan_apply_parse"
            work_dir.mkdir()
            adapter._plan_storage["plan-4"] = {
                "resource_group": "rg-test",
                "deployment_name": "dep-test",
                "template_file": "/tmp/main.bicep",
                "parameters_file": None,
                "work_dir": str(work_dir),
            }

            with mock.patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_proc = mock.AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = mock.AsyncMock(
                    return_value=(
                        json.dumps(
                            {
                                "properties": {
                                    "outputs": {"createdResources": {"value": ["res-a", "res-b"]}}
                                }
                            }
                        ).encode(),
                        b"warning from stderr",
                    )
                )
                mock_subprocess.return_value = mock_proc

                result = await adapter.apply("plan-4")

            assert result.success is True
            assert result.resources_created == ["res-a", "res-b"]

    def test_cleanup_work_dir_skips_non_prefixed_paths(self, adapter: BicepInfraProviderAdapter) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "unsafe_dir_name"
            work_dir.mkdir()

            adapter._cleanup_work_dir(str(work_dir))

            assert work_dir.exists()
