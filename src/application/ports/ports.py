"""Port interfaces (abstract base classes) for InfraAgent.

These define the contracts between the application layer and infrastructure.
Infrastructure adapters implement these ports. Swap adapters without touching domain or application logic.

Ref: TechSpec Section 2.1 (Port Interfaces)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ============================================================================
# LLM Completion Port (TechSpec Section 2.1, lines 153-172)
# ============================================================================


@dataclass
class LLMMessage:
    """A message in an LLM conversation.

    Fields:
        role: "user" | "assistant" | "system"
        content: The message text
    """
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM completion call.

    Fields:
        content: The generated text
        tool_calls: List of tool invocations (if any)
        usage: Token/cost metrics
        model_used: Actual model selected by ModelRouter (for logging/audit)
    """
    content: str
    tool_calls: list[dict] | None = None
    usage: dict | None = None
    model_used: str | None = None


@dataclass
class ToolDefinition:
    """Definition of a tool the LLM can call.

    Fields:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON schema for tool inputs
    """
    name: str
    description: str
    input_schema: dict


@dataclass
class TaskProfile:
    """Declares agent intent for ModelRouter-based model selection.

    Used to route different LLM tasks to appropriate models:
    - "complex-reasoning": Chain-of-thought, multi-step problems
    - "code-generation": IaC generation, structured outputs
    - "analysis": Report generation, summarization
    - "fast-lightweight": Quick decisions, simple responses
    - "orchestration": Multi-agent coordination

    Fields:
        profile: Task type (above values)
        max_tokens: Maximum response tokens
        temperature: Sampling temperature (0.0-1.0)
    """
    profile: str  # "complex-reasoning" | "code-generation" | "analysis" | "fast-lightweight" | "orchestration"
    max_tokens: int = 4096
    temperature: float = 0.2


class ILLMCompletionPort(ABC):
    """Abstracts over LLM providers (Azure OpenAI, Anthropic, etc.) with ModelRouter support.

    Methods route tasks through ModelRouter for intelligent model selection based on TaskProfile.
    """

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        """Generate a completion from an LLM.

        Args:
            system_prompt: System role message
            messages: Conversation history
            task_profile: Optional profile for ModelRouter-based model selection

        Returns:
            LLMResponse with generated content and model_used
        """
        ...

    @abstractmethod
    async def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
        tool_executor: callable,
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        """Generate a completion with tool-calling capability.

        Args:
            system_prompt: System role message
            messages: Conversation history
            tools: Available tools the LLM can invoke
            tool_executor: Callable to execute tool calls and return results
            task_profile: Optional profile for ModelRouter-based model selection

        Returns:
            LLMResponse with tool calls and final content
        """
        ...


# ============================================================================
# Infra Provider Port (TechSpec Section 2.1, lines 202-221)
# ============================================================================


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


# ============================================================================
# Source Control Port (TechSpec Section 2.1, lines 244-266)
# ============================================================================


@dataclass
class PRResult:
    """Result of creating a pull request.

    Fields:
        number: PR number/ID
        url: API URL for the PR
        html_url: Web URL for the PR
        state: PR state (open, closed, etc.)
        branch_name: Source branch name
    """
    number: int
    url: str
    html_url: str
    state: str
    branch_name: str


@dataclass
class PipelineStatus:
    """Status of a CI/CD pipeline run.

    Fields:
        status: "queued" | "in_progress" | "completed" | "failed"
        conclusion: "success" | "failure" | "cancelled" (null if in progress)
        plan_output: Output from the plan job (if available)
        run_url: URL to view the run
    """
    status: str  # "queued" | "in_progress" | "completed" | "failed"
    conclusion: str | None  # "success" | "failure" | "cancelled"
    plan_output: str | None = None
    run_url: str | None = None


