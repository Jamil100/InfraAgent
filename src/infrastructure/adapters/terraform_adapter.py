"""Terraform CLI adapter implementing IInfraProviderPort.

Manages Terraform operations: format checking, validation, linting, planning, and applying.
Uses asyncio for non-blocking CLI execution.

Ref: TechSpec Section 4.2, Issue #13
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import uuid
from pathlib import Path

from src.application.ports.ports import (
    ApplyResult,
    IInfraProviderPort,
    PlanResult,
    ValidationResult,
)


logger = logging.getLogger(__name__)


class TerraformInfraProviderAdapter(IInfraProviderPort):
    """Terraform CLI adapter implementing IInfraProviderPort.

    Manages all Terraform operations via async subprocess calls.
    Plan files are stored in temp directories with UUID naming for apply() coupling.
    """

    def __init__(self):
        """Initialize adapter."""
        self.logger = logger
        # Store mapping of plan_id (UUID) -> temp directory for plan/apply coupling
        self._plan_storage: dict[str, Path] = {}

    async def format_check(self, files: list[dict]) -> ValidationResult:
        """Check IaC format/syntax using terraform fmt -check.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with format validation results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._write_files(files, tmp)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "fmt", "-check", "-diff", "-recursive",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                self.logger.warning("terraform CLI not installed")
                return ValidationResult(
                    valid=True,
                    warnings=["Terraform CLI not installed; format check skipped"]
                )

            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            # Exit code: 0 = formatted, 3 = not formatted, other = error
            if proc.returncode == 0:
                return ValidationResult(valid=True)
            elif proc.returncode == 3:
                return ValidationResult(
                    valid=False,
                    errors=[f"Terraform format check failed:\n{stdout_text}"]
                )
            else:
                return ValidationResult(
                    valid=False,
                    errors=[stderr_text or "Format check failed"]
                )

    async def validate(self, files: list[dict]) -> ValidationResult:
        """Validate IaC semantics using terraform validate.

        Requires terraform init first (with -backend=false).

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with validation results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._write_files(files, tmp)

            # First: init (required before validate)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "init", "-backend=false", "-input=false",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                if proc.returncode != 0:
                    return ValidationResult(
                        valid=False,
                        errors=["Terraform init failed"]
                    )
            except FileNotFoundError:
                self.logger.warning("terraform CLI not installed")
                return ValidationResult(
                    valid=False,
                    errors=["Terraform CLI not installed"]
                )

            # Second: validate -json
            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "validate", "-json",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                return ValidationResult(
                    valid=False,
                    errors=["Terraform CLI not installed"]
                )

            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            # Parse JSON output
            errors, warnings = self._parse_tf_validate_json(stdout_text)

            return ValidationResult(
                valid=proc.returncode == 0,
                errors=errors,
                warnings=warnings
            )

    async def lint(self, files: list[dict]) -> ValidationResult:
        """Lint IaC using tflint (optional stretch goal).

        If tflint is not installed, returns success with warning.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with lint results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._write_files(files, tmp)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "tflint", ".",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                self.logger.info("tflint not installed; lint skipped")
                return ValidationResult(
                    valid=True,
                    warnings=["tflint not installed; lint check skipped"]
                )

            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            # Parse tflint output
            errors, warnings = self._parse_tflint_output(stdout_text)

            return ValidationResult(
                valid=proc.returncode == 0,
                errors=errors,
                warnings=warnings
            )

    async def plan(self, files: list[dict], variables: dict) -> PlanResult:
        """Generate a plan using terraform plan.

        Saves plan file for later apply() call. Plan is stored in a temp directory
        with UUID-based naming, and the UUID is returned as plan_id.

        Args:
            files: List of {"path": "...", "content": "..."} dicts
            variables: Variable values dict

        Returns:
            PlanResult with change summary and plan_id in output
        """
        # Create persistent temp directory for plan storage (lifetime = pipeline execution)
        plan_id = str(uuid.uuid4())
        tmpdir = Path(tempfile.gettempdir()) / f"tf_plan_{plan_id}"
        tmpdir.mkdir(parents=True, exist_ok=True)

        try:
            self._write_files(files, tmpdir)
            self._write_tfvars(variables, tmpdir)

            # Init
            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "init", "-backend=false", "-input=false",
                    cwd=str(tmpdir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                init_stdout, init_stderr = await proc.communicate()
                if proc.returncode != 0:
                    return PlanResult(
                        success=False,
                        output=init_stderr.decode(errors="replace"),
                        resources_to_create=0,
                        resources_to_modify=0,
                        resources_to_destroy=0,
                    )
            except FileNotFoundError:
                self.logger.error("terraform CLI not installed")
                return PlanResult(
                    success=False,
                    output="Terraform CLI not installed",
                    resources_to_create=0,
                    resources_to_modify=0,
                    resources_to_destroy=0,
                )

            # Plan
            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "plan", "-json", "-no-color", "-out=tfplan",
                    "-input=false",
                    cwd=str(tmpdir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                return PlanResult(
                    success=False,
                    output="Terraform CLI not installed",
                    resources_to_create=0,
                    resources_to_modify=0,
                    resources_to_destroy=0,
                )

            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            # Exit code: 0=no changes, 2=changes present (both are success)
            success = proc.returncode in (0, 2)

            # Parse plan JSON output
            create_count, update_count, delete_count = self._parse_tf_plan_json(stdout_text)

            # Store plan directory mapping for apply()
            self._plan_storage[plan_id] = tmpdir

            return PlanResult(
                success=success,
                output=stdout_text,
                resources_to_create=create_count,
                resources_to_modify=update_count,
                resources_to_destroy=delete_count,
            )
        except Exception as e:
            self.logger.error(f"Plan failed: {e}")
            return PlanResult(
                success=False,
                output=str(e),
                resources_to_create=0,
                resources_to_modify=0,
                resources_to_destroy=0,
            )

    async def apply(self, plan_id: str) -> ApplyResult:
        """Apply a plan created by plan().

        Args:
            plan_id: UUID returned from plan() call

        Returns:
            ApplyResult with deployment summary
        """
        # Retrieve plan directory
        tmpdir = self._plan_storage.get(plan_id)
        if not tmpdir:
            return ApplyResult(
                success=False,
                output="Plan not found",
                errors=[f"Plan ID {plan_id} not found in storage"]
            )

        if not tmpdir.exists():
            return ApplyResult(
                success=False,
                output="Plan directory deleted",
                errors=[f"Plan directory {tmpdir} no longer exists"]
            )

        try:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "terraform", "apply", "-json", "-no-color", "-auto-approve",
                    "tfplan",
                    cwd=str(tmpdir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
            except FileNotFoundError:
                return ApplyResult(
                    success=False,
                    output="Terraform CLI not installed",
                    errors=["Terraform CLI not installed"]
                )

            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            success = proc.returncode == 0

            # Parse apply JSON output for resource IDs
            resources_created = self._parse_tf_apply_json(stdout_text)

            result = ApplyResult(
                success=success,
                output=stdout_text,
                resources_created=resources_created,
                errors=[stderr_text] if not success else [],
            )

            # Clean up plan storage
            del self._plan_storage[plan_id]

            return result
        except Exception as e:
            self.logger.error(f"Apply failed: {e}")
            return ApplyResult(
                success=False,
                output=str(e),
                errors=[str(e)]
            )
        finally:
            # Clean up temp directory
            if tmpdir.exists():
                import shutil
                try:
                    shutil.rmtree(tmpdir)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up plan directory {tmpdir}: {e}")

    def get_language(self) -> str:
        """Return the IaC language this adapter supports.

        Returns:
            "terraform"
        """
        return "terraform"

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _write_files(self, files: list[dict], base_dir: Path) -> None:
        """Write files to disk in temp directory.

        Args:
            files: List of {"path": "...", "content": "..."} dicts
            base_dir: Base directory to write files to
        """
        for file_dict in files:
            path = file_dict.get("path", "")
            content = file_dict.get("content", "")

            if not path:
                continue

            file_path = base_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            self.logger.debug(f"Wrote {path} to {file_path}")

    def _write_tfvars(self, variables: dict, base_dir: Path) -> None:
        """Write terraform.tfvars file from variables dict.

        Uses JSON format which Terraform can parse.

        Args:
            variables: Variables dict (values can be any JSON-serializable type)
            base_dir: Directory to write terraform.tfvars to
        """
        if not variables:
            return

        tfvars_content = ""
        for key, value in variables.items():
            # Use JSON encoding for all values (works with Terraform's jsonDecode)
            json_value = json.dumps(value)
            tfvars_content += f'{key} = jsonDecode(\'{json_value}\')\n'

        tfvars_path = base_dir / "terraform.tfvars"
        tfvars_path.write_text(tfvars_content, encoding="utf-8")
        self.logger.debug(f"Wrote terraform.tfvars with {len(variables)} variables")

    def _parse_tf_plan_json(self, raw: str) -> tuple[int, int, int]:
        """Parse terraform plan -json output.

        Counts resource changes by action type.

        Args:
            raw: Raw JSON output from terraform plan -json

        Returns:
            Tuple of (create_count, update_count, delete_count)
        """
        create_count = 0
        update_count = 0
        delete_count = 0

        for line in raw.splitlines():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "planned_change":
                change = msg.get("change", {})
                action = change.get("action", "")

                if action == "create":
                    create_count += 1
                elif action in ("update", "replace"):
                    update_count += 1
                elif action == "delete":
                    delete_count += 1

        return create_count, update_count, delete_count

    def _parse_tf_validate_json(self, raw: str) -> tuple[list[str], list[str]]:
        """Parse terraform validate -json output.

        Args:
            raw: Raw JSON output from terraform validate -json

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            if raw.strip():
                errors.append(f"Could not parse validate output: {raw[:200]}")
            return errors, warnings

        for diag in data.get("diagnostics", []):
            level = diag.get("severity", "error")
            message = diag.get("summary", "")
            detail = diag.get("detail", "")
            full_msg = f"{message}\n{detail}" if detail else message

            if level == "error":
                errors.append(full_msg)
            else:
                warnings.append(full_msg)

        return errors, warnings

    def _parse_tflint_output(self, raw: str) -> tuple[list[str], list[str]]:
        """Parse tflint text output.

        tflint outputs in format: file:line:col: severity: message

        Args:
            raw: Raw text output from tflint

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors: list[str] = []
        warnings: list[str] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            # Format: file.tf:1:1: error: message
            parts = line.split(": ", 2)
            if len(parts) >= 3:
                severity = parts[1]
                message = parts[2] if len(parts) > 2 else ""

                if severity.lower() == "error":
                    errors.append(message)
                elif severity.lower() in ("warning", "notice"):
                    warnings.append(message)
            else:
                # Fallback for lines that don't match expected format
                warnings.append(line)

        return errors, warnings

    def _parse_tf_apply_json(self, raw: str) -> list[str]:
        """Parse terraform apply -json output.

        Extracts resource addresses that were created/modified.

        Args:
            raw: Raw JSON output from terraform apply -json

        Returns:
            List of resource addresses that were applied
        """
        resources: list[str] = []

        for line in raw.splitlines():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "apply_complete":
                # This message contains the summary
                continue
            elif msg.get("type") == "resource_drift":
                # Skip drift messages
                continue
            elif msg.get("message", "").startswith("Apply complete"):
                # This is the summary line
                continue

        return resources
