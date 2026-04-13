"""Bicep CLI adapter implementing IInfraProviderPort."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from src.application.ports.ports import (
    ApplyResult,
    IInfraProviderPort,
    PlanResult,
    ValidationResult,
)


logger = logging.getLogger(__name__)

_BICEP_CODE_RE = re.compile(r"\b(?P<level>Error|Warning)\s+(?P<code>BCP\d{3})\b", re.IGNORECASE)
_BICEP_ANY_CODE_RE = re.compile(r"\bBCP\d{3}\b", re.IGNORECASE)
_ERROR_WORD_RE = re.compile(r"\berror\b", re.IGNORECASE)
_WARN_WORD_RE = re.compile(r"\bwarning\b|\bwarn\b", re.IGNORECASE)
_IGNORED_LINT_CODES = {"BCP081", "BCP187"}
_REQUIRED_LINT_CODES = {"BCP035"}


class BicepInfraProviderAdapter(IInfraProviderPort):
    """Bicep implementation of infrastructure provider operations."""

    def __init__(self) -> None:
        self.logger = logger
        self._plan_storage: dict[str, dict[str, str | None]] = {}

    async def format_check(self, files: list[dict]) -> ValidationResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                bicep_files = self._write_files(files, tmp)
            except ValueError as exc:
                return ValidationResult(valid=False, errors=[str(exc)])

            errors: list[str] = []
            for bicep_file in bicep_files:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "bicep",
                        "format",
                        "--verify",
                        str(bicep_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                except FileNotFoundError:
                    return ValidationResult(valid=True, warnings=["Bicep CLI not installed; format check skipped"])

                if proc.returncode != 0:
                    output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
                    normalized_output = output.lower()
                    if "unrecognized" in normalized_output and "verify" in normalized_output:
                        fallback = await self._format_verify_via_stdout(bicep_file)
                        if fallback is None:
                            continue
                        errors.append(fallback)
                        continue
                    errors.append(output or f"Format check failed for {bicep_file.name}")

            return ValidationResult(valid=not errors, errors=errors)

    async def validate(self, files: list[dict]) -> ValidationResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                bicep_files = self._write_files(files, tmp)
            except ValueError as exc:
                return ValidationResult(valid=False, errors=[str(exc)])

            errors: list[str] = []
            for bicep_file in bicep_files:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "bicep",
                        "build",
                        "--stdout",
                        "--no-restore",
                        str(bicep_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await proc.communicate()
                except FileNotFoundError:
                    return ValidationResult(valid=False, errors=["Bicep CLI not installed"])

                if proc.returncode != 0:
                    output = stderr.decode(errors="replace").strip()
                    errors.append(output or f"Build failed for {bicep_file.name}")

            return ValidationResult(valid=not errors, errors=errors)

    async def lint(self, files: list[dict]) -> ValidationResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                bicep_files = self._write_files(files, tmp)
            except ValueError as exc:
                return ValidationResult(valid=False, errors=[str(exc)])

            errors: list[str] = []
            warnings: list[str] = []
            for bicep_file in bicep_files:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "bicep",
                        "lint",
                        "--no-restore",
                        str(bicep_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                except FileNotFoundError:
                    return ValidationResult(valid=True, warnings=["Bicep CLI not installed; lint skipped"])

                output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
                file_errors, file_warnings = self._triage_lint_output(output)
                errors.extend(file_errors)
                warnings.extend(file_warnings)
                if (
                    proc.returncode != 0
                    and not file_errors
                    and not file_warnings
                    and not _BICEP_ANY_CODE_RE.search(output)
                ):
                    errors.append(output or f"Bicep lint failed for {bicep_file.name}")

            return ValidationResult(valid=not errors, errors=errors, warnings=warnings)

    async def plan(self, files: list[dict], variables: dict) -> PlanResult:
        resource_group = (variables.get("resource_group") or variables.get("resourceGroup") or "").strip()
        if not resource_group:
            return PlanResult(
                success=False,
                output="Missing required variable: resource_group",
                resources_to_create=0,
                resources_to_modify=0,
                resources_to_destroy=0,
            )

        plan_id = str(uuid.uuid4())
        tmpdir = Path(tempfile.mkdtemp(prefix=f"bicep_plan_{plan_id}_"))
        persisted_plan = False

        try:
            bicep_files = self._write_files(files, tmpdir)
            template_file = self._select_template_file(bicep_files, variables)
            if template_file is None:
                return PlanResult(
                    success=False,
                    output="No Bicep template file found",
                    resources_to_create=0,
                    resources_to_modify=0,
                    resources_to_destroy=0,
                )

            deployment_name = (
                variables.get("deployment_name")
                or variables.get("deploymentName")
                or f"infraagent-{plan_id}"
            ).strip()
            params_path = self._write_parameters_file(variables, tmpdir)

            command = [
                "az",
                "deployment",
                "group",
                "what-if",
                "--resource-group",
                resource_group,
                "--name",
                deployment_name,
                "--template-file",
                str(template_file),
                "--output",
                "json",
            ]
            if params_path:
                command.extend(["--parameters", f"@{params_path}"])

            try:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=str(tmpdir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                return PlanResult(
                    success=False,
                    output="Azure CLI not installed",
                    resources_to_create=0,
                    resources_to_modify=0,
                    resources_to_destroy=0,
                )

            stdout_output = stdout.decode(errors="replace").strip()
            stderr_output = stderr.decode(errors="replace").strip()
            output = "\n".join(part for part in (stdout_output, stderr_output) if part)
            create_count, modify_count, destroy_count = self._parse_what_if_output(stdout_output)
            success = proc.returncode == 0

            if success:
                self._plan_storage[plan_id] = {
                    "resource_group": resource_group,
                    "deployment_name": deployment_name,
                    "template_file": str(template_file),
                    "parameters_file": str(params_path) if params_path else None,
                    "work_dir": str(tmpdir),
                }
                self.logger.debug("Stored bicep plan %s in %s", plan_id, tmpdir)
                persisted_plan = True

            return PlanResult(
                success=success,
                output=output,
                resources_to_create=create_count,
                resources_to_modify=modify_count,
                resources_to_destroy=destroy_count,
            )
        except Exception as exc:
            self.logger.error("Bicep plan failed: %s", exc)
            return PlanResult(
                success=False,
                output=str(exc),
                resources_to_create=0,
                resources_to_modify=0,
                resources_to_destroy=0,
            )
        finally:
            if not persisted_plan and tmpdir.exists():
                try:
                    shutil.rmtree(tmpdir)
                except OSError as exc:
                    self.logger.warning("Failed to clean up plan directory %s: %s", tmpdir, exc)

    async def apply(self, plan_id: str) -> ApplyResult:
        plan_context = self._plan_storage.get(plan_id)
        if not plan_context:
            return ApplyResult(
                success=False,
                output="Plan not found",
                errors=[f"Plan ID {plan_id} not found in storage"],
            )

        work_dir = plan_context.get("work_dir")
        template_file = plan_context.get("template_file")
        resource_group = plan_context.get("resource_group")
        deployment_name = plan_context.get("deployment_name")
        params_file = plan_context.get("parameters_file")

        try:
            if not resource_group or not deployment_name or not template_file:
                return ApplyResult(
                    success=False,
                    output="Invalid plan context",
                    errors=["Plan context is missing required deployment fields"],
                )

            command = [
                "az",
                "deployment",
                "group",
                "create",
                "--resource-group",
                resource_group,
                "--name",
                deployment_name,
                "--template-file",
                template_file,
                "--output",
                "json",
            ]
            if params_file:
                command.extend(["--parameters", f"@{params_file}"])

            try:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=work_dir or None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                return ApplyResult(
                    success=False,
                    output="Azure CLI not installed",
                    errors=["Azure CLI not installed"],
                )

            stdout_output = stdout.decode(errors="replace").strip()
            stderr_output = stderr.decode(errors="replace").strip()
            output = "\n".join(part for part in (stdout_output, stderr_output) if part)
            resources_created = self._parse_created_resources(stdout_output) if proc.returncode == 0 else []
            return ApplyResult(
                success=proc.returncode == 0,
                output=output,
                resources_created=resources_created,
                errors=[] if proc.returncode == 0 else [output],
            )
        finally:
            self._plan_storage.pop(plan_id, None)
            self._cleanup_work_dir(work_dir)

    def get_language(self) -> str:
        return "bicep"

    def _write_files(self, files: list[dict], base_dir: Path) -> list[Path]:
        base_resolved = base_dir.resolve()
        bicep_files: list[Path] = []
        for file_dict in files:
            path = file_dict.get("path", "")
            content = file_dict.get("content", "")
            if not path:
                continue

            requested_path = Path(path)
            if requested_path.is_absolute():
                raise ValueError(f"Absolute paths are not allowed: {path}")

            destination = (base_dir / requested_path).resolve()
            try:
                destination.relative_to(base_resolved)
            except ValueError as exc:
                raise ValueError(f"Path escapes workspace: {path}") from exc

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            if destination.suffix == ".bicep":
                bicep_files.append(destination)
        return bicep_files

    def _triage_lint_output(self, output: str) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        for line in output.splitlines():
            normalized = line.strip()
            if not normalized:
                continue

            match = _BICEP_CODE_RE.search(line)
            if not match:
                if _ERROR_WORD_RE.search(normalized):
                    errors.append(normalized)
                elif _WARN_WORD_RE.search(normalized):
                    warnings.append(normalized)
                continue

            code = match.group("code").upper()
            level = match.group("level").lower()
            if code in _IGNORED_LINT_CODES:
                continue
            if code in _REQUIRED_LINT_CODES or level == "error":
                errors.append(normalized)
            else:
                warnings.append(normalized)

        return errors, warnings

    async def _format_verify_via_stdout(self, bicep_file: Path) -> str | None:
        """Compatibility fallback for older bicep CLIs without --verify."""
        proc = await asyncio.create_subprocess_exec(
            "bicep",
            "format",
            "--stdout",
            str(bicep_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
            return output or f"Format check failed for {bicep_file.name}"

        current = bicep_file.read_text(encoding="utf-8")
        formatted = stdout.decode(errors="replace")
        if current != formatted:
            return f"Format check failed for {bicep_file.name}"
        return None

    def _select_template_file(self, bicep_files: list[Path], variables: dict[str, Any]) -> Path | None:
        requested = variables.get("template_file") or variables.get("templateFile")
        if isinstance(requested, str) and requested:
            return Path(requested)

        for path in bicep_files:
            if path.name == "main.bicep":
                return path
        return bicep_files[0] if bicep_files else None

    def _write_parameters_file(self, variables: dict, tmpdir: Path) -> Path | None:
        explicit = variables.get("parameters")
        params: dict[str, Any]
        if isinstance(explicit, dict):
            params = explicit
        else:
            control_keys = {
                "resource_group",
                "resourceGroup",
                "deployment_name",
                "deploymentName",
                "template_file",
                "templateFile",
            }
            params = {k: v for k, v in variables.items() if k not in control_keys}

        if not params:
            return None

        az_params = {
            "parameters": {
                key: value if isinstance(value, dict) and "value" in value else {"value": value}
                for key, value in params.items()
            }
        }
        params_file = tmpdir / "parameters.json"
        params_file.write_text(json.dumps(az_params), encoding="utf-8")
        return params_file

    def _parse_what_if_output(self, output: str) -> tuple[int, int, int]:
        create_count = 0
        modify_count = 0
        destroy_count = 0

        try:
            data = json.loads(output) if output else {}
        except json.JSONDecodeError:
            return 0, 0, 0

        changes = data.get("changes", [])
        for change in changes:
            change_type = str(change.get("changeType") or "").lower()
            if change_type == "create":
                create_count += 1
            # Azure what-if reports in-place updates as "Modify".
            elif change_type == "modify":
                modify_count += 1
            elif change_type == "delete":
                destroy_count += 1

        return create_count, modify_count, destroy_count

    def _parse_created_resources(self, output: str) -> list[str]:
        try:
            data = json.loads(output) if output else {}
        except json.JSONDecodeError:
            return []

        properties = data.get("properties", {})
        outputs = properties.get("outputs", {})
        resources = outputs.get("createdResources", {})
        value = resources.get("value") if isinstance(resources, dict) else None
        if value is None:
            self.logger.debug("No createdResources output found in deployment response")
        return value if isinstance(value, list) else []

    def _cleanup_work_dir(self, work_dir: str | None) -> None:
        if not work_dir:
            return

        work_path = Path(work_dir)
        if not work_path.exists():
            return

        temp_root = Path(tempfile.gettempdir()).resolve()
        resolved_work_path = work_path.resolve()
        in_temp_root = resolved_work_path.parent == temp_root or temp_root in resolved_work_path.parents
        if not resolved_work_path.name.startswith("bicep_plan_") or not in_temp_root:
            self.logger.warning("Skipping unsafe cleanup path: %s", resolved_work_path)
            return

        try:
            shutil.rmtree(resolved_work_path)
        except OSError as exc:
            self.logger.warning("Failed to clean up plan directory %s: %s", resolved_work_path, exc)
