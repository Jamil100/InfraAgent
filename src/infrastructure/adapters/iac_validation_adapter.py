"""IaC validation adapter — deterministic bicep lint + terraform validate via CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path

from src.domain.models.models import GeneratedFile, Severity, ValidationFinding
from src.application.ports.ports import IValidationPort

logger = logging.getLogger(__name__)

# Matches: /path/file.bicep(10,3) : Warning rule-id: message
_BICEP_DIAG_RE = re.compile(
    r"(?P<file>[^\(]+)\((?P<line>\d+),(?P<col>\d+)\)\s*:\s*(?P<level>\w+)\s+(?P<rule>[^:]+):\s*(?P<msg>.+)"
)


class IaCValidationAdapter(IValidationPort):
    """Runs bicep lint (via az bicep lint) and terraform validate on generated files."""

    async def validate(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        bicep_files = [f for f in files if f.path.endswith(".bicep")]
        tf_files = [f for f in files if f.path.endswith(".tf")]

        findings: list[ValidationFinding] = []

        if bicep_files:
            findings.extend(await _validate_bicep(bicep_files))

        if tf_files:
            findings.extend(await _validate_terraform(tf_files))

        return findings


# ---------------------------------------------------------------------------
# Bicep helpers
# ---------------------------------------------------------------------------


async def _validate_bicep(files: list[GeneratedFile]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write all files so cross-file references resolve
        for gf in files:
            dest = tmp / gf.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(gf.content, encoding="utf-8")

        for gf in files:
            if not gf.path.endswith(".bicep"):
                continue
            bicep_path = tmp / gf.path
            findings.extend(await _run_bicep_lint(bicep_path, gf.path))

    return findings


async def _run_bicep_lint(bicep_path: Path, relative_path: str) -> list[ValidationFinding]:
    """Run `az bicep lint` on a single file and parse diagnostics."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "az", "bicep", "lint",
            "--file", str(bicep_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        logger.warning("az CLI not found — skipping bicep lint")
        return [
            ValidationFinding(
                checker="bicep-lint",
                severity=Severity.WARNING,
                file=relative_path,
                message="az CLI not installed; bicep lint skipped.",
                remediation="Install Azure CLI: https://aka.ms/installazurecliwindows",
            )
        ]

    # az bicep lint writes diagnostics to stderr; exit code != 0 on errors
    output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
    return _parse_bicep_diagnostics(output, relative_path)


def _parse_bicep_diagnostics(output: str, file_hint: str) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for line in output.splitlines():
        m = _BICEP_DIAG_RE.search(line)
        if m:
            level = m.group("level").lower()
            severity = Severity.ERROR if level == "error" else Severity.WARNING if level == "warning" else Severity.INFO
            findings.append(
                ValidationFinding(
                    checker=f"bicep-lint/{m.group('rule').strip()}",
                    severity=severity,
                    file=file_hint,
                    line=int(m.group("line")),
                    message=m.group("msg").strip(),
                    remediation=f"See https://aka.ms/bicep/linter/{m.group('rule').strip()}",
                )
            )
        elif line.strip() and ("error" in line.lower() or "warning" in line.lower()):
            # Fallback for unstructured output
            severity = Severity.ERROR if "error" in line.lower() else Severity.WARNING
            findings.append(
                ValidationFinding(
                    checker="bicep-lint",
                    severity=severity,
                    file=file_hint,
                    message=line.strip(),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Terraform helpers
# ---------------------------------------------------------------------------


async def _validate_terraform(files: list[GeneratedFile]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        for gf in files:
            dest = tmp / gf.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(gf.content, encoding="utf-8")

        # 1. fmt check
        fmt_findings = await _run_terraform_fmt(tmpdir)
        findings.extend(fmt_findings)

        # 2. init (no backend) — required before validate
        init_ok = await _run_terraform_init(tmpdir)
        if not init_ok:
            findings.append(
                ValidationFinding(
                    checker="terraform-init",
                    severity=Severity.ERROR,
                    message="terraform init failed; validate skipped.",
                    remediation="Check provider and module source configurations.",
                )
            )
            return findings

        # 3. validate
        val_findings = await _run_terraform_validate(tmpdir)
        findings.extend(val_findings)

    return findings


async def _run_terraform_fmt(cwd: str) -> list[ValidationFinding]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "terraform", "fmt", "-check", "-diff", "-recursive",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
    except FileNotFoundError:
        logger.warning("terraform CLI not found — skipping fmt check")
        return [
            ValidationFinding(
                checker="terraform-fmt",
                severity=Severity.WARNING,
                message="terraform CLI not installed; fmt check skipped.",
                remediation="Install Terraform CLI: https://developer.hashicorp.com/terraform/install",
            )
        ]

    if proc.returncode != 0:
        return [
            ValidationFinding(
                checker="terraform-fmt",
                severity=Severity.WARNING,
                message="Terraform files need formatting.",
                remediation=f"Run `terraform fmt` to fix.\n{stdout.decode(errors='replace').strip()}",
            )
        ]
    return []


async def _run_terraform_init(cwd: str) -> bool:
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


async def _run_terraform_validate(cwd: str) -> list[ValidationFinding]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "terraform", "validate", "-json",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
    except FileNotFoundError:
        return []

    return _parse_terraform_validate_json(stdout.decode(errors="replace"))


def _parse_terraform_validate_json(raw: str) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        if raw.strip():
            findings.append(
                ValidationFinding(
                    checker="terraform-validate",
                    severity=Severity.WARNING,
                    message=f"Could not parse validate output: {raw[:200]}",
                )
            )
        return findings

    for diag in data.get("diagnostics", []):
        level = diag.get("severity", "error")
        severity = Severity.ERROR if level == "error" else Severity.WARNING
        rng = diag.get("range", {})
        file_path = rng.get("filename", "")
        line = rng.get("start", {}).get("line", 0)
        findings.append(
            ValidationFinding(
                checker="terraform-validate",
                severity=severity,
                file=file_path,
                line=line,
                message=diag.get("summary", ""),
                remediation=diag.get("detail", ""),
            )
        )
    return findings
