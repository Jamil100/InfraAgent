"""Deploy adapter — runs bicep what-if / terraform plan and apply via CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path

from src.domain.models.models import GeneratedFile, IaCLanguage, PlanResult
from src.application.ports.ports import IDeployPort

logger = logging.getLogger(__name__)


def make_deploy_adapter(
    iac_language: IaCLanguage,
    *,
    resource_group: str = "",
    subscription_id: str = "",
    location: str = "westeurope",
) -> IDeployPort:
    """Factory — returns the right adapter for the requested IaC language."""
    if iac_language == IaCLanguage.TERRAFORM:
        return TerraformDeployAdapter()
    return BicepDeployAdapter(
        resource_group=resource_group,
        subscription_id=subscription_id,
        location=location,
    )


# ---------------------------------------------------------------------------
# Bicep adapter (az deployment group what-if / create)
# ---------------------------------------------------------------------------


class BicepDeployAdapter(IDeployPort):
    """Runs `az deployment group what-if` and `az deployment group create`."""

    def __init__(
        self,
        *,
        resource_group: str = "",
        subscription_id: str = "",
        location: str = "westeurope",
    ) -> None:
        self._rg = resource_group
        self._sub = subscription_id
        self._location = location

    async def plan(self, files: list[GeneratedFile]) -> PlanResult:
        main_file = _find_main_bicep(files)
        if not main_file:
            return PlanResult(
                success=False,
                error="No main.bicep entry point found in generated files.",
            )

        if not self._rg:
            return PlanResult(
                success=False,
                error="resource_group not configured; cannot run bicep what-if.",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for gf in files:
                dest = tmp / gf.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(gf.content, encoding="utf-8")

            template_path = tmp / main_file.path
            cmd = [
                "az", "deployment", "group", "what-if",
                "--resource-group", self._rg,
                "--template-file", str(template_path),
                "--no-prompt",
                "--output", "json",
            ]
            if self._sub:
                cmd += ["--subscription", self._sub]

            return await _run_az_cmd(cmd, "bicep-what-if")

    async def apply(self, files: list[GeneratedFile]) -> PlanResult:
        main_file = _find_main_bicep(files)
        if not main_file:
            return PlanResult(
                success=False,
                error="No main.bicep entry point found.",
            )

        if not self._rg:
            return PlanResult(
                success=False,
                error="resource_group not configured; cannot deploy.",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for gf in files:
                dest = tmp / gf.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(gf.content, encoding="utf-8")

            template_path = tmp / main_file.path
            cmd = [
                "az", "deployment", "group", "create",
                "--resource-group", self._rg,
                "--template-file", str(template_path),
                "--output", "json",
            ]
            if self._sub:
                cmd += ["--subscription", self._sub]

            return await _run_az_cmd(cmd, "bicep-deploy")


def _find_main_bicep(files: list[GeneratedFile]) -> GeneratedFile | None:
    """Return main.bicep if present, else the first .bicep file."""
    for f in files:
        if f.path.lower() == "main.bicep" or f.path.lower().endswith("/main.bicep"):
            return f
    return next((f for f in files if f.path.endswith(".bicep")), None)


async def _run_az_cmd(cmd: list[str], operation: str) -> PlanResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        return PlanResult(
            success=False,
            error="az CLI not installed. Install from https://aka.ms/installazurecliwindows",
        )

    out_text = stdout.decode(errors="replace")
    err_text = stderr.decode(errors="replace")
    success = proc.returncode == 0

    result = PlanResult(success=success, output=out_text, error=err_text if not success else "")

    # Parse what-if JSON for resource change summary
    if success and operation == "bicep-what-if":
        result = _parse_whatif_output(out_text, result)

    return result


def _parse_whatif_output(raw: str, base: PlanResult) -> PlanResult:
    try:
        data = json.loads(raw)
        changes = data.get("properties", {}).get("changes", [])
        create, update, delete = [], [], []
        for c in changes:
            resource = c.get("resourceId", "").split("/")[-1]
            change_type = c.get("changeType", "").lower()
            if change_type == "create":
                create.append(resource)
            elif change_type in ("modify", "nochange"):
                update.append(resource)
            elif change_type == "delete":
                delete.append(resource)
        return base.model_copy(
            update={
                "resources_to_create": create,
                "resources_to_update": update,
                "resources_to_delete": delete,
            }
        )
    except (json.JSONDecodeError, KeyError):
        return base


# ---------------------------------------------------------------------------
# Terraform adapter (terraform plan / apply)
# ---------------------------------------------------------------------------


class TerraformDeployAdapter(IDeployPort):
    """Runs `terraform plan` and `terraform apply`."""

    async def plan(self, files: list[GeneratedFile]) -> PlanResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for gf in files:
                dest = tmp / gf.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(gf.content, encoding="utf-8")

            if not await _tf_init(tmpdir):
                return PlanResult(
                    success=False,
                    error="terraform init failed — check provider configs.",
                )

            return await _tf_plan(tmpdir)

    async def apply(self, files: list[GeneratedFile]) -> PlanResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for gf in files:
                dest = tmp / gf.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(gf.content, encoding="utf-8")

            if not await _tf_init(tmpdir):
                return PlanResult(
                    success=False,
                    error="terraform init failed.",
                )

            return await _tf_apply(tmpdir)


async def _tf_init(cwd: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "terraform", "init", "-backend=false", "-input=false",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0
    except FileNotFoundError:
        return False


async def _tf_plan(cwd: str) -> PlanResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            "terraform", "plan", "-json", "-input=false",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        return PlanResult(
            success=False,
            error="terraform CLI not installed. See https://developer.hashicorp.com/terraform/install",
        )

    out_text = stdout.decode(errors="replace")
    err_text = stderr.decode(errors="replace")
    success = proc.returncode in (0, 2)  # 2 = changes present but no error

    result = PlanResult(success=success, output=out_text, error=err_text if not success else "")
    return _parse_tf_plan_json(out_text, result)


def _parse_tf_plan_json(raw: str, base: PlanResult) -> PlanResult:
    """Extract add/change/destroy counts from streamed JSON plan output."""
    create, update, delete = [], [], []
    for line in raw.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "planned_change":
            change = msg.get("change", {})
            action = change.get("action", "")
            addr = change.get("resource", {}).get("addr", "")
            if action == "create":
                create.append(addr)
            elif action in ("update", "replace"):
                update.append(addr)
            elif action == "delete":
                delete.append(addr)

    return base.model_copy(
        update={
            "resources_to_create": create,
            "resources_to_update": update,
            "resources_to_delete": delete,
        }
    )


async def _tf_apply(cwd: str) -> PlanResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            "terraform", "apply", "-auto-approve", "-json", "-input=false",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        return PlanResult(
            success=False,
            error="terraform CLI not installed.",
        )

    success = proc.returncode == 0
    return PlanResult(
        success=success,
        output=stdout.decode(errors="replace"),
        error=stderr.decode(errors="replace") if not success else "",
    )
