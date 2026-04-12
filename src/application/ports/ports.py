"""Port interfaces (abstract base classes) for InfraAgent.

These define the contracts between the application layer and infrastructure.
Swap adapters without touching domain or application logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.models import (
    CodeGenOutput,
    GeneratedFile,
    PlanResult,
    RequirementsHandoff,
    SubscriptionContext,
    ValidationFinding,
)


class ICodeGenPort(ABC):
    """Generates IaC code from requirements."""

    @abstractmethod
    async def generate(
        self,
        requirements: RequirementsHandoff,
        feedback: list[ValidationFinding] | None = None,
    ) -> CodeGenOutput:
        ...


class IValidationPort(ABC):
    """Runs deterministic IaC validation (fmt, build, validate, lint)."""

    @abstractmethod
    async def validate(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        ...


class IStandardsPort(ABC):
    """Validates code against organizational naming/tagging/structural policies."""

    @abstractmethod
    async def check(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        ...


class ISecurityPort(ABC):
    """Runs static security analysis (tfsec, Checkov, bicep diagnostics)."""

    @abstractmethod
    async def scan(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        ...


class ISourceControlPort(ABC):
    """Manages branches, commits, and PRs."""

    @abstractmethod
    async def create_branch(self, branch_name: str) -> str:
        ...

    @abstractmethod
    async def commit_files(
        self, branch_name: str, files: list[GeneratedFile], message: str
    ) -> str:
        ...

    @abstractmethod
    async def create_pr(
        self, branch_name: str, title: str, body: str
    ) -> str:
        ...


class IDeployPort(ABC):
    """Runs plan/apply operations."""

    @abstractmethod
    async def plan(self, files: list[GeneratedFile]) -> PlanResult:
        ...

    @abstractmethod
    async def apply(self, files: list[GeneratedFile]) -> PlanResult:
        ...


class ISubscriptionDiscoveryPort(ABC):
    """Queries Azure subscription for existing resources."""

    @abstractmethod
    async def discover(self, subscription_id: str) -> SubscriptionContext:
        ...
