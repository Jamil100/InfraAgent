"""Orchestrator — drives the InfraAgent pipeline through all stages."""

from __future__ import annotations

import logging
import uuid
from typing import AsyncIterator

from src.domain.models.models import (
    CodeGenOutput,
    InfraRequest,
    PipelineStage,
    PipelineState,
    RequirementsHandoff,
    Severity,
    ValidationFinding,
)
from src.application.ports.ports import (
    ICodeGenPort,
    IDeployPort,
    ISecurityPort,
    ISourceControlPort,
    IStandardsPort,
    IValidationPort,
)

logger = logging.getLogger(__name__)

MAX_LOOP1_ITERATIONS = 3  # codegen → validate → standards → security → retry
MAX_LOOP2_ITERATIONS = 2  # plan-failure rework


class OrchestratorPipeline:
    """Graph-based pipeline: Consulting → CodeGen ↔ Review loop → H1 → PR → Plan → H2 → Deploy."""

    def __init__(
        self,
        codegen: ICodeGenPort,
        standards: IStandardsPort,
        security: ISecurityPort,
        source_control: ISourceControlPort,
        validation: IValidationPort | None = None,
        deploy: IDeployPort | None = None,
    ) -> None:
        self._codegen = codegen
        self._standards = standards
        self._security = security
        self._scm = source_control
        self._validation = validation
        self._deploy = deploy

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

        # --- Loop 1: CodeGen → Validate → Standards → Security → retry on errors ---
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

            # IaC Validation (deterministic: lint / fmt / validate)
            if self._validation:
                state.stage = PipelineStage.VALIDATION
                yield state
                val_findings = await self._validation.validate(codegen_output.files)
            else:
                val_findings = []

            # Standards review (LLM)
            state.stage = PipelineStage.STANDARDS
            yield state
            std_findings = await self._standards.check(codegen_output.files)

            # Security scan (LLM)
            state.stage = PipelineStage.SECURITY
            yield state
            sec_findings = await self._security.scan(codegen_output.files)

            all_findings = val_findings + std_findings + sec_findings
            state.validation_findings = all_findings

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
        # Pipeline pauses here in production; auto-approved for MVP/demo.
        # The /api/pipeline/approve/h1 endpoint resumes execution.

        # --- Create PR ---
        if not (codegen_output and codegen_output.files):
            state.stage = PipelineStage.FAILED
            state.error = "No files to commit"
            yield state
            return

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
            return

        yield state

        # --- Loop 2: Plan → on failure rework CodeGen → re-plan ---
        if not self._deploy:
            return  # deploy adapter not configured; stop after PR

        for plan_iteration in range(1, MAX_LOOP2_ITERATIONS + 1):
            state.loop2_iteration = plan_iteration
            state.stage = PipelineStage.PLAN
            yield state

            plan_result = await self._deploy.plan(codegen_output.files)
            state.plan_result = plan_result

            if plan_result.success:
                logger.info("Plan succeeded on loop2 iteration %d", plan_iteration)
                break

            logger.warning(
                "Plan failed (iteration %d): %s", plan_iteration, plan_result.error
            )

            if plan_iteration < MAX_LOOP2_ITERATIONS:
                # Rework: feed plan error back into CodeGen as a finding
                all_findings.append(
                    ValidationFinding(
                        checker="plan-failure",
                        severity=Severity.ERROR,
                        message=f"Plan failed: {plan_result.error[:500]}",
                        remediation="Revise the IaC to resolve the plan error.",
                    )
                )
                state.validation_findings = all_findings

                # Regenerate and re-commit
                feedback = [f for f in all_findings if f.severity == Severity.ERROR]
                codegen_output = await self._codegen.generate(requirements, feedback=feedback)
                state.codegen_output = codegen_output

                if codegen_output.files:
                    try:
                        await self._scm.commit_files(
                            branch,
                            codegen_output.files,
                            f"fix: InfraAgent plan-failure rework (iteration {plan_iteration})",
                        )
                    except Exception as exc:
                        logger.error("SCM rework commit error: %s", exc)

        if not (state.plan_result and state.plan_result.success):
            state.stage = PipelineStage.FAILED
            state.error = f"Plan failed after {MAX_LOOP2_ITERATIONS} attempts"
            yield state
            return

        # --- Human Gate H2: Plan Review ---
        state.stage = PipelineStage.HUMAN_REVIEW_PLAN
        yield state
        # In production, pauses for /api/pipeline/approve/h2.
        # Auto-approved for MVP demo.

        # --- Deploy ---
        state.stage = PipelineStage.DEPLOYING
        yield state

        deploy_result = await self._deploy.apply(codegen_output.files)
        state.plan_result = deploy_result

        if deploy_result.success:
            state.stage = PipelineStage.DEPLOYED
        else:
            state.stage = PipelineStage.FAILED
            state.error = f"Deploy failed: {deploy_result.error}"

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
