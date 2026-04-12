"""Application layer port interfaces and dataclasses."""

from __future__ import annotations

# LLM Completion
from src.application.ports.ports import (
    ILLMCompletionPort,
    LLMMessage,
    LLMResponse,
    TaskProfile,
    ToolDefinition,
)

# Infra Provider
from src.application.ports.ports import (
    ApplyResult,
    IInfraProviderPort,
    PlanResult,
    ValidationResult,
)

# Source Control
from src.application.ports.ports import (
    ISourceControlPort,
    PRResult,
    PipelineStatus,
)

# Policy Engine
from src.application.ports.ports import (
    IPolicyEnginePort,
    PolicyResult,
    PolicyViolation,
)

# Template Registry
from src.application.ports.ports import (
    HydratedTemplate,
    ITemplateRegistryPort,
    TemplateMetadata,
)

# Observability
from src.application.ports.ports import IObservabilityPort

# Subscription Discovery
from src.application.ports.ports import (
    DiscoveredResource,
    DiscoveredVNet,
    ISubscriptionDiscoveryPort,
    SubscriptionContext,
)

# Legacy/Application (for backward compatibility)
from src.application.ports.ports import (
    ICodeGenPort,
    ISecurityPort,
    IStandardsPort,
    IValidationPort,
    IDeployPort,
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
    # Legacy/Application
    "ICodeGenPort",
    "IValidationPort",
    "IStandardsPort",
    "ISecurityPort",
    "IDeployPort",
]