class ISourceControlPort(ABC):
    """Abstracts over version control systems (GitHub, Azure DevOps, etc.).

    Manages branches, commits, PRs, and workflow triggers.
    """

    @abstractmethod
    async def create_branch(self, repo: str, branch: str, base: str) -> str:
        """Create a new branch.

        Args:
            repo: Repository name or URL
            branch: New branch name
            base: Base branch to branch from

        Returns:
            Created branch name
        """
        ...

    @abstractmethod
    async def commit_files(
        self, repo: str, branch: str, files: list[dict], message: str
    ) -> str:
        """Commit files to a branch.

        Args:
            repo: Repository name or URL
            branch: Target branch
            files: List of {"path": "...", "content": "..."} dicts
            message: Commit message

        Returns:
            Commit SHA
        """
        ...

    @abstractmethod
    async def create_pr(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> PRResult:
        """Create a pull request.

        Args:
            repo: Repository name or URL
            title: PR title
            body: PR description
            head: Source branch name
            base: Target branch name

        Returns:
            PRResult with PR details
        """
        ...

    @abstractmethod
    async def get_pipeline_status(self, repo: str, run_id: int) -> PipelineStatus:
        """Get status of a CI/CD pipeline run.

        Args:
            repo: Repository name or URL
            run_id: Run ID from CI/CD system

        Returns:
            PipelineStatus with current run state
        """
        ...

    @abstractmethod
    async def trigger_workflow(
        self, repo: str, workflow: str, ref: str, inputs: dict
    ) -> int:
        """Trigger a CI/CD workflow run.

        Args:
            repo: Repository name or URL
            workflow: Workflow name or file
            ref: Branch/tag/SHA to run on
            inputs: Workflow input parameters

        Returns:
            Run ID for later status checks
        """
        ...


# ============================================================================
# Policy Engine Port (TechSpec Section 2.1, lines 288-298)
# ============================================================================


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
    """Abstracts over policy validation (naming, tagging, security).

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


# ============================================================================
# Template Registry Port (TechSpec Section 2.1, lines 323-338)
# ============================================================================


@dataclass
class TemplateMetadata:
    """Metadata describing an IaC template.

    Fields:
        name: Template identifier
        description: Human-readable description
        azure_services: List of Azure service types (e.g., ["compute", "network"])
        complexity: "simple" | "moderate" | "complex"
        iac_languages: Supported languages (["terraform", "bicep"])
        parameters: Template input parameters
        tags: Search tags
        version: Template version
    """
    name: str
    description: str
    azure_services: list[str]
    complexity: str  # "simple" | "moderate" | "complex"
    iac_languages: list[str]
    parameters: list[dict]
    tags: list[str]
    version: str


@dataclass
class HydratedTemplate:
    """A template with variables applied.

    Fields:
        files: Generated IaC files
        metadata: Template metadata
        applied_standards: Applied naming/tagging standards
    """
    files: list[dict]  # [{"path": "...", "content": "..."}]
    metadata: TemplateMetadata
    applied_standards: dict  # {"naming": "...", "tags": {...}}


class ITemplateRegistryPort(ABC):
    """Abstracts over the knowledge wiki / template registry.

    Manages creation, search, and retrieval of IaC templates.
    """

    @abstractmethod
    async def search(self, query: str, filters: dict | None = None) -> list[TemplateMetadata]:
        """Search for templates by query and optional filters.

        Args:
            query: Search query text
            filters: Optional filters (e.g., {"complexity": "simple"})

        Returns:
            List of matching template metadata
        """
        ...

    @abstractmethod
    async def get_template(self, name: str, language: str) -> dict:
        """Retrieve a template by name and language.

        Args:
            name: Template name
            language: "terraform" or "bicep"

        Returns:
            Template definition dict
        """
        ...

    @abstractmethod
    async def hydrate(
        self, name: str, language: str, parameters: dict, standards: dict
    ) -> HydratedTemplate:
        """Generate IaC from a template with parameters and standards applied.

        Args:
            name: Template name
            language: "terraform" or "bicep"
            parameters: Variable values for the template
            standards: Naming/tagging standards to apply

        Returns:
            HydratedTemplate with generated IaC files
        """
        ...

    @abstractmethod
    async def publish(self, template: dict, metadata: TemplateMetadata) -> str:
        """Publish a new template to the registry.

        Args:
            template: Template definition
            metadata: Template metadata

        Returns:
            Published template name/ID
        """
        ...


# ============================================================================
# Observability Port (TechSpec Section 2.1, lines 345-355)
# ============================================================================


class IObservabilityPort(ABC):
    """Wraps OpenTelemetry for tracing, metrics, and logging.

    Lightweight abstraction for observability backends.
    """

    @abstractmethod
    def start_span(self, name: str, attributes: dict | None = None) -> object:
        """Start a tracing span.

        Args:
            name: Span name
            attributes: Optional span attributes

        Returns:
            Span context object (opaque to caller)
        """
        ...

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional metric tags
        """
        ...

    @abstractmethod
    def log(self, level: str, message: str, **kwargs) -> None:
        """Log a message.

        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            **kwargs: Additional log context
        """
        ...


# ============================================================================
# Subscription Discovery Port (TechSpec Section 2.1, lines 390-404)
# ============================================================================


@dataclass
class DiscoveredResource:
    """An Azure resource discovered in a subscription.

    Fields:
        resource_group: Resource group name
        resource_type: Azure resource type (e.g., "Microsoft.Compute/virtualMachines")
        name: Resource name
        location: Azure region
        tags: Resource tags
    """
    resource_group: str
    resource_type: str
    name: str
    location: str
    tags: dict = field(default_factory=dict)


@dataclass
class DiscoveredVNet:
    """A virtual network discovered in a subscription.

    Fields:
        name: VNet name
        resource_group: Resource group name
        address_space: CIDR blocks (e.g., ["10.0.0.0/16"])
        subnets: Subnet definitions
    """
    name: str
    resource_group: str
    address_space: list[str]
    subnets: list[dict]  # [{"name": "...", "address_prefix": "..."}]


@dataclass
class SubscriptionContext:
    """Complete context of an Azure subscription.

    Fields:
        subscription_id: Subscription ID
        subscription_name: Display name
        resource_groups: List of resource group names
        resources: Discovered resources
        vnets: Discovered virtual networks
        naming_patterns: Inferred naming patterns (e.g., ["rg-{env}-{app}-{region}"])
        quotas: Resource quotas and usage
        state_backends: Detected Terraform state storage locations
        available_regions: Regions available in subscription
    """
    subscription_id: str
    subscription_name: str
    resource_groups: list[str]
    resources: list[DiscoveredResource] = field(default_factory=list)
    vnets: list[DiscoveredVNet] = field(default_factory=list)
    naming_patterns: list[str] = field(default_factory=list)
    quotas: dict = field(default_factory=dict)
    state_backends: list[dict] = field(default_factory=list)
    available_regions: list[str] = field(default_factory=list)


class ISubscriptionDiscoveryPort(ABC):
    """Abstracts over Azure subscription discovery via Azure MCP Server.

    Queries existing Azure infrastructure to support intelligent code generation.
    """

    @abstractmethod
    async def discover(self, subscription_id: str) -> SubscriptionContext:
        """Discover resources and context in an Azure subscription.

        Args:
            subscription_id: Azure subscription ID

        Returns:
            SubscriptionContext with full subscription inventory
        """
        ...

    @abstractmethod
    async def check_sku_availability(
        self, subscription_id: str, resource_type: str, sku: str, region: str
    ) -> bool:
        """Check if a specific SKU is available in a region.

        Args:
            subscription_id: Azure subscription ID
            resource_type: Resource type (e.g., "Microsoft.Compute/virtualMachines")
            sku: SKU name (e.g., "Standard_D4s_v3")
            region: Azure region

        Returns:
            True if SKU is available in region
        """
        ...

    @abstractmethod
    async def check_quota(
        self, subscription_id: str, resource_type: str, region: str
    ) -> dict:
        """Check quota/limit status for a resource type in a region.

        Args:
            subscription_id: Azure subscription ID
            resource_type: Resource type (e.g., "Microsoft.Compute/cores")
            region: Azure region

        Returns:
            Dict with {"used": N, "limit": M} quota info
        """
        ...


# ============================================================================
# Legacy/Application Ports (existing, kept for backward compatibility)
# ============================================================================


# These ports use domain models from src.domain.models.models
# They are defined here for historical/compatibility reasons
# New code should prefer ports above

from src.domain.models.models import (
    CodeGenOutput,
    GeneratedFile,
    PlanResult as PlanResultPydantic,
    RequirementsHandoff,
    SubscriptionContext as SubscriptionContextPydantic,
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
