"""Generate use case for custom and catalog IaC generation paths."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from src.application.ports.infra_provider_port import IInfraProviderPort
from src.application.ports.llm_port import (
    ILLMCompletionPort,
    LLMMessage,
    TaskProfile,
    ToolDefinition,
)
from src.application.ports.observability_port import IObservabilityPort
from src.application.ports.policy_engine_port import IPolicyEnginePort, PolicyViolation
from src.application.ports.template_registry_port import ITemplateRegistryPort
from src.domain.models.models import GeneratedFile, IaCLanguage

MAX_MAKER_CHECKER_ITERATIONS = 3
MAX_REWORK_CONTEXT_VIOLATIONS = 5

FILE_STRUCTURE_TERRAFORM = {
    "root": [
        "main.tf",
        "variables.tf",
        "outputs.tf",
        "providers.tf",
        "backend.tf",
        "terraform.tfvars",
        "locals.tf",
    ],
    "modules_dir": "modules/",
    "docs_dir": "docs/",
}

FILE_STRUCTURE_BICEP = {
    "root": [
        "main.bicep",
        "main.bicepparam",
    ],
    "modules_dir": "modules/",
    "docs_dir": "docs/",
}

SECRET_HANDLING_RULES = [
    "Never hardcode secrets, passwords, connection strings, or API keys in IaC files.",
    "Use Azure Key Vault references for all sensitive values.",
    "Mark sensitive variables with `sensitive = true` (Terraform) or `@secure()` decorator (Bicep).",
    "Use Managed Identity for service-to-service authentication where possible.",
    "Never output sensitive values.",
]


@dataclass
class GenerateResult:
    files: list[GeneratedFile]
    standards_passed: bool
    security_passed: bool
    violations: list[dict[str, Any]]
    iteration_count: int
    diagram_mermaid: str | None
    assistant_message: str


class GenerateUseCase:
    CODEGEN_PROFILE = TaskProfile(profile="code-generation")
    DIAGRAM_PROFILE = TaskProfile(profile="fast-lightweight")

    def __init__(
        self,
        llm: ILLMCompletionPort,
        policy: IPolicyEnginePort,
        templates: ITemplateRegistryPort,
        infra_providers: dict[str, IInfraProviderPort],
        observability: IObservabilityPort,
    ) -> None:
        self._llm = llm
        self._policy = policy
        self._templates = templates
        self._infra = infra_providers
        self._obs = observability

    async def run_custom_path(
        self,
        requirements: str,
        language: IaCLanguage,
        conversation_history: list[LLMMessage],
        mcp_tool_executor: Callable[..., Any],
        project_type: str = "production",
        subscription_context: dict[str, Any] | None = None,
    ) -> GenerateResult:
        provider = self._infra[language.value]
        all_violations: list[dict[str, Any]] = []
        latest_files: list[GeneratedFile] = []

        for iteration in range(1, MAX_MAKER_CHECKER_ITERATIONS + 1):
            iteration_violations: list[dict[str, Any]] = []
            self._obs.start_span(
                "generate_iteration",
                {"iteration": iteration, "language": language.value},
            )
            latest_files = await self._generate_code(
                requirements=requirements,
                language=language,
                history=conversation_history,
                tool_executor=mcp_tool_executor,
                prior_violations=all_violations,
                project_type=project_type,
                subscription_context=subscription_context,
            )
            if not latest_files:
                iteration_violations.append(
                    _violation(
                        checker="codegen",
                        severity="error",
                        message="Code generation returned no files.",
                    )
                )
                all_violations.extend(iteration_violations)
                continue

            iac_validation = await self._run_iac_validation_pipeline(
                provider,
                latest_files,
                language,
            )
            iteration_violations.extend(
                [
                    _violation(
                        checker="iac_validation",
                        severity="warning",
                        message=warning,
                    )
                    for warning in iac_validation["warnings"]
                ]
            )
            if not iac_validation["passed"]:
                iteration_violations.extend(
                    [
                        _violation(
                            checker="iac_validation",
                            severity="error",
                            message=error,
                        )
                        for error in iac_validation["errors"]
                    ]
                )
                all_violations.extend(iteration_violations)
                continue

            file_dicts = _as_file_dicts(latest_files)
            naming = await self._policy.validate_naming(file_dicts)
            tags = await self._policy.validate_tags(file_dicts)
            standards_violations = [
                _policy_violation_to_dict("standards", v)
                for v in [*naming.violations, *tags.violations]
            ]
            if standards_violations:
                iteration_violations.extend(standards_violations)
                all_violations.extend(iteration_violations)
                continue

            security = await self._policy.validate_security(file_dicts)
            security_violations = [
                _policy_violation_to_dict("security", v) for v in security.violations
            ]
            if security_violations:
                iteration_violations.extend(security_violations)
                all_violations.extend(iteration_violations)
                continue

            diagram = await self._generate_diagram(latest_files, language)
            self._obs.record_metric("generate_iterations", float(iteration))
            return GenerateResult(
                files=latest_files,
                standards_passed=True,
                security_passed=True,
                violations=iteration_violations,
                iteration_count=iteration,
                diagram_mermaid=diagram,
                assistant_message=(
                    f"Generated {len(latest_files)} files in {iteration} iteration(s)."
                ),
            )

        self._obs.record_metric("generate_max_iterations_reached", 1.0)
        return GenerateResult(
            files=latest_files,
            standards_passed=False,
            security_passed=False,
            violations=all_violations,
            iteration_count=MAX_MAKER_CHECKER_ITERATIONS,
            diagram_mermaid=None,
            assistant_message=(
                f"Reached max iterations ({MAX_MAKER_CHECKER_ITERATIONS}). "
                "Remaining violations require manual review."
            ),
        )

    async def run_catalog_path(
        self,
        template_name: str,
        language: IaCLanguage,
        parameters: dict[str, Any],
        standards: dict[str, Any],
    ) -> GenerateResult:
        hydrated = await self._templates.hydrate(
            template_name,
            language.value,
            parameters,
            standards,
        )
        generated_files = [
            GeneratedFile(path=file_data["path"], content=file_data["content"])
            for file_data in hydrated.files
        ]
        file_dicts = _as_file_dicts(generated_files)
        provider = self._infra[language.value]
        validation = await provider.validate(file_dicts)
        violations = [
            _violation("syntax_validation", "error", message=error)
            for error in validation.errors
        ] + [
            _violation("syntax_validation", "warning", message=warning)
            for warning in validation.warnings
        ]

        return GenerateResult(
            files=generated_files,
            standards_passed=True,
            security_passed=True,
            violations=violations,
            iteration_count=1,
            diagram_mermaid=None,
            assistant_message=(
                f"Template '{template_name}' hydrated with {len(hydrated.files)} files."
            ),
        )

    async def _run_iac_validation_pipeline(
        self,
        provider: IInfraProviderPort,
        files: list[GeneratedFile],
        language: IaCLanguage,
    ) -> dict[str, Any]:
        self._obs.start_span("iac_validation_pipeline", {"language": language.value})
        file_dicts = _as_file_dicts(files)

        format_result = await provider.format_check(file_dicts)
        if not format_result.valid:
            return {
                "passed": False,
                "errors": [f"Format: {error}" for error in format_result.errors],
                "warnings": format_result.warnings,
            }

        validate_result = await provider.validate(file_dicts)
        if not validate_result.valid:
            return {
                "passed": False,
                "errors": [f"Validate: {error}" for error in validate_result.errors],
                "warnings": validate_result.warnings,
            }

        lint_result = await provider.lint(file_dicts)
        if not lint_result.valid:
            return {
                "passed": False,
                "errors": [f"Lint: {error}" for error in lint_result.errors],
                "warnings": lint_result.warnings,
            }

        return {"passed": True, "errors": [], "warnings": lint_result.warnings}

    async def _generate_code(
        self,
        requirements: str,
        language: IaCLanguage,
        history: list[LLMMessage],
        tool_executor: Callable[..., Any],
        prior_violations: list[dict[str, Any]],
        project_type: str,
        subscription_context: dict[str, Any] | None,
    ) -> list[GeneratedFile]:
        system_prompt = self._build_codegen_prompt(
            language,
            prior_violations,
            project_type=project_type,
            subscription_context=subscription_context,
        )
        response = await self._llm.complete_with_tools(
            system_prompt=system_prompt,
            messages=[*history, LLMMessage(role="user", content=requirements)],
            tools=self._get_mcp_tools(language),
            tool_executor=tool_executor,
            task_profile=self.CODEGEN_PROFILE,
        )
        return self._parse_generated_files(response.content)

    async def _generate_diagram(
        self,
        files: list[GeneratedFile],
        language: IaCLanguage,
    ) -> str | None:
        self._obs.start_span("generate_diagram", {"language": language.value})
        code_summary = "\n\n".join(
            [
                f"## {file.path}\n```{language.value}\n{file.content}\n```"
                for file in files[:10]
            ]
        )
        response = await self._llm.complete(
            system_prompt=(
                "Generate a Mermaid architecture diagram from IaC code. "
                "Return only Mermaid text."
            ),
            messages=[
                LLMMessage(
                    role="user",
                    content=f"Generate a Mermaid diagram for:\n\n{code_summary}",
                )
            ],
            task_profile=self.DIAGRAM_PROFILE,
        )
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 2 and lines[0].strip().startswith("```"):
                diagram_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                return "\n".join(diagram_lines).strip() or None
        return content or None

    def _build_codegen_prompt(
        self,
        language: IaCLanguage,
        prior_violations: list[dict[str, Any]],
        project_type: str,
        subscription_context: dict[str, Any] | None,
    ) -> str:
        file_structure = (
            FILE_STRUCTURE_TERRAFORM
            if language == IaCLanguage.TERRAFORM
            else FILE_STRUCTURE_BICEP
        )
        prompt_lines = [
            "You are InfraAgent's code generation assistant.",
            "Use Azure Verified Modules (AVM) first whenever available.",
            "If no AVM exists for a resource, use native resource declarations.",
            "",
            "Secret handling rules:",
            *[f"- {rule}" for rule in SECRET_HANDLING_RULES],
            "",
            f"Project type: {project_type}",
            f"Required root files: {', '.join(file_structure['root'])}",
            f"Modules directory: {file_structure['modules_dir']}",
            f"Docs directory: {file_structure['docs_dir']}",
        ]
        if subscription_context:
            prompt_lines.extend(["", f"Subscription context: {subscription_context}"])
        if prior_violations:
            prompt_lines.append("")
            prompt_lines.append("Fix these previous violations:")
            # Violations are appended in generation order, so the tail contains the
            # most recent and most relevant context for the next rework iteration.
            for violation in prior_violations[-MAX_REWORK_CONTEXT_VIOLATIONS:]:
                checker = violation.get("checker", "unknown")
                severity = violation.get("severity", "unknown")
                message = violation.get("message", "")
                prompt_lines.append(f"- [{checker}/{severity}] {message}")
        return "\n".join(prompt_lines)

    def _get_mcp_tools(self, language: IaCLanguage) -> list[ToolDefinition]:
        if language == IaCLanguage.TERRAFORM:
            return [
                ToolDefinition(
                    name="search_modules",
                    description="Search Terraform modules, including AVM modules.",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                )
            ]
        return [
            ToolDefinition(
                name="list_avm_metadata",
                description="List Azure Verified Module metadata for Bicep resources.",
                input_schema={"type": "object", "properties": {"resourceType": {"type": "string"}}},
            )
        ]

    def _parse_generated_files(self, content: str) -> list[GeneratedFile]:
        payload = _extract_json_payload(content)
        if not isinstance(payload, dict):
            return []

        files = payload.get("files", [])
        if not isinstance(files, list):
            return []

        generated_files: list[GeneratedFile] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).strip()
            body = str(item.get("content", ""))
            if not path:
                continue
            generated_files.append(GeneratedFile(path=path, content=body))
        return generated_files


def _extract_json_payload(content: str) -> Any:
    if "```json" in content:
        start = content.find("```json") + len("```json")
        end = content.find("```", start)
        if end > start:
            raw_json = content[start:end].strip()
            try:
                return json.loads(raw_json)
            except json.JSONDecodeError:
                return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _as_file_dicts(files: list[GeneratedFile]) -> list[dict[str, str]]:
    return [{"path": file.path, "content": file.content} for file in files]


def _policy_violation_to_dict(checker: str, violation: PolicyViolation) -> dict[str, Any]:
    message = violation.policy
    if any(value is not None and value != "" for value in (violation.expected, violation.actual)):
        message = f"{violation.policy} (expected: {violation.expected}, actual: {violation.actual})"
    return _violation(
        checker=checker,
        severity=_map_policy_severity(violation.severity),
        resource=violation.resource,
        message=message,
        remediation=violation.remediation,
    )


def _violation(
    checker: str,
    severity: str,
    message: str,
    resource: str = "",
    file: str = "",
    line: int = 0,
    remediation: str = "",
) -> dict[str, Any]:
    return {
        "checker": checker,
        "severity": severity,
        "resource": resource,
        "file": file,
        "line": line,
        "message": message,
        "remediation": remediation,
    }


def _map_policy_severity(severity: str) -> str:
    """Normalize policy severities to domain-supported values: error/warning/info."""
    normalized = severity.lower()
    if normalized in {"critical", "high", "error"}:
        return "error"
    if normalized in {"medium", "low", "warning", "warn"}:
        return "warning"
    return "info"
