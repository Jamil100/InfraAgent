"""Orchestrator — drives the InfraAgent pipeline through all stages."""

from __future__ import annotations

import logging
import uuid
from typing import AsyncIterator

from src.core.models import (
    CodeGenOutput,
    InfraRequest,
    PipelineStage,
    PipelineState,
    RequirementsHandoff,
    Severity,
    ValidationFinding,
)
from src.core.ports import (
    ICodeGenPort,
    ISecurityPort,
    ISourceControlPort,
    IStandardsPort,
)

logger = logging.getLogger(__name__)

MAX_LOOP1_ITERATIONS = 3  # codegen → validate → standards → security → retry


class OrchestratorPipeline:
    """Graph-based pipeline: Consulting → CodeGen ↔ Review loop → PR."""

    def __init__(
        self,
        codegen: ICodeGenPort,
        standards: IStandardsPort,
        security: ISecurityPort,
        source_control: ISourceControlPort,
    ) -> None:
        self._codegen = codegen
        self._standards = standards
        self._security = security
        self._scm = source_control

    async def run(
        self,
        requirements: RequirementsHandoff,
        request: InfraRequest,
    ) -> AsyncIterator[PipelineState]:
        """Execute the pipeline, yielding state after each stage."""
        state = PipelineState(
            session_id=request.session_id or str(uuid.uuid4()),
            request=request,
            requirements=requirements,
        )

        # --- Stage: CodeGen → Review Loop ---
        codegen_output: CodeGenOutput | None = None
        all_findings: list[ValidationFinding] = []

        for iteration in range(1, MAX_LOOP1_ITERATIONS + 1):
            state.loop1_iteration = iteration

            # CodeGen
            state.stage = PipelineStage.CODEGEN
            yield state

            feedback = [f for f in all_findings if f.severity == Severity.ERROR]
            codegen_output = await self._codegen.generate(
                requirements, feedback=feedback or None
            )
            state.codegen_output = codegen_output

            if not codegen_output.files:
                state.stage = PipelineStage.FAILED
                state.error = "CodeGen produced no files"
                yield state
                return

            # Standards
            state.stage = PipelineStage.STANDARDS
            yield state
            std_findings = await self._standards.check(codegen_output.files)

            # Security
            state.stage = PipelineStage.SECURITY
            yield state
            sec_findings = await self._security.scan(codegen_output.files)

            all_findings = std_findings + sec_findings
            state.validation_findings = all_findings

            # If no errors, break
            errors = [f for f in all_findings if f.severity == Severity.ERROR]
            if not errors:
                logger.info("Loop 1 passed on iteration %d", iteration)
                break

            logger.info(
                "Loop 1 iteration %d: %d errors, retrying", iteration, len(errors)
            )

        # --- Human Gate H1: Code Review ---
        state.stage = PipelineStage.HUMAN_REVIEW_CODE
        yield state
        # In a real system, we'd pause and wait for approval.
        # For MVP/demo, we auto-approve and continue.

        # --- Stage: Create PR ---
        if codegen_output and codegen_output.files:
            branch = f"infraagent/{state.session_id[:8]}"
            state.stage = PipelineStage.PR_CREATED
            try:
                await self._scm.create_branch(branch)
                await self._scm.commit_files(
                    branch,
                    codegen_output.files,
                    f"feat: InfraAgent generated IaC for {requirements.project_name}",
                )
                pr_url = await self._scm.create_pr(
                    branch,
                    f"[InfraAgent] {requirements.project_name} infrastructure",
                    _build_pr_body(requirements, codegen_output, all_findings),
                )
                state.pr_url = pr_url
            except Exception as exc:
                logger.error("Source control error: %s", exc)
                state.error = str(exc)
                state.stage = PipelineStage.FAILED
            yield state
        else:
            state.stage = PipelineStage.FAILED
            state.error = "No files to commit"
            yield state


def _build_pr_body(
    req: RequirementsHandoff,
    output: CodeGenOutput,
    findings: list[ValidationFinding],
) -> str:
    """Build a markdown PR description."""
    errors = [f for f in findings if f.severity == Severity.ERROR]
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    files_list = "\n".join(f"- `{f.path}`" for f in output.files)

    body = f"""## InfraAgent Generated Infrastructure

**Project**: {req.project_name}
**Language**: {req.iac_language.value}
**Region**: {req.azure_region}
**Environment**: {req.environment}

### Description
{req.description}

### Generated Files
{files_list}

### Review Summary
- Errors: {len(errors)}
- Warnings: {len(warnings)}

### Architecture
```mermaid
{output.mermaid_diagram}
```

---
*Generated by InfraAgent*
"""
    return body
