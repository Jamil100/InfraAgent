"""Policy Engine port interface.

Contract between the application layer and policy validation backends (naming, tagging, security, AVM).
Ref: TechSpec Section 2.1, lines 288-298
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PolicyViolation:
    """A policy enforcement violation.

    Fields:
        resource: Resource identifier that violated policy
        policy: Policy name/rule
        severity: "critical" | "high" | "medium" | "low"
        expected: Expected value per policy
        actual: Actual value found
        remediation: How to fix the violation
    """
    resource: str
    policy: str
    severity: str  # "critical" | "high" | "medium" | "low"
    expected: str
    actual: str
    remediation: str


@dataclass
class PolicyResult:
    """Result of policy validation.

    Fields:
        passed: Whether all policies passed
        violations: List of any violations found
    """
    passed: bool
    violations: list[PolicyViolation] = field(default_factory=list)


class IPolicyEnginePort(ABC):
    """Abstracts over policy validation (naming, tagging, security, AVM compliance).

    Enforces organizational standards and compliance rules.
    """

    @abstractmethod
    async def validate_naming(self, files: list[dict]) -> PolicyResult:
        """Validate resource naming conventions.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            PolicyResult with naming violations (if any)
        """
        ...

    @abstractmethod
    async def validate_tags(self, files: list[dict]) -> PolicyResult:
        """Validate resource tagging policies.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            PolicyResult with tagging violations (if any)
        """
        ...

    @abstractmethod
    async def validate_security(self, files: list[dict]) -> PolicyResult:
        """Validate security policies.

        Args:
            files: List of {"path": "...", "content": "..."} dicts

        Returns:
            PolicyResult with security violations (if any)
        """
        ...

    @abstractmethod
    async def check_avm_availability(
        self, resource_type: str, version: str | None = None
    ) -> bool:
        """Check whether an Azure Verified Module (AVM) exists for a resource type.

        Used by the Standards Agent to prefer AVM modules over raw resource declarations.

        Args:
            resource_type: Azure resource type (e.g., "Microsoft.Compute/virtualMachines")
            version: Optional specific AVM version to check

        Returns:
            True if an AVM module is available for the resource type
        """
        ...
