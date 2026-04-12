"""Application layer port interfaces and dataclasses."""

from __future__ import annotations

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

# Legacy ports (backward compat — new code should prefer the canonical ports above)
from src.application.ports.ports import (
    ICodeGenPort,
    IDeployPort,
    ISecurityPort,
    IStandardsPort,
    IValidationPort,
)

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
