"""Backward-compatibility re-export shim for port interfaces.

All canonical port definitions now live in their own files:
  - llm_port.py
  - infra_provider_port.py
  - source_control_port.py
  - policy_engine_port.py
  - template_registry_port.py
  - observability_port.py
  - subscription_discovery_port.py

New code should import directly from those modules or from the package __init__.
This file exists so that any existing imports of the form
  ``from src.application.ports.ports import X``
continue to work without modification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# Re-export everything from the individual port files
from src.application.ports.infra_provider_port import (
    ApplyResult,
    IInfraProviderPort,
    PlanResult,
    ValidationResult,
)
from src.application.ports.llm_port import (
    ILLMCompletionPort,
    LLMMessage,
    LLMResponse,
    TaskProfile,
    ToolDefinition,
)
from src.application.ports.observability_port import IObservabilityPort
from src.application.ports.policy_engine_port import (
    IPolicyEnginePort,
    PolicyResult,
    PolicyViolation,
)
from src.application.ports.source_control_port import (
    ISourceControlPort,
    PipelineStatus,
    PRResult,
)
from src.application.ports.subscription_discovery_port import (
    DiscoveredResource,
    DiscoveredVNet,
    ISubscriptionDiscoveryPort,
    SubscriptionContext,
)
from src.application.ports.template_registry_port import (
    HydratedTemplate,
    ITemplateRegistryPort,
    TemplateMetadata,
)

# ============================================================================
# Legacy/Application Ports
# These use domain models from src.domain.models.models and are kept here
# because they pre-date the clean port split. New code should prefer the
# canonical ports above.
# ============================================================================

from src.domain.models.models import (
    CodeGenOutput,
    GeneratedFile,
    PlanResult as PlanResultPydantic,
    RequirementsHandoff,
    ValidationFinding,
)


class ICodeGenPort(ABC):
    """Generates IaC code from requirements.

    Used by code generation workspace agent.
    """

    @abstractmethod
    async def generate(
        self,
        requirements: RequirementsHandoff,
        feedback: list[ValidationFinding] | None = None,
    ) -> CodeGenOutput:
        """Generate IaC code from requirements.

        Args:
            requirements: User requirements handoff
            feedback: Optional validation feedback for regeneration

        Returns:
            Generated IaC files and artifacts
        """
        ...


class IValidationPort(ABC):
    """Runs deterministic IaC validation (fmt, build, validate, lint).

    Note: Prefer IInfraProviderPort for new code.
    """

    @abstractmethod
    async def validate(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        """Validate IaC files.

        Args:
            files: Generated IaC files

        Returns:
            List of validation findings (errors/warnings)
        """
        ...


class IStandardsPort(ABC):
    """Validates code against organizational naming/tagging/structural policies.

    Note: Prefer IPolicyEnginePort for new code.
    """

    @abstractmethod
    async def check(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        """Check code against organizational standards.

        Args:
            files: Generated IaC files

        Returns:
            List of policy violations (as ValidationFindings)
        """
        ...


class ISecurityPort(ABC):
    """Runs static security analysis (tfsec, Checkov, bicep diagnostics).

    Note: Prefer IPolicyEnginePort for new code.
    """

    @abstractmethod
    async def scan(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        """Scan code for security issues.

        Args:
            files: Generated IaC files

        Returns:
            List of security findings
        """
        ...


class IDeployPort(ABC):
    """Runs plan/apply operations.

    Note: Prefer IInfraProviderPort for new code.
    """

    @abstractmethod
    async def plan(self, files: list[GeneratedFile]) -> PlanResultPydantic:
        """Generate a deployment plan.

        Args:
            files: Generated IaC files

        Returns:
            Plan result with change summary
        """
        ...

    @abstractmethod
    async def apply(self, files: list[GeneratedFile]) -> PlanResultPydantic:
        """Apply infrastructure changes.

        Args:
            files: Generated IaC files

        Returns:
            Apply result
        """
        ...


__all__ = [
    # LLM
    "ILLMCompletionPort",
    "LLMMessage",
    "LLMResponse",
    "TaskProfile",
    "ToolDefinition",
    # Infra Provider
    "IInfraProviderPort",
    "ApplyResult",
    "PlanResult",
    "ValidationResult",
    # Source Control
    "ISourceControlPort",
    "PRResult",
    "PipelineStatus",
    # Policy Engine
    "IPolicyEnginePort",
    "PolicyResult",
    "PolicyViolation",
    # Template Registry
    "ITemplateRegistryPort",
    "HydratedTemplate",
    "TemplateMetadata",
    # Observability
    "IObservabilityPort",
    # Subscription Discovery
    "ISubscriptionDiscoveryPort",
    "DiscoveredResource",
    "DiscoveredVNet",
    "SubscriptionContext",
    # Legacy
    "ICodeGenPort",
    "IValidationPort",
    "IStandardsPort",
    "ISecurityPort",
    "IDeployPort",
]
