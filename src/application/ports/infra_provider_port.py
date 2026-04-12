"""Infrastructure Provider port interface.

Contract between the application layer and IaC tools (Terraform, Bicep).
Ref: TechSpec Section 2.1, lines 202-221
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of IaC validation/lint/format check.

    Fields:
        valid: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages
    """
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PlanResult:
    """Result of a plan operation (Terraform plan / Bicep what-if).

    Fields:
        success: Whether plan succeeded
        output: Plan output text
        resources_to_create: Count of resources to create
        resources_to_modify: Count of resources to modify
        resources_to_destroy: Count of resources to destroy
        estimated_cost: Estimated cost impact (if available)
    """
    success: bool
    output: str
    resources_to_create: int
    resources_to_modify: int
    resources_to_destroy: int
    estimated_cost: float | None = None


@dataclass
class ApplyResult:
    """Result of an apply operation (Terraform apply / Bicep deployment).

    Fields:
        success: Whether apply succeeded
        output: Deployment output text
        resources_created: List of created resource IDs
        errors: List of any errors that occurred
    """
    success: bool
    output: str
    resources_created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class IInfraProviderPort(ABC):
    """Abstracts over infrastructure as code tools (Terraform and Bicep).

    Single unified port for both languages; implementations choose which to support.
    """

    @abstractmethod
    async def format_check(self, files: list[dict]) -> ValidationResult:
        """Check IaC format/syntax.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with format check results
        """
        ...

    @abstractmethod
    async def validate(self, files: list[dict]) -> ValidationResult:
        """Validate IaC semantics and configuration.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with validation results
        """
        ...

    @abstractmethod
    async def lint(self, files: list[dict]) -> ValidationResult:
        """Lint IaC for best practices and style.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            ValidationResult with lint results
        """
        ...

    @abstractmethod
    async def plan(self, files: list[dict], variables: dict) -> PlanResult:
        """Generate a plan of infrastructure changes.

        Args:
            files: List of {"path": "...", "content": "..."} dicts
            variables: Variable values for the plan

        Returns:
            PlanResult with change summary
        """
        ...

    @abstractmethod
    async def apply(self, plan_id: str) -> ApplyResult:
        """Apply a previously created plan.

        Args:
            plan_id: ID of the plan to apply

        Returns:
            ApplyResult with deployment results
        """
        ...

    @abstractmethod
    def get_language(self) -> str:
        """Return the IaC language this adapter supports.

        Returns:
            "terraform" or "bicep"
        """
        ...
