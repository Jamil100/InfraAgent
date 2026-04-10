# InfraAgent — Technical Specification Document

**Version:** 2.0  
**Date:** April 2026  
**Status:** Draft  
**Classification:** Internal — Microsoft Hackathon  
**Companion:** InfraAgent PRD v2.0  

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | April 2026 | Aligned with PRD v2.0: Added ModelRouter as default model selection strategy (replacing hardcoded model names). Added IaC Validation Pipeline as explicit stage (fmt/init/validate/lint). Added Azure subscription discovery to consulting flow. Defined generated code file structure conventions. Added AVM-first module strategy to CodeGen. Defined architecture diagram generation approach (Mermaid from IaC). Expanded plan-failure rework loop with error categorization and data flow. Added set-diff analysis for plan review (P1). Defined secret handling patterns for generated code. Added project type classification to consulting flow. Added subscription context to database schema. |
| 1.0 | April 2026 | Initial draft aligned with PRD v1.0. |

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Clean Architecture Implementation](#2-clean-architecture-implementation)
3. [Domain Layer](#3-domain-layer)
4. [Application Layer — Use Cases](#4-application-layer--use-cases)
5. [Agent Definitions](#5-agent-definitions)
6. [MCP Server Integration](#6-mcp-server-integration)
7. [Knowledge Wiki Schema](#7-knowledge-wiki-schema)
8. [Backend API Contracts](#8-backend-api-contracts)
9. [Database Schema](#9-database-schema)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Project Structure](#11-project-structure)
12. [Infrastructure as Code (InfraAgent Self-Deployment)](#12-infrastructure-as-code-infraagent-self-deployment)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Observability](#14-observability)
15. [Security](#15-security)
16. [Development Guidelines](#16-development-guidelines)
17. [Appendix A — Agent System Prompts](#appendix-a--agent-system-prompts)
18. [Appendix B — Sequence Diagrams](#appendix-b--sequence-diagrams)

---

## 1. Architecture Overview

### 1.1 Six-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                                   │
│  React / Next.js Frontend                                               │
│  ┌──────────┐ ┌──────────────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │Chat UI   │ │Self-Service      │ │File      │ │Architecture       │  │
│  │          │ │Catalog           │ │Explorer  │ │Diagram Viewer     │  │
│  └──────────┘ └──────────────────┘ └──────────┘ └───────────────────┘  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ REST + WebSocket (SSE)
┌────────────────────────────▼────────────────────────────────────────────┐
│                    API GATEWAY LAYER                                     │
│  Python (FastAPI)                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │/chat     │ │/catalog  │ │/deploy   │ │/webhook  │ │/health       │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                    APPLICATION LAYER                                    │
│  Use Cases + Agent Orchestration                                        │
│  ┌──────────────────┐ ┌────────────────┐ ┌────────────────────────┐     │
│  │ConsultUseCase    │ │GenerateUseCase │ │DeployUseCase           │     │
│  └──────────────────┘ └────────────────┘ └────────────────────────┘     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Orchestrator (Microsoft Agent Framework — graph workflow)        │   │
│  │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │   │
│  │ │Conslt│→│CdGen │→│Stds  │→│Secur │→│PR    │→│Deploy│→│Curat │   │   │
│  │ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                    DOMAIN LAYER  (pure business logic, zero deps)       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │NamingPolicy  │ │TaggingPolicy │ │SecurityPolicy│ │DeployPolicy  │    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                     │
│  │TemplateModel │ │ValidationRes │ │DeploymentPlan│                     │
│  └──────────────┘ └──────────────┘ └──────────────┘                     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ Port Interfaces
┌────────────────────────────▼────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER  (adapters)                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │AzureOpenAI   │ │TerraformCLI  │ │GitHubAdapter │ │CosmosDB      │    │
│  │Adapter       │ │Adapter       │ │              │ │Adapter       │    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │BicepCLI      │ │MCPClient     │ │AISearch      │ │KeyVault      │    │
│  │Adapter       │ │Adapter       │ │Adapter       │ │Adapter       │    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent runtime | Azure AI Foundry Agent Service (Hosted Agents) | Managed scaling, native MCP, model catalog, tracing |
| Model selection | Azure AI Foundry ModelRouter | Agents declare task profiles, not model names; cost-optimal routing across catalog |
| Orchestration | Microsoft Agent Framework (graph workflow) | Typed workflows, checkpointing, human-in-the-loop, handoff |
| Backend language | Python | Foundry SDK is Python-first; Agent Framework is Python-native |
| Frontend | React / Next.js / TypeScript | Team competency; Tailwind + shadcn/ui for rapid UI |
| IaC grounding | MCP servers (Terraform + Bicep + Azure) | Live registry schemas, zero hallucination |
| Architecture | Hexagonal (ports & adapters) | Business logic decoupled from framework/provider changes |
| API style | V2 conversations/responses | Future-proof; classic threads API retires March 2027 |
| State persistence | Azure PostgreSQL | Conversations, deployments, settings; reliable ACID |
| IaC for InfraAgent itself | Bicep | Meta-point for hackathon; dogfooding |

---

## 2. Clean Architecture Implementation

### 2.1 Port Interfaces

All cross-layer communication goes through abstract port interfaces defined in the application layer. Infrastructure adapters implement these ports.

```python
# src/application/ports/llm_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMMessage:
    role: str  # "user" | "assistant" | "system"
    content: str

@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] | None = None
    usage: dict | None = None
    model_used: str | None = None  # Actual model selected by ModelRouter

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict

@dataclass
class TaskProfile:
    """Declares agent intent for ModelRouter-based model selection."""
    profile: str  # "complex-reasoning" | "code-generation" | "analysis" | "fast-lightweight" | "orchestration"
    max_tokens: int = 4096
    temperature: float = 0.2

class ILLMCompletionPort(ABC):
    """Abstracts over LLM providers (Azure OpenAI, Anthropic, etc.) with ModelRouter support."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse: ...

    @abstractmethod
    async def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
        tool_executor: callable,
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse: ...
```

```python
# src/application/ports/infra_provider_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]

@dataclass
class PlanResult:
    success: bool
    output: str
    resources_to_create: int
    resources_to_modify: int
    resources_to_destroy: int
    estimated_cost: float | None = None

@dataclass
class ApplyResult:
    success: bool
    output: str
    resources_created: list[str]
    errors: list[str]

class IInfraProviderPort(ABC):
    """Abstracts over Terraform and Bicep."""

    @abstractmethod
    async def format_check(self, files: list[dict]) -> ValidationResult: ...

    @abstractmethod
    async def validate(self, files: list[dict]) -> ValidationResult: ...

    @abstractmethod
    async def lint(self, files: list[dict]) -> ValidationResult: ...

    @abstractmethod
    async def plan(self, files: list[dict], variables: dict) -> PlanResult: ...

    @abstractmethod
    async def apply(self, plan_id: str) -> ApplyResult: ...

    @abstractmethod
    def get_language(self) -> str: ...  # "terraform" | "bicep"
```

```python
# src/application/ports/source_control_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PRResult:
    number: int
    url: str
    html_url: str
    state: str
    branch_name: str

@dataclass
class PipelineStatus:
    status: str  # "queued" | "in_progress" | "completed" | "failed"
    conclusion: str | None  # "success" | "failure" | "cancelled"
    plan_output: str | None
    run_url: str | None

class ISourceControlPort(ABC):
    """Abstracts over GitHub (and future Azure DevOps)."""

    @abstractmethod
    async def create_branch(self, repo: str, branch: str, base: str) -> str: ...

    @abstractmethod
    async def commit_files(
        self, repo: str, branch: str, files: list[dict], message: str
    ) -> str: ...

    @abstractmethod
    async def create_pr(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> PRResult: ...

    @abstractmethod
    async def get_pipeline_status(self, repo: str, run_id: int) -> PipelineStatus: ...

    @abstractmethod
    async def trigger_workflow(
        self, repo: str, workflow: str, ref: str, inputs: dict
    ) -> int: ...
```

```python
# src/application/ports/policy_engine_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PolicyViolation:
    resource: str
    policy: str
    severity: str  # "critical" | "high" | "medium" | "low"
    expected: str
    actual: str
    remediation: str

@dataclass
class PolicyResult:
    passed: bool
    violations: list[PolicyViolation]

class IPolicyEnginePort(ABC):
    """Abstracts over policy evaluation (standards, security)."""

    @abstractmethod
    async def validate_naming(self, files: list[dict]) -> PolicyResult: ...

    @abstractmethod
    async def validate_tags(self, files: list[dict]) -> PolicyResult: ...

    @abstractmethod
    async def validate_security(self, files: list[dict]) -> PolicyResult: ...
```

```python
# src/application/ports/template_registry_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TemplateMetadata:
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
    files: list[dict]  # [{"path": "...", "content": "..."}]
    metadata: TemplateMetadata
    applied_standards: dict  # naming, tags applied

class ITemplateRegistryPort(ABC):
    """Abstracts over the knowledge wiki."""

    @abstractmethod
    async def search(self, query: str, filters: dict | None = None) -> list[TemplateMetadata]: ...

    @abstractmethod
    async def get_template(self, name: str, language: str) -> dict: ...

    @abstractmethod
    async def hydrate(
        self, name: str, language: str, parameters: dict, standards: dict
    ) -> HydratedTemplate: ...

    @abstractmethod
    async def publish(self, template: dict, metadata: TemplateMetadata) -> str: ...
```

```python
# src/application/ports/observability_port.py
from abc import ABC, abstractmethod

class IObservabilityPort(ABC):
    """Wraps OpenTelemetry for tracing, metrics, and logging."""

    @abstractmethod
    def start_span(self, name: str, attributes: dict | None = None) -> object: ...

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None: ...

    @abstractmethod
    def log(self, level: str, message: str, **kwargs) -> None: ...
```

```python
# src/application/ports/subscription_discovery_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class DiscoveredResource:
    resource_group: str
    resource_type: str
    name: str
    location: str
    tags: dict = field(default_factory=dict)

@dataclass
class DiscoveredVNet:
    name: str
    resource_group: str
    address_space: list[str]
    subnets: list[dict]  # [{"name": "...", "address_prefix": "..."}]

@dataclass
class SubscriptionContext:
    subscription_id: str
    subscription_name: str
    resource_groups: list[str]
    resources: list[DiscoveredResource]
    vnets: list[DiscoveredVNet]
    naming_patterns: list[str]  # Detected patterns e.g. ["rg-{env}-{app}-{region}"]
    quotas: dict  # {"Microsoft.Compute/virtualMachines": {"used": 10, "limit": 50}}
    state_backends: list[dict]  # Detected Terraform state storage accounts
    available_regions: list[str]

class ISubscriptionDiscoveryPort(ABC):
    """Abstracts over Azure subscription discovery via Azure MCP Server."""

    @abstractmethod
    async def discover(self, subscription_id: str) -> SubscriptionContext: ...

    @abstractmethod
    async def check_sku_availability(
        self, subscription_id: str, resource_type: str, sku: str, region: str
    ) -> bool: ...

    @abstractmethod
    async def check_quota(
        self, subscription_id: str, resource_type: str, region: str
    ) -> dict: ...
```

### 2.2 Dependency Injection

All adapters are wired at application startup. Use cases receive ports via constructor injection — never import infrastructure modules directly.

```python
# src/main.py  (composition root)
from src.infrastructure.adapters.azure_openai_adapter import AzureOpenAIAdapter
from src.infrastructure.adapters.terraform_adapter import TerraformAdapter
from src.infrastructure.adapters.bicep_adapter import BicepAdapter
from src.infrastructure.adapters.github_adapter import GitHubAdapter
from src.infrastructure.adapters.policy_adapter import PolicyAdapter
from src.infrastructure.adapters.template_registry_adapter import TemplateRegistryAdapter
from src.infrastructure.adapters.otel_adapter import OpenTelemetryAdapter
from src.infrastructure.adapters.subscription_discovery_adapter import SubscriptionDiscoveryAdapter
from src.application.use_cases.consult import ConsultUseCase
from src.application.use_cases.generate import GenerateUseCase
from src.application.use_cases.deploy import DeployUseCase

def create_app():
    # Infrastructure adapters
    llm = AzureOpenAIAdapter(endpoint=..., credential=..., model_router_enabled=True)
    github = GitHubAdapter(token=...)
    policy = PolicyAdapter(standards_repo=...)
    templates = TemplateRegistryAdapter(wiki_repo=...)
    observability = OpenTelemetryAdapter(connection_string=...)
    subscription_discovery = SubscriptionDiscoveryAdapter(credential=...)

    # IaC providers (selected at runtime per user request)
    terraform = TerraformAdapter()
    bicep = BicepAdapter()
    infra_providers = {"terraform": terraform, "bicep": bicep}

    # Use cases (injected with ports — no framework leakage)
    consult_uc = ConsultUseCase(
        llm=llm, templates=templates,
        subscription_discovery=subscription_discovery, observability=observability,
    )
    generate_uc = GenerateUseCase(
        llm=llm, policy=policy, templates=templates,
        infra_providers=infra_providers, observability=observability,
    )
    deploy_uc = DeployUseCase(
        github=github, infra_providers=infra_providers, observability=observability,
    )

    # FastAPI app with use cases injected
    app = build_fastapi_app(consult_uc, generate_uc, deploy_uc)
    return app
```

---

## 3. Domain Layer

The domain layer contains pure business logic with zero external dependencies. Every class is a plain Python dataclass or function — no imports from `azure`, `openai`, `fastapi`, or any framework.

### 3.1 Domain Models

```python
# src/domain/models/deployment.py
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class DeploymentStage(Enum):
    CONSULTING = "consulting"
    DISCOVERING_SUBSCRIPTION = "discovering_subscription"
    GENERATING = "generating"
    VALIDATING_IAC = "validating_iac"              # fmt/init/validate/lint
    VALIDATING_STANDARDS = "validating_standards"
    SCANNING_SECURITY = "scanning_security"
    AWAITING_CODE_REVIEW = "awaiting_code_review"        # H1
    CREATING_PR = "creating_pr"
    RUNNING_PLAN = "running_plan"
    REWORKING_PLAN_FAILURE = "reworking_plan_failure"     # Loop 2
    AWAITING_PLAN_REVIEW = "awaiting_plan_review"        # H2
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProjectType(Enum):
    """Project type classification determines WAF pillar depth and requirements gathering intensity."""
    DEMO = "demo"                  # Minimal WAF; quick generation
    PRODUCTION = "production"      # Cost, reliability, security, operational excellence
    ENTERPRISE = "enterprise"      # Comprehensive WAF; all pillars
    REGULATED = "regulated"        # Comprehensive WAF + compliance frameworks

class IaCLanguage(Enum):
    TERRAFORM = "terraform"
    BICEP = "bicep"

class DeploymentPath(Enum):
    CHAT_CUSTOM = "chat_custom"       # Full agent pipeline
    CATALOG_TEMPLATE = "catalog_template"  # Template fast-path

@dataclass
class GeneratedFile:
    path: str
    content: str
    language: str  # "hcl" | "bicep" | "yaml" | "json"
    is_new: bool = True

@dataclass
class DeploymentRequest:
    id: str
    conversation_id: str
    path: DeploymentPath
    iac_language: IaCLanguage
    requirements: str
    project_type: ProjectType = ProjectType.PRODUCTION
    subscription_id: str | None = None
    subscription_context: dict | None = None  # Serialized SubscriptionContext
    template_name: str | None = None
    template_parameters: dict | None = None
    files: list[GeneratedFile] = field(default_factory=list)
    stage: DeploymentStage = DeploymentStage.CONSULTING
    pr_number: int | None = None
    pr_url: str | None = None
    plan_output: str | None = None
    plan_error_category: str | None = None  # Categorized plan failure
    plan_rework_iteration: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Conversation:
    id: str
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    deployment_request_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 3.2 Domain Policies (Deterministic Business Rules)

```python
# src/domain/policies/naming_policy.py
import re
from dataclasses import dataclass

@dataclass
class NamingRule:
    resource_type: str
    pattern: str     # regex pattern
    template: str    # human-readable template e.g. "vm-{env}-{app}-{seq}"
    example: str

# Organization naming conventions — loaded from standards repo at startup
DEFAULT_NAMING_RULES: list[NamingRule] = [
    NamingRule("azurerm_resource_group",   r"^rg-\w+-\w+-\w+$",     "rg-{env}-{app}-{region}",     "rg-prod-web-eastus"),
    NamingRule("azurerm_virtual_network",  r"^vnet-\w+-\w+-\d{3}$", "vnet-{env}-{region}-{seq}",   "vnet-prod-eastus-001"),
    NamingRule("azurerm_subnet",           r"^snet-\w+-\w+-\d{3}$", "snet-{env}-{purpose}-{seq}",  "snet-prod-app-001"),
    NamingRule("azurerm_virtual_machine",  r"^vm-\w+-\w+-\d{3}$",   "vm-{env}-{app}-{seq}",        "vm-prod-web-001"),
    NamingRule("azurerm_storage_account",  r"^st\w{3,20}\d{3}$",    "st{env}{app}{seq}",           "stprodweb001"),
    NamingRule("azurerm_network_security_group", r"^nsg-\w+-\w+-\d{3}$", "nsg-{env}-{purpose}-{seq}", "nsg-prod-web-001"),
]

def validate_resource_name(resource_type: str, name: str, rules: list[NamingRule] = None) -> tuple[bool, str | None]:
    """Pure function. Returns (is_valid, error_message_or_none)."""
    rules = rules or DEFAULT_NAMING_RULES
    for rule in rules:
        if rule.resource_type == resource_type:
            if re.match(rule.pattern, name):
                return True, None
            return False, f"Resource '{name}' does not match pattern '{rule.template}' (example: {rule.example})"
    return True, None  # No rule for this resource type — allow


# src/domain/policies/tagging_policy.py
from dataclasses import dataclass

@dataclass
class TagRule:
    name: str
    enforcement: str  # "required" | "recommended" | "auto"
    description: str

DEFAULT_REQUIRED_TAGS: list[TagRule] = [
    TagRule("environment", "required",    "Deployment stage (dev, staging, prod)"),
    TagRule("owner",       "required",    "Team or individual responsible"),
    TagRule("cost-center", "required",    "Finance cost allocation code"),
    TagRule("application", "recommended", "Application or service name"),
    TagRule("created-by",  "auto",        "Deployment method (infraagent)"),
]

def validate_tags(resource_tags: dict, rules: list[TagRule] = None) -> list[str]:
    """Returns list of violation messages. Empty list = all good."""
    rules = rules or DEFAULT_REQUIRED_TAGS
    violations = []
    for rule in rules:
        if rule.enforcement == "required" and rule.name not in resource_tags:
            violations.append(f"Missing required tag '{rule.name}': {rule.description}")
    return violations


# src/domain/policies/security_policy.py
SECURITY_RULES = [
    {"id": "SEC-001", "severity": "critical", "rule": "No public blob access",           "description": "Blob containers must disable public access"},
    {"id": "SEC-002", "severity": "critical", "rule": "No inbound RDP/SSH from internet", "description": "Block 3389/22 from 0.0.0.0/0"},
    {"id": "SEC-003", "severity": "high",     "rule": "HTTPS only",                       "description": "All web endpoints must use HTTPS"},
    {"id": "SEC-004", "severity": "high",     "rule": "TLS 1.2 minimum",                  "description": "Enforce TLS 1.2+ on all connections"},
    {"id": "SEC-005", "severity": "high",     "rule": "Encryption at rest",                "description": "All storage and disks must be encrypted"},
    {"id": "SEC-006", "severity": "high",     "rule": "NSG on all subnets",                "description": "Every subnet must have an attached NSG"},
    {"id": "SEC-007", "severity": "medium",   "rule": "Managed disks only",                "description": "VMs must use managed disks"},
]
```

### 3.3 Domain Services

```python
# src/domain/services/standards_service.py
from src.domain.policies.naming_policy import validate_resource_name, NamingRule
from src.domain.policies.tagging_policy import validate_tags, TagRule
from dataclasses import dataclass

@dataclass
class StandardsViolation:
    resource: str
    category: str  # "naming" | "tagging" | "structural"
    message: str
    severity: str

@dataclass
class StandardsResult:
    passed: bool
    violations: list[StandardsViolation]

def validate_standards(
    parsed_resources: list[dict],  # [{"type": "azurerm_virtual_machine", "name": "...", "tags": {...}}]
    naming_rules: list[NamingRule] | None = None,
    tag_rules: list[TagRule] | None = None,
) -> StandardsResult:
    """
    Pure domain function. No I/O, no LLM, no external calls.
    Takes parsed resource data and returns structured violations.
    """
    violations = []

    for resource in parsed_resources:
        # Naming validation
        valid, error = validate_resource_name(resource["type"], resource["name"], naming_rules)
        if not valid:
            violations.append(StandardsViolation(
                resource=resource["name"],
                category="naming",
                message=error,
                severity="high",
            ))

        # Tag validation
        tags = resource.get("tags", {})
        tag_errors = validate_tags(tags, tag_rules)
        for te in tag_errors:
            violations.append(StandardsViolation(
                resource=resource["name"],
                category="tagging",
                message=te,
                severity="high",
            ))

    return StandardsResult(passed=len(violations) == 0, violations=violations)
```

---

## 4. Application Layer — Use Cases

Use cases orchestrate domain logic and port calls. They contain no framework-specific code.

### 4.1 ConsultUseCase

```python
# src/application/use_cases/consult.py
from dataclasses import dataclass
from src.application.ports.llm_port import ILLMCompletionPort, LLMMessage, TaskProfile
from src.application.ports.template_registry_port import ITemplateRegistryPort
from src.application.ports.observability_port import IObservabilityPort
from src.application.ports.subscription_discovery_port import ISubscriptionDiscoveryPort, SubscriptionContext
from src.domain.models.deployment import ProjectType

@dataclass
class ConsultResult:
    response: str
    recommended_template: str | None = None
    recommended_path: str | None = None  # "catalog" | "custom"
    requirements_complete: bool = False
    project_type: ProjectType | None = None
    subscription_context: SubscriptionContext | None = None

class ConsultUseCase:
    TASK_PROFILE = TaskProfile(profile="complex-reasoning")

    def __init__(
        self,
        llm: ILLMCompletionPort,
        templates: ITemplateRegistryPort,
        subscription_discovery: ISubscriptionDiscoveryPort,
        observability: IObservabilityPort,
    ):
        self._llm = llm
        self._templates = templates
        self._discovery = subscription_discovery
        self._obs = observability

    async def run(
        self,
        user_message: str,
        conversation_history: list[LLMMessage],
        domain_skill: str | None = None,
        subscription_id: str | None = None,
    ) -> ConsultResult:
        """
        Runs one turn of the consulting agent conversation.
        The consulting agent:
        1. Classifies project type (demo/production/enterprise/regulated)
        2. Runs subscription discovery to inventory existing resources
        3. Asks probing questions based on the loaded domain skill
        4. Searches the knowledge wiki for matching templates
        5. Recommends a template (catalog path) or custom generation
        """
        span = self._obs.start_span("consult_use_case", {"skill": domain_skill or "default"})

        # Subscription discovery (runs once when subscription_id is first provided)
        subscription_context = None
        if subscription_id:
            subscription_context = await self._discover_subscription(subscription_id)

        # Build system prompt with domain skill context
        system_prompt = self._build_system_prompt(domain_skill, subscription_context)

        # Search wiki for potentially relevant templates based on conversation so far
        template_matches = await self._templates.search(user_message)
        template_context = self._format_template_matches(template_matches)

        # Append template context to the conversation
        augmented_message = user_message
        if template_context:
            augmented_message += f"\n\n[SYSTEM: Available templates that might match: {template_context}]"

        messages = conversation_history + [LLMMessage(role="user", content=augmented_message)]

        # Call LLM with ModelRouter task profile
        response = await self._llm.complete(system_prompt, messages, task_profile=self.TASK_PROFILE)

        # Parse response for routing signals
        recommended_template = self._extract_template_recommendation(response.content)
        requirements_complete = self._check_requirements_complete(response.content)
        project_type = self._extract_project_type(response.content)

        path = None
        if recommended_template:
            path = "catalog"
        elif requirements_complete:
            path = "custom"

        self._obs.record_metric("consult_turns", 1.0)
        return ConsultResult(
            response=response.content,
            recommended_template=recommended_template,
            recommended_path=path,
            requirements_complete=requirements_complete,
            project_type=project_type,
            subscription_context=subscription_context,
        )

    async def _discover_subscription(self, subscription_id: str) -> SubscriptionContext:
        """Connects to Azure subscription via MCP to inventory existing resources."""
        span = self._obs.start_span("subscription_discovery", {"subscription": subscription_id})
        context = await self._discovery.discover(subscription_id)
        self._obs.record_metric("subscription_discoveries", 1.0)
        return context

    def _build_system_prompt(self, domain_skill: str | None, subscription_context: SubscriptionContext | None) -> str:
        base = CONSULTING_AGENT_SYSTEM_PROMPT
        if domain_skill:
            base += f"\n\n## Domain Skill\n\n{domain_skill}"
        if subscription_context:
            base += f"\n\n## Subscription Context\n\n"
            base += f"Subscription: {subscription_context.subscription_name} ({subscription_context.subscription_id})\n"
            base += f"Resource groups: {', '.join(subscription_context.resource_groups[:10])}\n"
            base += f"Existing VNets: {len(subscription_context.vnets)}\n"
            base += f"Detected naming patterns: {', '.join(subscription_context.naming_patterns)}\n"
            if subscription_context.state_backends:
                base += f"Terraform state backends detected: {len(subscription_context.state_backends)}\n"
        return base

    def _format_template_matches(self, matches) -> str:
        if not matches:
            return ""
        return "\n".join(f"- {m.name}: {m.description} (services: {', '.join(m.azure_services)})" for m in matches[:5])

    def _extract_template_recommendation(self, content: str) -> str | None:
        # Parse for structured recommendation markers
        if "[RECOMMEND_TEMPLATE:" in content:
            start = content.index("[RECOMMEND_TEMPLATE:") + len("[RECOMMEND_TEMPLATE:")
            end = content.index("]", start)
            return content[start:end].strip()
        return None

    def _check_requirements_complete(self, content: str) -> bool:
        return "[REQUIREMENTS_COMPLETE]" in content

    def _extract_project_type(self, content: str) -> ProjectType | None:
        """Parse for project type classification markers."""
        for pt in ProjectType:
            marker = f"[PROJECT_TYPE:{pt.value.upper()}]"
            if marker in content:
                return pt
        return None
```

### 4.2 GenerateUseCase

```python
# src/application/use_cases/generate.py
from dataclasses import dataclass
from src.application.ports.llm_port import ILLMCompletionPort, LLMMessage, TaskProfile
from src.application.ports.infra_provider_port import IInfraProviderPort
from src.application.ports.policy_engine_port import IPolicyEnginePort
from src.application.ports.template_registry_port import ITemplateRegistryPort
from src.application.ports.observability_port import IObservabilityPort
from src.domain.models.deployment import GeneratedFile, IaCLanguage, DeploymentPath, ProjectType

MAX_MAKER_CHECKER_ITERATIONS = 3
MAX_PLAN_REWORK_ITERATIONS = 2

# Generated code file structure conventions
FILE_STRUCTURE_TERRAFORM = {
    "root": [
        "main.tf",            # Root module composition
        "variables.tf",       # Input variables
        "outputs.tf",         # Output values
        "providers.tf",       # Provider configuration with version pins
        "backend.tf",         # Remote state backend configuration
        "terraform.tfvars",   # Variable values (no secrets)
        "locals.tf",          # Local values and computed expressions
    ],
    "modules_dir": "modules/",  # modules/<resource>/{main,variables,outputs}.tf
    "docs_dir": "docs/",        # docs/architecture.mermaid
}

FILE_STRUCTURE_BICEP = {
    "root": [
        "main.bicep",            # Root module
        "main.bicepparam",       # Parameter file
    ],
    "modules_dir": "modules/",   # modules/<resource>.bicep
    "docs_dir": "docs/",         # docs/architecture.mermaid
}

# Secret handling patterns for generated code
SECRET_HANDLING_RULES = [
    "Never hardcode secrets, passwords, connection strings, or API keys in IaC files.",
    "Use Azure Key Vault references for all sensitive values.",
    "Mark sensitive variables with `sensitive = true` (Terraform) or `@secure()` decorator (Bicep).",
    "Use Managed Identity for service-to-service authentication where possible.",
    "Reference secrets via data sources: `data.azurerm_key_vault_secret` (Terraform) or `existing` keyword (Bicep).",
    "Never output sensitive values — mark outputs as `sensitive = true` (Terraform) or omit them (Bicep).",
]

@dataclass
class GenerateResult:
    files: list[GeneratedFile]
    standards_passed: bool
    security_passed: bool
    violations: list[dict]
    iteration_count: int
    assistant_message: str
    diagram_mermaid: str | None = None  # Architecture diagram in Mermaid syntax

@dataclass
class PlanFailureAnalysis:
    """Structured analysis of a plan failure for rework loop."""
    category: str  # "resource_conflict" | "sku_unavailable" | "quota_exceeded" | "auth_failure" | "provider_mismatch" | "module_error"
    error_message: str
    stderr: str
    exit_code: int
    is_fixable_in_code: bool
    suggested_fix: str | None = None

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
    ):
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
        mcp_tool_executor: callable,
        project_type: ProjectType = ProjectType.PRODUCTION,
        subscription_context: dict | None = None,
    ) -> GenerateResult:
        """
        Full custom generation pipeline:
        CodeGen (AVM-first) → IaC Validation Pipeline (fmt/validate/lint) → Standards → Security → Diagram
        Loops if violations, max 3x total across all checkers.
        """
        provider = self._infra[language.value]
        iteration = 0
        all_violations = []

        while iteration < MAX_MAKER_CHECKER_ITERATIONS:
            iteration += 1
            self._obs.start_span("generate_iteration", {"iteration": iteration, "language": language.value})

            # Step 1: CodeGen agent generates code (AVM-first, secret-safe)
            files = await self._generate_code(
                requirements, language, conversation_history, mcp_tool_executor,
                all_violations, project_type, subscription_context,
            )

            # Step 2: IaC Validation Pipeline (deterministic toolchain — runs BEFORE LLM-based checks)
            #   Terraform: fmt → init → validate → tflint
            #   Bicep: build → format → bicep linter
            iac_validation = await self._run_iac_validation_pipeline(provider, files, language)
            if not iac_validation["passed"]:
                all_violations.extend([{"type": "iac_validation", "error": e} for e in iac_validation["errors"]])
                continue

            # Step 3: Standards agent validates (naming, tagging)
            standards_result = await self._policy.validate_naming([{"path": f.path, "content": f.content} for f in files])
            tags_result = await self._policy.validate_tags([{"path": f.path, "content": f.content} for f in files])

            standards_passed = standards_result.passed and tags_result.passed
            if not standards_passed:
                all_violations.extend([{"type": "standards", "violation": v.__dict__} for v in standards_result.violations + tags_result.violations])
                continue

            # Step 4: Security agent scans
            security_result = await self._policy.validate_security([{"path": f.path, "content": f.content} for f in files])
            security_passed = security_result.passed

            if not security_passed:
                critical_high = [v for v in security_result.violations if v.severity in ("critical", "high")]
                if critical_high:
                    all_violations.extend([{"type": "security", "violation": v.__dict__} for v in critical_high])
                    continue

            # Step 5: Generate architecture diagram from IaC code
            diagram = await self._generate_diagram(files, language)

            # All checks passed
            self._obs.record_metric("generate_iterations", float(iteration))
            return GenerateResult(
                files=files,
                standards_passed=True,
                security_passed=security_passed,
                violations=[{"type": "security", "violation": v.__dict__} for v in security_result.violations] if not security_passed else [],
                iteration_count=iteration,
                assistant_message=f"Generated {len(files)} files in {iteration} iteration(s). All standards and security checks passed.",
                diagram_mermaid=diagram,
            )

        # Max iterations reached — return best effort with violations
        self._obs.record_metric("generate_max_iterations_reached", 1.0)
        return GenerateResult(
            files=files if 'files' in dir() else [],
            standards_passed=False,
            security_passed=False,
            violations=all_violations,
            iteration_count=iteration,
            assistant_message=f"Reached max iterations ({MAX_MAKER_CHECKER_ITERATIONS}). Remaining violations require manual review.",
        )

    async def run_catalog_path(
        self,
        template_name: str,
        language: IaCLanguage,
        parameters: dict,
        standards: dict,
    ) -> GenerateResult:
        """
        Catalog fast-path: hydrate template with parameters + org standards.
        Skips iterative codegen/standards/security loops (templates are pre-validated).
        """
        hydrated = await self._templates.hydrate(template_name, language.value, parameters, standards)
        provider = self._infra[language.value]

        # Validate syntax only (standards are baked in during hydration)
        validation = await provider.validate([{"path": f["path"], "content": f["content"]} for f in hydrated.files])

        files = [GeneratedFile(path=f["path"], content=f["content"], language=language.value) for f in hydrated.files]

        return GenerateResult(
            files=files,
            standards_passed=True,
            security_passed=True,
            violations=[{"type": "syntax", "error": e} for e in validation.errors] if not validation.valid else [],
            iteration_count=1,
            assistant_message=f"Template '{template_name}' hydrated with {len(files)} files.",
        )

    async def _generate_code(self, requirements, language, history, tool_executor, prior_violations,
                              project_type=ProjectType.PRODUCTION, subscription_context=None) -> list[GeneratedFile]:
        """Calls CodeGen agent via LLM with MCP tools. Enforces AVM-first and secret handling."""
        system_prompt = self._build_codegen_prompt(language, prior_violations, project_type, subscription_context)
        messages = history + [LLMMessage(role="user", content=requirements)]

        # MCP tools for code generation
        tools = self._get_mcp_tools(language)

        response = await self._llm.complete_with_tools(
            system_prompt, messages, tools, tool_executor, task_profile=self.CODEGEN_PROFILE
        )
        return self._parse_generated_files(response.content, language)

    async def _run_iac_validation_pipeline(
        self, provider: IInfraProviderPort, files: list[GeneratedFile], language: IaCLanguage
    ) -> dict:
        """
        Deterministic IaC validation pipeline. Runs BEFORE any LLM-based review.
        
        Terraform: terraform fmt -check → terraform init → terraform validate → tflint
        Bicep:     bicep build → bicep format --verify → bicep linter rules
        
        Returns {"passed": bool, "errors": list[str], "warnings": list[str]}
        """
        self._obs.start_span("iac_validation_pipeline", {"language": language.value})
        file_dicts = [{"path": f.path, "content": f.content} for f in files]

        # Step 1: Format check (non-destructive)
        fmt_result = await provider.format_check(file_dicts)
        if not fmt_result.valid:
            return {"passed": False, "errors": [f"Format: {e}" for e in fmt_result.errors], "warnings": []}

        # Step 2: Syntax validation (init + validate for TF, build for Bicep)
        validation = await provider.validate(file_dicts)
        if not validation.valid:
            return {"passed": False, "errors": [f"Validate: {e}" for e in validation.errors], "warnings": validation.warnings}

        # Step 3: Lint (tflint for TF, bicep linter for Bicep)
        lint_result = await provider.lint(file_dicts)
        if not lint_result.valid:
            return {"passed": False, "errors": [f"Lint: {e}" for e in lint_result.errors], "warnings": lint_result.warnings}

        return {"passed": True, "errors": [], "warnings": lint_result.warnings}

    async def _generate_diagram(self, files: list[GeneratedFile], language: IaCLanguage) -> str | None:
        """
        Generate a Mermaid architecture diagram from the IaC code.
        Uses a lightweight LLM call to parse resource definitions and produce a Mermaid graph.
        The diagram is stored alongside the generated code as docs/architecture.mermaid.
        """
        self._obs.start_span("generate_diagram")
        code_summary = "\n\n".join([f"## {f.path}\n```{f.language}\n{f.content}\n```" for f in files[:10]])
        system_prompt = (
            "You are a diagram generator. Given IaC code, produce a Mermaid architecture diagram "
            "showing all Azure resources, their relationships (network connections, dependencies, data flow), "
            "and groupings (resource groups, subnets). Output ONLY the Mermaid code, no explanation."
        )
        messages = [LLMMessage(role="user", content=f"Generate a Mermaid architecture diagram for:\n\n{code_summary}")]
        response = await self._llm.complete(system_prompt, messages, task_profile=self.DIAGRAM_PROFILE)
        return response.content.strip()

    def _categorize_plan_failure(self, stderr: str, exit_code: int) -> PlanFailureAnalysis:
        """
        Categorize a plan failure to determine if it's fixable in code.
        Used by the plan-failure rework loop (Loop 2).
        """
        error_lower = stderr.lower()

        if "already exists" in error_lower or "resource group" in error_lower and "exists" in error_lower:
            return PlanFailureAnalysis("resource_conflict", stderr, stderr, exit_code, True,
                                       "Use data source to reference existing resource or adjust naming")
        elif "not available" in error_lower and ("sku" in error_lower or "vm size" in error_lower):
            return PlanFailureAnalysis("sku_unavailable", stderr, stderr, exit_code, True,
                                       "Query Azure MCP for alternative SKUs/regions")
        elif "quota" in error_lower or "exceeded" in error_lower:
            return PlanFailureAnalysis("quota_exceeded", stderr, stderr, exit_code, False,
                                       "Requires manual quota increase — escalate to user")
        elif "authorization" in error_lower or "permission" in error_lower or "forbidden" in error_lower:
            return PlanFailureAnalysis("auth_failure", stderr, stderr, exit_code, False,
                                       "Cannot be fixed in code — escalate to user")
        elif "unsupported attribute" in error_lower or "provider" in error_lower and "version" in error_lower:
            return PlanFailureAnalysis("provider_mismatch", stderr, stderr, exit_code, True,
                                       "Update provider version pin and re-validate")
        elif "invalid value" in error_lower or "variable" in error_lower:
            return PlanFailureAnalysis("module_error", stderr, stderr, exit_code, True,
                                       "Fix variable value or type based on module docs via MCP")
        else:
            return PlanFailureAnalysis("unknown", stderr, stderr, exit_code, True,
                                       "Analyze error and attempt targeted fix")

    def _build_codegen_prompt(self, language: IaCLanguage, prior_violations: list,
                               project_type: ProjectType = ProjectType.PRODUCTION,
                               subscription_context: dict | None = None) -> str:
        prompt = CODEGEN_AGENT_SYSTEM_PROMPT_TERRAFORM if language == IaCLanguage.TERRAFORM else CODEGEN_AGENT_SYSTEM_PROMPT_BICEP

        # AVM-first module strategy
        prompt += "\n\n## AVM-First Module Strategy\n\n"
        prompt += "You MUST prefer Azure Verified Modules (AVM) over raw resource declarations for any resource where an AVM module exists.\n"
        if language == IaCLanguage.TERRAFORM:
            prompt += 'Use `source = "Azure/avm-res-{service}-{resource}/azurerm"` with version pinning via `version = "~> x.y"`.\n'
            prompt += "Always check AVM availability via MCP tool `search_modules` with query `avm-res-` before writing raw resources.\n"
        else:
            prompt += "Use AVM Bicep modules via `br/public:avm/res/{service}/{resource}:{version}`.\n"
            prompt += "Always check AVM availability via MCP tool `list_avm_metadata` before writing raw resources.\n"

        # Secret handling patterns
        prompt += "\n\n## Secret Handling Rules\n\n"
        for rule in SECRET_HANDLING_RULES:
            prompt += f"- {rule}\n"

        # File structure conventions
        file_structure = FILE_STRUCTURE_TERRAFORM if language == IaCLanguage.TERRAFORM else FILE_STRUCTURE_BICEP
        prompt += f"\n\n## File Structure\n\nGenerate files following this structure:\n"
        prompt += f"Root files: {', '.join(file_structure['root'])}\n"
        prompt += f"Modules directory: {file_structure['modules_dir']}<resource>/ (one module per logical resource group)\n"
        prompt += f"Documentation: {file_structure['docs_dir']}architecture.mermaid\n"

        # Project type → WAF depth
        prompt += f"\n\n## Project Type: {project_type.value}\n\n"
        if project_type == ProjectType.DEMO:
            prompt += "Minimal WAF compliance. Prioritize simplicity and speed.\n"
        elif project_type == ProjectType.PRODUCTION:
            prompt += "Apply WAF pillars: Cost Optimization, Reliability, Security, Operational Excellence.\n"
        elif project_type in (ProjectType.ENTERPRISE, ProjectType.REGULATED):
            prompt += "Comprehensive WAF compliance across all pillars. Include diagnostic settings, private endpoints, and zone redundancy.\n"

        # Subscription context
        if subscription_context:
            prompt += f"\n\n## Subscription Context\n\n{subscription_context}\n"
            prompt += "Use existing resources where appropriate (via data sources). Avoid CIDR conflicts with existing VNets.\n"

        if prior_violations:
            prompt += "\n\n## Previous Violations to Fix\n\n"
            for v in prior_violations[-5:]:  # Last 5 violations
                prompt += f"- {v}\n"
        return prompt

    def _get_mcp_tools(self, language: IaCLanguage) -> list:
        # Returns tool definitions from the appropriate MCP server
        # Loaded at startup and cached
        ...

    def _parse_generated_files(self, content: str, language: IaCLanguage) -> list[GeneratedFile]:
        # Parses LLM output for ```hcl file=path or ```bicep file=path blocks
        ...
```

### 4.3 DeployUseCase

```python
# src/application/use_cases/deploy.py
from dataclasses import dataclass
from src.application.ports.source_control_port import ISourceControlPort, PRResult, PipelineStatus
from src.application.ports.infra_provider_port import IInfraProviderPort
from src.application.ports.observability_port import IObservabilityPort
from src.domain.models.deployment import GeneratedFile, IaCLanguage

@dataclass
class DeployResult:
    pr: PRResult | None = None
    plan: PipelineStatus | None = None
    apply: PipelineStatus | None = None
    error: str | None = None

class DeployUseCase:
    def __init__(
        self,
        github: ISourceControlPort,
        infra_providers: dict[str, IInfraProviderPort],
        observability: IObservabilityPort,
    ):
        self._github = github
        self._infra = infra_providers
        self._obs = observability

    async def create_pr(
        self,
        repo: str,
        files: list[GeneratedFile],
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PRResult:
        """Creates branch, commits all files atomically, opens PR."""
        branch_name = f"infraagent/{title.lower().replace(' ', '-')[:50]}"
        await self._github.create_branch(repo, branch_name, base_branch)

        file_dicts = [{"path": f.path, "content": f.content} for f in files]
        await self._github.commit_files(repo, branch_name, file_dicts, f"feat: {title} (InfraAgent)")

        pr = await self._github.create_pr(repo, title, body, branch_name, base_branch)
        self._obs.record_metric("prs_created", 1.0)
        return pr

    async def get_plan_status(self, repo: str, run_id: int) -> PipelineStatus:
        """Polls GitHub Actions for plan/apply status."""
        return await self._github.get_pipeline_status(repo, run_id)

    async def trigger_apply(self, repo: str, workflow: str, ref: str, inputs: dict) -> int:
        """Triggers terraform apply / az deployment create via GitHub Actions."""
        run_id = await self._github.trigger_workflow(repo, workflow, ref, inputs)
        self._obs.record_metric("deployments_triggered", 1.0)
        return run_id
```

---

## 5. Agent Definitions

Each agent is registered with Azure AI Foundry Agent Service as a Hosted Agent. The orchestrator coordinates them using the Microsoft Agent Framework's graph workflow API.

### 5.1 Agent Registry

```python
# src/infrastructure/agents/registry.py
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool, FunctionTool
from azure.identity import DefaultAzureCredential

FOUNDRY_ENDPOINT = "https://<resource>.ai.azure.com/api/projects/<project>"

# ModelRouter task profiles — agents declare intent, not model names.
# ModelRouter routes to optimal model based on cost, capability, and availability.
#
# | Profile              | Primary Candidate | Fallback Candidates               |
# |----------------------|-------------------|-----------------------------------|
# | complex-reasoning    | GPT-4o            | GPT-4.1                           |
# | code-generation      | GPT-4o            | Claude 3.5 Sonnet (via catalog)   |
# | analysis             | GPT-4o-mini       | GPT-4o                            |
# | fast-lightweight     | GPT-4o-mini       | Phi-4                             |
# | orchestration        | GPT-4o            | GPT-4o-mini                       |

AGENT_CONFIGS = {
    "orchestrator": {
        "task_profile": "orchestration",
        "instructions_file": "prompts/orchestrator.md",
        "tools": [],  # Uses agent-to-agent handoff
    },
    "consulting": {
        "task_profile": "complex-reasoning",
        "instructions_file": "prompts/consulting_agent.md",
        "tools": [
            MCPTool(server_label="azure", server_url="<azure-mcp-url>", require_approval="never"),
        ],
    },
    "codegen": {
        "task_profile": "code-generation",
        "instructions_file": "prompts/codegen_agent.md",
        "tools": [
            MCPTool(server_label="terraform", server_url="<terraform-mcp-url>", require_approval="never"),
            MCPTool(server_label="bicep", server_url="<bicep-mcp-url>", require_approval="never"),
            MCPTool(server_label="azure", server_url="<azure-mcp-url>", require_approval="never"),
        ],
    },
    "standards": {
        "task_profile": "analysis",
        "instructions_file": "prompts/standards_agent.md",
        "tools": [
            MCPTool(server_label="github", server_url="<github-mcp-url>", require_approval="never"),
        ],
    },
    "security": {
        "task_profile": "fast-lightweight",
        "instructions_file": "prompts/security_agent.md",
        "tools": [
            # tfsec and Checkov exposed as Azure Function tools
            FunctionTool(functions=[
                {"name": "run_tfsec", "description": "Run tfsec static analysis on Terraform files", "parameters": {"type": "object", "properties": {"files": {"type": "array"}}}},
                {"name": "run_checkov", "description": "Run Checkov policy scan on IaC files", "parameters": {"type": "object", "properties": {"files": {"type": "array"}}}},
            ]),
        ],
    },
    "pr_workflow": {
        "task_profile": "fast-lightweight",
        "instructions_file": "prompts/pr_workflow_agent.md",
        "tools": [
            MCPTool(server_label="github", server_url="<github-mcp-url>", require_approval="never"),
        ],
    },
    "deploy": {
        "task_profile": "orchestration",
        "instructions_file": "prompts/deploy_agent.md",
        "tools": [
            MCPTool(server_label="github", server_url="<github-mcp-url>", require_approval="never"),
            MCPTool(server_label="azure", server_url="<azure-mcp-url>", require_approval="never"),
        ],
    },
    "template_curation": {
        "task_profile": "code-generation",
        "instructions_file": "prompts/template_curation_agent.md",
        "tools": [
            MCPTool(server_label="github", server_url="<github-mcp-url>", require_approval="never"),
        ],
    },
}

async def register_agents():
    """Register all agents with Foundry Agent Service at startup. ModelRouter resolves models from task profiles."""
    client = AIProjectClient(endpoint=FOUNDRY_ENDPOINT, credential=DefaultAzureCredential())
    for name, config in AGENT_CONFIGS.items():
        instructions = open(config["instructions_file"]).read()
        await client.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(
                model_router_profile=config["task_profile"],  # ModelRouter selects optimal model
                instructions=instructions,
                tools=config["tools"],
            ),
        )
```

### 5.2 Orchestrator Workflow (Microsoft Agent Framework)

```python
# src/infrastructure/agents/orchestrator.py
"""
Graph-based orchestrator using Microsoft Agent Framework.
Implements the InfraAgent pipeline as a directed workflow with human gates.
"""

from agent_framework import AgentWorkflow, AgentNode, HumanApprovalNode, ConditionalEdge
from agent_framework.azure_ai import FoundryChatClient

def build_chat_path_workflow() -> AgentWorkflow:
    """
    Chat path: Consult → SubscriptionDiscovery → CodeGen → IaCValidation → Standards → Security → H1 → PR → Plan → H2 → Deploy
    With maker-checker loop on CodeGen/IaCValidation/Standards/Security (max 3x).
    Plan-failure rework loop (max 2x) with error categorization.
    """
    workflow = AgentWorkflow(name="infraagent_chat_path")

    # Nodes
    consult    = AgentNode("consulting",            agent_name="consulting")
    discovery  = AgentNode("subscription_discovery", agent_name="consulting")  # consulting agent in discovery mode
    codegen    = AgentNode("codegen",               agent_name="codegen")
    iac_valid  = AgentNode("iac_validation",        agent_name=None)           # Deterministic — no LLM agent
    standards  = AgentNode("standards",             agent_name="standards")
    security   = AgentNode("security",              agent_name="security")
    diagram    = AgentNode("diagram_gen",           agent_name="codegen")      # codegen agent in diagram mode
    h1_gate    = HumanApprovalNode("h1_code_review",  prompt="Review generated code and architecture diagram.")
    pr_create  = AgentNode("pr_workflow",           agent_name="pr_workflow")
    plan       = AgentNode("plan",                  agent_name="deploy")       # deploy agent in plan mode
    h2_gate    = HumanApprovalNode("h2_plan_review",   prompt="Review terraform plan / bicep what-if output.")
    deploy     = AgentNode("deploy",                agent_name="deploy")       # deploy agent in apply mode

    # Edges
    workflow.add_edge(consult, discovery)
    workflow.add_edge(discovery, codegen)
    workflow.add_edge(codegen, iac_valid)       # IaC validation runs BEFORE LLM-based checks
    workflow.add_edge(iac_valid, standards)
    workflow.add_edge(standards, security)

    # Maker-checker conditional: if violations and iteration < 3, loop back to codegen
    workflow.add_conditional_edge(security, [
        ConditionalEdge(condition="passed",               target=diagram),
        ConditionalEdge(condition="violations_fixable",    target=codegen),  # Loop
        ConditionalEdge(condition="max_iterations",        target=diagram),  # Escalate with best effort
    ])

    # IaC validation failures loop back to codegen directly
    workflow.add_conditional_edge(iac_valid, [
        ConditionalEdge(condition="passed",               target=standards),
        ConditionalEdge(condition="failed",               target=codegen),  # Loop back for fmt/validate/lint fixes
    ])

    workflow.add_edge(diagram, h1_gate)
    workflow.add_edge(h1_gate, pr_create)
    workflow.add_edge(pr_create, plan)

    # Plan conditional with failure categorization
    workflow.add_conditional_edge(plan, [
        ConditionalEdge(condition="plan_success",          target=h2_gate),
        ConditionalEdge(condition="plan_failed_fixable",   target=codegen),  # Loop 2 (max 2x) — fixable errors
        ConditionalEdge(condition="plan_failed_escalate",  target=h2_gate),  # Non-fixable (quota, auth) — show to user
    ])

    workflow.add_edge(h2_gate, deploy)

    workflow.set_entry(consult)
    return workflow


def build_catalog_path_workflow() -> AgentWorkflow:
    """
    Catalog path: Template hydrate → Validate → H1 → PR → Plan → H2 → Deploy
    Much simpler — no consulting, no iterative codegen/standards/security.
    """
    workflow = AgentWorkflow(name="infraagent_catalog_path")

    hydrate   = AgentNode("hydrate",            agent_name="codegen")  # codegen in hydrate mode
    validate  = AgentNode("validate",            agent_name="standards")  # syntax check only
    h1_gate   = HumanApprovalNode("h1_code_review",  prompt="Review template deployment.")
    pr_create = AgentNode("pr_workflow",         agent_name="pr_workflow")
    plan      = AgentNode("plan",                agent_name="deploy")
    h2_gate   = HumanApprovalNode("h2_plan_review",   prompt="Review plan output.")
    deploy    = AgentNode("deploy",              agent_name="deploy")

    workflow.add_edge(hydrate, validate)
    workflow.add_edge(validate, h1_gate)
    workflow.add_edge(h1_gate, pr_create)
    workflow.add_edge(pr_create, plan)
    workflow.add_edge(plan, h2_gate)
    workflow.add_edge(h2_gate, deploy)

    workflow.set_entry(hydrate)
    return workflow
```

---

## 6. MCP Server Integration

### 6.1 MCP Connection Configuration

```python
# src/infrastructure/mcp/config.py
from dataclasses import dataclass

@dataclass
class MCPServerConfig:
    label: str
    url: str
    auth_type: str  # "none" | "api_key" | "entra_id"
    auth_value: str | None = None

MCP_SERVERS = {
    "terraform": MCPServerConfig(
        label="terraform",
        url="https://<function-app>.azurewebsites.net/mcp",  # Self-hosted via Azure Functions
        auth_type="api_key",
    ),
    "bicep": MCPServerConfig(
        label="bicep",
        url="https://<function-app>.azurewebsites.net/mcp",
        auth_type="api_key",
    ),
    "azure": MCPServerConfig(
        label="azure",
        url="https://<azure-mcp>.azurewebsites.net/mcp",
        auth_type="entra_id",
    ),
    "github": MCPServerConfig(
        label="github",
        url="https://<github-mcp>.azurewebsites.net/mcp",
        auth_type="api_key",
    ),
}
```

### 6.2 MCP Tool Inventory

| MCP Server | Key Tools Used by InfraAgent | Agent Consumer |
|------------|------------------------------|----------------|
| **Terraform MCP** | `search_providers`, `get_provider_details`, `search_modules`, `get_module_details`, `search_policies`, `get_policy_details` | CodeGen |
| **Bicep MCP** | `get_az_resource_type_schema`, `get_bicep_best_practices`, `get_bicep_file_diagnostics`, `list_avm_metadata`, `format_bicep_file`, `decompile_arm_template_file` | CodeGen |
| **Azure MCP** | Resource management (list, get, create), subscription info, quota checks, Key Vault secrets, deployment operations | Consulting, CodeGen, Deploy |
| **GitHub MCP** | `create_branch`, `commit_files`, `create_pull_request`, `list_workflows`, `trigger_workflow`, `get_workflow_run` | PR Workflow, Deploy |

---

## 7. Knowledge Wiki Schema

### 7.1 Repository Structure

```
infraagent-wiki/
├── templates/
│   ├── aks-cluster/
│   │   ├── metadata.yaml
│   │   ├── terraform/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── bicep/
│   │       ├── main.bicep
│   │       └── main.bicepparam
│   ├── 3-tier-web-app/
│   │   ├── metadata.yaml
│   │   ├── terraform/
│   │   │   ├── modules/
│   │   │   │   ├── app-service/
│   │   │   │   ├── sql-database/
│   │   │   │   └── vnet/
│   │   │   └── main.tf
│   │   └── bicep/
│   │       ├── modules/
│   │       │   ├── appService.bicep
│   │       │   ├── sqlDatabase.bicep
│   │       │   └── vnet.bicep
│   │       └── main.bicep
│   └── static-website-cdn/
│       ├── metadata.yaml
│       ├── terraform/
│       └── bicep/
├── skills/
│   ├── general-azure/
│   │   └── SKILL.md
│   ├── foundry-ads-session/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── foundry-patterns.md
│   │       ├── readiness-checklist.md
│   │       └── probing-questions.md
│   └── networking/
│       └── SKILL.md
├── standards/
│   ├── naming.md
│   ├── tagging.md
│   └── policies.md
└── patterns/
    ├── hub-spoke-networking.md
    ├── landing-zone.md
    └── adr/
        ├── 001-mcp-over-direct-api.md
        └── 002-bicep-and-terraform-dual-support.md
```

### 7.2 Template metadata.yaml Schema

```yaml
name: "aks-cluster"
display_name: "Azure Kubernetes Service Cluster"
description: "Production-ready AKS cluster with managed identity, Azure CNI, and monitoring."
version: "1.2.0"
author: "platform-team"
approved_by: "john.doe@company.com"
created_at: "2026-03-15"
updated_at: "2026-04-01"

azure_services:
  - "Azure Kubernetes Service"
  - "Azure Container Registry"
  - "Azure Monitor"
  - "Azure Virtual Network"

complexity: "moderate"  # simple | moderate | complex
iac_languages:
  - "terraform"
  - "bicep"

tags:
  - "kubernetes"
  - "containers"
  - "aks"
  - "microservices"

parameters:
  - name: "node_count"
    type: "integer"
    default: 3
    description: "Number of worker nodes in the default node pool"
    validation:
      min: 1
      max: 100

  - name: "vm_size"
    type: "string"
    default: "Standard_D4s_v5"
    description: "VM SKU for worker nodes"
    validation:
      allowed_values:
        - "Standard_D2s_v5"
        - "Standard_D4s_v5"
        - "Standard_D8s_v5"
        - "Standard_D16s_v5"

  - name: "kubernetes_version"
    type: "string"
    default: "1.29"
    description: "Kubernetes version"

  - name: "enable_monitoring"
    type: "boolean"
    default: true
    description: "Enable Azure Monitor container insights"

  - name: "network_plugin"
    type: "string"
    default: "azure"
    description: "Network plugin (azure CNI or kubenet)"
    validation:
      allowed_values: ["azure", "kubenet"]

# Org-level parameters are NOT listed here — they are auto-injected by the Standards Agent
# (environment, naming convention, required tags, subscription, resource group)
```

---

## 8. Backend API Contracts

### 8.1 API Route Summary

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/chat` | Send message to consulting/codegen agents | JWT |
| `POST` | `/api/chat/{conversation_id}/approve` | Human gate approval (H1 or H2) | JWT |
| `POST` | `/api/chat/{conversation_id}/reject` | Human gate rejection with feedback | JWT |
| `GET`  | `/api/catalog` | List templates from knowledge wiki | JWT |
| `GET`  | `/api/catalog/{name}` | Get template details + parameter schema | JWT |
| `POST` | `/api/catalog/{name}/deploy` | Deploy a catalog template | JWT |
| `GET`  | `/api/deployments/{id}` | Get deployment status | JWT |
| `GET`  | `/api/deployments/{id}/plan` | Get plan output | JWT |
| `GET`  | `/api/deployments/{id}/files` | Get generated files | JWT |
| `GET`  | `/api/deployments/{id}/diagram` | Get architecture diagram (SVG) | JWT |
| `GET`  | `/api/standards` | Load current org standards | JWT |
| `GET`  | `/api/health` | Health check | None |
| `WS`   | `/ws/chat/{conversation_id}` | Real-time streaming for chat + status | JWT |

### 8.2 Key Request/Response Schemas

#### POST /api/chat

```json
// Request
{
  "message": "I need a 3-tier web app with App Service, SQL Database, and a VNet",
  "conversation_id": "uuid-optional",
  "iac_language": "bicep"  // "terraform" | "bicep" | null (agent decides)
}

// Response (SSE stream)
// Event: message
{
  "type": "assistant_message",
  "content": "Great, let me help you design that. A few questions...",
  "conversation_id": "uuid",
  "stage": "consulting"
}

// Event: stage_change
{
  "type": "stage_change",
  "stage": "discovering_subscription",
  "message": "Connecting to Azure subscription to inventory existing resources..."
}

// Event: subscription_context
{
  "type": "subscription_context",
  "subscription_name": "Production-Sub-01",
  "resource_groups": ["rg-prod-web-westeurope", "rg-prod-data-westeurope"],
  "vnets": [{"name": "vnet-prod-westeurope", "address_space": ["10.0.0.0/16"]}],
  "naming_patterns": ["rg-{env}-{app}-{region}"],
  "message": "Found 2 resource groups, 1 VNet, detected naming pattern: rg-{env}-{app}-{region}"
}

// Event: stage_change
{
  "type": "stage_change",
  "stage": "generating",
  "message": "Generating Bicep code..."
}

// Event: stage_change
{
  "type": "stage_change",
  "stage": "validating_iac",
  "message": "Running IaC validation pipeline (fmt → validate → lint)..."
}

// Event: files_generated
{
  "type": "files_generated",
  "files": [
    {"path": "modules/appService.bicep", "content": "...", "language": "bicep"}
  ],
  "diagram_url": "/api/deployments/{id}/diagram",
  "diagram_mermaid": "graph TD; ..."
}

// Event: approval_required
{
  "type": "approval_required",
  "gate": "h1_code_review",
  "deployment_id": "uuid",
  "message": "Please review the generated code and architecture diagram."
}
```

#### POST /api/catalog/{name}/deploy

```json
// Request
{
  "template_name": "aks-cluster",
  "iac_language": "terraform",
  "parameters": {
    "node_count": 5,
    "vm_size": "Standard_D4s_v5",
    "kubernetes_version": "1.29",
    "enable_monitoring": true
  },
  "target_repo": "org/infra-deployments",
  "target_branch": "main"
}

// Response
{
  "deployment_id": "uuid",
  "status": "hydrating",
  "message": "Template 'aks-cluster' is being hydrated with your parameters..."
}
```

#### GET /api/deployments/{id}

```json
// Response
{
  "id": "uuid",
  "conversation_id": "uuid",
  "path": "catalog_template",
  "iac_language": "terraform",
  "stage": "awaiting_plan_review",
  "project_type": "production",
  "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "template_name": "aks-cluster",
  "pr": {
    "number": 42,
    "url": "https://github.com/org/repo/pull/42",
    "state": "open"
  },
  "plan": {
    "status": "completed",
    "resources_to_create": 8,
    "resources_to_modify": 0,
    "resources_to_destroy": 0,
    "output_url": "/api/deployments/{id}/plan",
    "error_category": null,
    "rework_iteration": 0
  },
  "diagram_url": "/api/deployments/{id}/diagram",
  "files_count": 5,
  "created_at": "2026-04-09T10:30:00Z",
  "updated_at": "2026-04-09T10:32:15Z"
}
```

---

## 9. Database Schema

PostgreSQL via SQLAlchemy (async) or Prisma for Python.

```sql
-- Conversations
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT,
    iac_language    VARCHAR(20),  -- 'terraform' | 'bicep' | NULL
    deployment_path VARCHAR(30),  -- 'chat_custom' | 'catalog_template' | NULL
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    agent_name      VARCHAR(50),  -- which agent generated this message
    code_blocks     JSONB,        -- [{filename, language, code}]
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

-- Deployments
CREATE TABLE deployments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    path            VARCHAR(30) NOT NULL,   -- 'chat_custom' | 'catalog_template'
    iac_language    VARCHAR(20) NOT NULL,    -- 'terraform' | 'bicep'
    stage           VARCHAR(50) NOT NULL DEFAULT 'consulting',
    project_type    VARCHAR(20) DEFAULT 'production',  -- 'demo' | 'production' | 'enterprise' | 'regulated'
    subscription_id VARCHAR(100),
    subscription_context JSONB,             -- Serialized SubscriptionContext from discovery
    template_name   VARCHAR(100),
    template_params JSONB,
    requirements    TEXT,
    pr_number       INTEGER,
    pr_url          TEXT,
    pr_branch       VARCHAR(200),
    plan_output     TEXT,
    plan_status     VARCHAR(30),
    plan_error_category VARCHAR(50),         -- 'resource_conflict' | 'sku_unavailable' | 'quota_exceeded' | etc.
    plan_rework_iteration INTEGER DEFAULT 0, -- Loop 2 counter (max 2)
    apply_status    VARCHAR(30),
    apply_output    TEXT,
    iteration_count INTEGER DEFAULT 0,
    violations      JSONB,       -- [{type, resource, message, severity}]
    diagram_mermaid TEXT,        -- Generated architecture diagram in Mermaid syntax
    target_repo     VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Generated Files (snapshot per deployment)
CREATE TABLE generated_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id   UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    path            VARCHAR(500) NOT NULL,
    content         TEXT NOT NULL,
    language        VARCHAR(20) NOT NULL,
    is_new          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_files_deployment ON generated_files(deployment_id);

-- Settings (singleton until multi-user)
CREATE TABLE settings (
    id                      UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000001',
    azure_subscription_id   VARCHAR(100),
    azure_tenant_id         VARCHAR(100),
    github_token_encrypted  TEXT,
    github_repo             VARCHAR(200),
    default_branch          VARCHAR(100) DEFAULT 'main',
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id   UUID REFERENCES deployments(id),
    action          VARCHAR(50) NOT NULL,  -- 'h1_approved' | 'h2_rejected' | 'pr_created' | 'deploy_started'
    actor           VARCHAR(100),
    details         JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. Frontend Architecture

### 10.1 Route Structure

```
/                         → Landing page (choose Chat or Catalog)
/chat                     → Chat interface with Consulting/CodeGen agents
/chat/:conversationId     → Existing conversation
/catalog                  → Self-service template catalog (search + browse)
/catalog/:templateName    → Template detail + parameter form + deploy button
/deployments/:id          → Deployment tracker (stages, PR, plan, diagram)
/settings                 → Connection config (Azure, GitHub)
```

### 10.2 State Management

```typescript
// Global state via React Context + useReducer (or Zustand for simplicity)

interface AppState {
  // Chat
  conversations: Map<string, Conversation>;
  activeConversationId: string | null;

  // Deployment tracking
  activeDeployment: Deployment | null;

  // Catalog
  templates: TemplateMetadata[];
  catalogSearchQuery: string;

  // Connection
  settings: UserSettings;
  connectionStatus: { azure: boolean; github: boolean; foundry: boolean };
}

// WebSocket connection for real-time updates
// /ws/chat/{conversationId} provides SSE-style events:
//   - assistant_message (streaming text)
//   - stage_change (pipeline progress)
//   - files_generated (code blocks)
//   - approval_required (human gate)
//   - deployment_status (plan/apply progress)
```

### 10.3 Key Components

| Component | Description |
|-----------|-------------|
| `ChatPanel` | Message history, markdown rendering, code blocks, streaming indicator |
| `SubscriptionDiscoveryPanel` | Displays discovered subscription context: resource groups, VNets, naming patterns, quotas |
| `CatalogGrid` | Searchable grid of template cards with service icons and complexity badges |
| `TemplateDetail` | Parameter form, preview of files, deploy button |
| `FileExplorer` | Tree view of generated `.tf` / `.bicep` files with syntax highlighting |
| `DiagramViewer` | Mermaid architecture diagram rendered as SVG with zoom/pan/export |
| `DeploymentTracker` | Pipeline stage visualization (Consulting → Discovery → CodeGen → IaC Validation → Standards → Security → H1 → PR → Plan → H2 → Deploy) |
| `ApprovalModal` | Human gate UI for H1 (code review) and H2 (plan review) |
| `PlanDiffViewer` | Set-diff analysis view for plan review — filters false-positive diffs, highlights destructive changes (P1) |
| `StandardsPanel` | Read-only view of org naming/tagging/policy rules |

---

## 11. Project Structure

```
infraagent/
├── src/
│   ├── domain/                          # Pure business logic (zero deps)
│   │   ├── models/
│   │   │   ├── deployment.py            # DeploymentRequest, Conversation, GeneratedFile
│   │   │   └── template.py              # TemplateMetadata, HydratedTemplate
│   │   ├── policies/
│   │   │   ├── naming_policy.py         # Naming convention rules + validator
│   │   │   ├── tagging_policy.py        # Required tags rules + validator
│   │   │   └── security_policy.py       # Security rules (deterministic checks)
│   │   └── services/
│   │       ├── standards_service.py     # Orchestrates naming + tagging validation
│   │       └── iac_parser.py            # Parses HCL/Bicep into resource models
│   │
│   ├── application/                     # Use cases + port interfaces
│   │   ├── ports/
│   │   │   ├── llm_port.py             # ILLMCompletionPort + TaskProfile (ModelRouter)
│   │   │   ├── infra_provider_port.py  # IInfraProviderPort (format_check, validate, lint, plan, apply)
│   │   │   ├── source_control_port.py  # ISourceControlPort
│   │   │   ├── policy_engine_port.py   # IPolicyEnginePort
│   │   │   ├── template_registry_port.py  # ITemplateRegistryPort
│   │   │   ├── subscription_discovery_port.py  # ISubscriptionDiscoveryPort
│   │   │   └── observability_port.py   # IObservabilityPort
│   │   └── use_cases/
│   │       ├── consult.py              # ConsultUseCase
│   │       ├── generate.py             # GenerateUseCase (custom + catalog paths)
│   │       └── deploy.py               # DeployUseCase
│   │
│   ├── infrastructure/                  # Adapters (framework-specific)
│   │   ├── adapters/
│   │   │   ├── azure_openai_adapter.py # ILLMCompletionPort → Azure OpenAI + ModelRouter
│   │   │   ├── terraform_adapter.py    # IInfraProviderPort → Terraform CLI (fmt/init/validate/tflint)
│   │   │   ├── bicep_adapter.py        # IInfraProviderPort → Bicep CLI (build/format/lint)
│   │   │   ├── github_adapter.py       # ISourceControlPort → Octokit / GitHub API
│   │   │   ├── policy_adapter.py       # IPolicyEnginePort → tfsec + Checkov + domain rules
│   │   │   ├── template_registry_adapter.py  # ITemplateRegistryPort → GitHub wiki repo
│   │   │   ├── subscription_discovery_adapter.py  # ISubscriptionDiscoveryPort → Azure MCP
│   │   │   ├── postgres_adapter.py     # Database access
│   │   │   └── otel_adapter.py         # IObservabilityPort → OpenTelemetry
│   │   ├── agents/
│   │   │   ├── registry.py             # Foundry agent registration
│   │   │   └── orchestrator.py         # Agent Framework workflow definitions
│   │   └── mcp/
│   │       ├── config.py               # MCP server connection configs
│   │       └── tool_adapter.py         # MCP tool → Foundry tool conversion
│   │
│   ├── api/                             # FastAPI routes (presentation layer)
│   │   ├── routes/
│   │   │   ├── chat.py                 # POST /api/chat, WebSocket /ws/chat
│   │   │   ├── catalog.py             # GET /api/catalog, POST /api/catalog/{name}/deploy
│   │   │   ├── deployments.py         # GET /api/deployments/{id}
│   │   │   ├── standards.py           # GET /api/standards
│   │   │   └── health.py             # GET /api/health
│   │   ├── middleware/
│   │   │   ├── auth.py                # JWT / Entra ID middleware
│   │   │   └── cors.py               # CORS config
│   │   └── schemas/
│   │       ├── chat.py                # Pydantic request/response models
│   │       ├── catalog.py
│   │       └── deployment.py
│   │
│   ├── prompts/                         # Agent system prompts (markdown)
│   │   ├── orchestrator.md
│   │   ├── consulting_agent.md
│   │   ├── codegen_agent_terraform.md
│   │   ├── codegen_agent_bicep.md
│   │   ├── standards_agent.md
│   │   ├── security_agent.md
│   │   ├── pr_workflow_agent.md
│   │   ├── deploy_agent.md
│   │   └── template_curation_agent.md
│   │
│   ├── config.py                        # Centralized configuration
│   └── main.py                          # Composition root + FastAPI app
│
├── frontend/                            # React / Next.js
│   ├── src/
│   │   ├── app/                         # Next.js app router
│   │   │   ├── page.tsx                 # Landing
│   │   │   ├── chat/
│   │   │   ├── catalog/
│   │   │   ├── deployments/
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── StreamingIndicator.tsx
│   │   │   ├── catalog/
│   │   │   │   ├── CatalogGrid.tsx
│   │   │   │   ├── TemplateCard.tsx
│   │   │   │   └── ParameterForm.tsx
│   │   │   ├── deployment/
│   │   │   │   ├── DeploymentTracker.tsx
│   │   │   │   ├── PipelineStages.tsx
│   │   │   │   └── ApprovalModal.tsx
│   │   │   ├── code/
│   │   │   │   ├── FileExplorer.tsx
│   │   │   │   ├── CodeBlock.tsx
│   │   │   │   └── DiagramViewer.tsx
│   │   │   └── ui/                      # shadcn/ui primitives
│   │   ├── lib/
│   │   │   ├── api.ts                   # Backend API client
│   │   │   ├── ws.ts                    # WebSocket client
│   │   │   └── types.ts                 # Shared TypeScript interfaces
│   │   └── hooks/
│   │       ├── useChat.ts
│   │       ├── useDeployment.ts
│   │       └── useCatalog.ts
│   ├── package.json
│   └── tsconfig.json
│
├── infra/                               # Bicep IaC for InfraAgent itself
│   ├── main.bicep                       # Root deployment
│   ├── modules/
│   │   ├── foundry.bicep               # AI Foundry resource + project
│   │   ├── postgres.bicep              # Azure PostgreSQL Flexible Server
│   │   ├── appService.bicep            # App Service for backend
│   │   ├── staticWebApp.bicep          # Static Web App for frontend
│   │   ├── keyVault.bicep              # Key Vault for secrets
│   │   ├── aiSearch.bicep              # AI Search for policy RAG
│   │   ├── functionApp.bicep           # Azure Functions for MCP hosting
│   │   └── monitoring.bicep            # App Insights + Log Analytics
│   └── parameters/
│       ├── dev.bicepparam
│       └── prod.bicepparam
│
├── wiki/                                # Knowledge wiki (submodule or separate repo)
│   └── (see section 7.1)
│
├── .github/
│   └── workflows/
│       ├── ci.yml                       # Lint, type-check, test on PR
│       ├── deploy-infra.yml            # Bicep deploy for InfraAgent itself
│       └── deploy-app.yml             # Backend + frontend deployment
│
├── tests/
│   ├── unit/
│   │   ├── domain/                      # Pure domain logic tests (no mocks needed)
│   │   │   ├── test_naming_policy.py
│   │   │   ├── test_tagging_policy.py
│   │   │   └── test_standards_service.py
│   │   └── application/
│   │       ├── test_consult_use_case.py # Mocked ports
│   │       ├── test_generate_use_case.py
│   │       └── test_deploy_use_case.py
│   ├── integration/
│   │   ├── test_github_adapter.py
│   │   ├── test_terraform_adapter.py
│   │   └── test_mcp_connection.py
│   └── e2e/
│       └── test_chat_to_deploy.py       # Full pipeline E2E
│
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 12. Infrastructure as Code (InfraAgent Self-Deployment)

InfraAgent's own infrastructure is deployed via Bicep — dogfooding the platform.

### 12.1 Azure Resources Required

| Resource | SKU / Tier | Purpose |
|----------|-----------|---------|
| Azure AI Foundry Resource | AIServices (S0) | Agent runtime, model deployments |
| Azure AI Foundry Project | — | Agent workspace |
| Azure OpenAI Deployments | GPT-4o (GlobalStandard), GPT-4o-mini (GlobalStandard) | Agent model inference |
| Azure App Service | B2 (hackathon) | Python backend hosting |
| Azure Static Web Apps | Free | React frontend hosting |
| Azure PostgreSQL Flexible | Burstable B1ms | Database |
| Azure Key Vault | Standard | Secrets (GitHub PAT, API keys) |
| Azure AI Search | Basic | Policy RAG, template search |
| Azure Functions | Consumption | MCP server hosting (tfsec, Checkov) |
| Azure App Insights | — | Observability |
| Azure Storage Account | Standard LRS | Function app storage, generated artifacts |

### 12.2 Estimated Cost (Hackathon)

| Resource | Monthly Estimate |
|----------|-----------------|
| AI Foundry + GPT-4o (pay-per-token) | ~$50–100 (demo usage) |
| App Service B2 | ~$55 |
| PostgreSQL B1ms | ~$25 |
| AI Search Basic | ~$75 |
| Everything else | ~$20 |
| **Total** | **~$225–275/month** |

---

## 13. CI/CD Pipeline

### 13.1 InfraAgent's Own CI/CD

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy src/
      - run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - run: pytest tests/integration/ -v -m "not slow"
```

### 13.2 Generated IaC CI/CD (Created by PR Workflow Agent)

The PR Workflow Agent creates this GitHub Actions workflow in the target repo if it doesn't exist:

```yaml
# .github/workflows/terraform-plan.yml  (generated by InfraAgent)
name: Terraform Plan
on:
  pull_request:
    paths: ["terraform/**"]
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
        working-directory: terraform/
      - run: terraform validate
        working-directory: terraform/
      - run: terraform plan -no-color -out=tfplan
        working-directory: terraform/
        env:
          ARM_SUBSCRIPTION_ID: ${{ secrets.ARM_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.ARM_TENANT_ID }}
          ARM_CLIENT_ID: ${{ secrets.ARM_CLIENT_ID }}
          ARM_CLIENT_SECRET: ${{ secrets.ARM_CLIENT_SECRET }}
      - uses: actions/github-script@v7
        with:
          script: |
            // Post plan output as PR comment
```

Equivalent Bicep workflow uses `az deployment group what-if` and `az deployment group create`.

---

## 14. Observability

### 14.1 Tracing

Every agent call and use case execution is traced via OpenTelemetry, exported to Azure App Insights.

```python
# Trace hierarchy:
# [Span] POST /api/chat
#   └── [Span] ConsultUseCase.run
#         ├── [Span] subscription_discovery (subscription=<id>)
#         ├── [Span] template_registry.search
#         ├── [Span] llm.complete (profile=complex-reasoning, model_used=gpt-4o, tokens_in=X, tokens_out=Y)
#         └── [Span] wiki.search_templates
#
# [Span] POST /api/chat (after consult → codegen)
#   └── [Span] GenerateUseCase.run_custom_path
#         ├── [Span] llm.complete_with_tools (iteration=1, profile=code-generation)
#         │     ├── [Span] mcp.terraform.search_modules (query="avm-res-")
#         │     ├── [Span] mcp.terraform.search_providers
#         │     └── [Span] mcp.terraform.get_provider_details
#         ├── [Span] iac_validation_pipeline (language=terraform)
#         │     ├── [Span] infra_provider.format_check
#         │     ├── [Span] infra_provider.validate
#         │     └── [Span] infra_provider.lint
#         ├── [Span] policy_engine.validate_naming
#         ├── [Span] policy_engine.validate_tags
#         ├── [Span] policy_engine.validate_security
#         └── [Span] generate_diagram (profile=fast-lightweight)
```

### 14.2 Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `infraagent.chat.latency` | Histogram | End-to-end chat turn latency |
| `infraagent.subscription_discoveries` | Counter | Subscription discovery runs |
| `infraagent.generate.iterations` | Histogram | Maker-checker iterations before passing |
| `infraagent.generate.max_iterations_reached` | Counter | Times max iterations were hit |
| `infraagent.iac_validation.failures` | Counter (by step: fmt/validate/lint) | IaC validation pipeline failures |
| `infraagent.plan_rework.iterations` | Histogram | Plan-failure rework iterations (Loop 2) |
| `infraagent.plan_rework.category` | Counter (by category) | Plan failure categories (resource_conflict, sku_unavailable, etc.) |
| `infraagent.prs_created` | Counter | PRs created |
| `infraagent.deployments_triggered` | Counter | Apply operations triggered |
| `infraagent.deployments_succeeded` | Counter | Successful deployments |
| `infraagent.deployments_failed` | Counter | Failed deployments |
| `infraagent.token_usage` | Counter (by agent, profile, model_used) | LLM token consumption |
| `infraagent.mcp.call_latency` | Histogram (by server, tool) | MCP tool call latency |
| `infraagent.catalog.deploys` | Counter | Catalog template deployments |
| `infraagent.standards.violations` | Counter (by category) | Standards violations detected |
| `infraagent.diagrams.generated` | Counter | Architecture diagrams generated |

---

## 15. Security

### 15.1 Authentication & Authorization

| Surface | Method | Details |
|---------|--------|---------|
| Frontend → Backend | JWT (Entra ID) | Hackathon: optional. Post-hackathon: required |
| Backend → Foundry | DefaultAzureCredential | Managed Identity in production |
| Backend → GitHub | PAT (encrypted in Key Vault) | Scopes: `repo`, `workflow` |
| Backend → PostgreSQL | Managed Identity | No password in connection string |
| MCP Servers | API Key or Entra ID | Per-server configuration |

### 15.2 Secrets Management

All secrets stored in Azure Key Vault. Never in code, environment variables, or database.

| Secret | Key Vault Name | Rotated |
|--------|---------------|---------|
| GitHub PAT | `github-pat` | Manual (90-day expiry) |
| Azure OpenAI API Key | `aoai-api-key` | Managed Identity preferred |
| Foundry connection string | `foundry-connection` | Managed Identity preferred |
| PostgreSQL connection | `postgres-connection` | Managed Identity preferred |

### 15.3 Safety Rules (Enforced in Domain Layer)

These rules are deterministic code, not LLM prompts:

1. **Never auto-deploy** without explicit human approval at H2.
2. **Never expose credentials** in generated IaC, chat, or PR descriptions.
3. **Always show plan** before apply. No apply without preceding plan.
4. **Warn on destructive changes** — any `destroy` in plan output triggers a prominent warning.
5. **Rate-limit LLM calls** — max 20 chat turns per conversation, max 3 maker-checker iterations.
6. **Terraform state is customer-owned** — InfraAgent never holds or manages state files.

---

## 16. Development Guidelines

### 16.1 Coding Standards

| Rule | Details |
|------|---------|
| Type hints | All function signatures must have type hints |
| Async | All I/O operations are `async` |
| No raw SQL | Use SQLAlchemy ORM or Prisma |
| Error handling | Domain errors are typed exceptions. Infrastructure errors are caught and logged at adapter boundary |
| Testing | Domain layer: 100% unit test coverage. Application layer: use case tests with mocked ports |
| Imports | Domain layer must never import from `infrastructure`, `api`, or any third-party package |
| Linting | `ruff` for linting, `mypy` for type checking |
| Formatting | `ruff format` (Black-compatible) |
| Commits | Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`) |

### 16.2 Testing Strategy

| Layer | Test Type | What's Mocked | Speed |
|-------|-----------|---------------|-------|
| Domain | Unit | Nothing (pure functions) | < 1ms/test |
| Application (Use Cases) | Unit | All ports (LLM, GitHub, policy, etc.) | < 10ms/test |
| Infrastructure (Adapters) | Integration | External services (use test doubles or sandboxes) | < 5s/test |
| API Routes | Integration | Use cases (injected test doubles) | < 1s/test |
| E2E | E2E | Nothing (real Foundry + real GitHub) | < 5min/test |

### 16.3 Agent Prompt Development

Agent prompts live in `src/prompts/*.md` and are version-controlled. Changes to prompts go through the same PR review process as code. Prompt evaluation uses `azure-ai-evaluation` with golden datasets:

```python
# tests/evaluation/test_codegen_quality.py
from azure.ai.evaluation import evaluate

results = evaluate(
    data="tests/evaluation/golden/codegen_cases.jsonl",
    evaluators={
        "validity": terraform_validity_evaluator,
        "standards": standards_compliance_evaluator,
        "security": security_scan_evaluator,
    },
    model=codegen_agent,
)
assert results["validity"]["pass_rate"] > 0.95
assert results["standards"]["pass_rate"] == 1.0
```

---

## Appendix A — Agent System Prompts

Full system prompts for each agent. These are the `instructions` field in the Foundry agent definition.

### A.1 Consulting Agent (Summary)

> You are the InfraAgent Consulting Agent — a senior solutions architect that runs architecture design sessions. You gather requirements through probing questions, challenge vague answers, evaluate trade-offs, and recommend architecture patterns from the knowledge wiki.
>
> **Behavior:**
> 1. Ask 2–3 targeted questions per turn. Never more than 4.
> 2. **Classify the project type** early in the conversation: Demo/Learning, Production, Enterprise, or Regulated. Output `[PROJECT_TYPE:PRODUCTION]` (or the appropriate type). This determines WAF pillar depth and requirements gathering intensity.
> 3. Track what you know vs. what you're assuming.
> 4. **Run subscription discovery** when a target subscription is provided. Summarize findings conversationally ("I can see you already have a VNet `vnet-prod-westeurope` with subnets...") and use them as constraints for downstream agents.
> 5. Search the knowledge wiki for matching templates after every user response.
> 6. If a template matches, output `[RECOMMEND_TEMPLATE:template-name]` and suggest the catalog path.
> 7. When requirements are complete, output `[REQUIREMENTS_COMPLETE]` and hand off to the pipeline.
> 8. If a domain skill is loaded, follow its phase structure and readiness checklist.
> 9. Use Azure MCP Server to check real-time subscription context when relevant.

### A.2 CodeGen Agent — Terraform (Summary)

> You are the InfraAgent CodeGen Agent. You generate production-ready Terraform HCL for Microsoft Azure.
>
> **Critical rules:**
> 1. ALWAYS use Terraform MCP tools before generating code.
> 2. NEVER rely on training data for resource schemas.
> 3. **AVM-FIRST:** Always check for Azure Verified Modules (AVM) via `search_modules` with query `avm-res-` before writing raw resource blocks. Use AVM when available.
> 4. Use ```hcl file=path code blocks.
> 5. Follow modular structure: modules/<resource>/{main,variables,outputs}.tf. Root files: main.tf, variables.tf, outputs.tf, providers.tf, backend.tf.
> 6. Apply organizational standards (naming, tags, security) from context.
> 7. **Secret handling:** Never hardcode secrets. Use Key Vault references, `sensitive = true` on variables, and Managed Identity for auth. Never output sensitive values.
> 8. If prior violations are listed, fix them in this iteration.
> 9. If subscription context is provided, use existing resources via `data` sources and avoid CIDR conflicts.

### A.3 CodeGen Agent — Bicep (Summary)

> Same as A.2 but for Bicep. Uses Bicep MCP Server tools (`get_az_resource_type_schema`, `list_avm_metadata`, `get_bicep_best_practices`). Uses ```bicep file=path code blocks. Follows Bicep module conventions. **AVM-FIRST:** Always check `list_avm_metadata` before writing raw resource blocks; use `br/public:avm/res/{service}/{resource}:{version}` when available. **Secret handling:** Use `@secure()` decorator on parameters, reference Key Vault secrets via `existing` keyword, never output sensitive values.

*(Full prompts will be 500–1000 lines each and developed iteratively during Week 1.)*

---

## Appendix B — Sequence Diagrams

### B.1 Chat Path (Custom Pipeline)

```
User        Frontend      Backend       Consulting    CodeGen     IaCValid    Standards    Security    PR Agent    Deploy
 │              │             │              │            │           │            │           │           │          │
 │─ message ──→│─ POST ─────→│──────────────→│            │           │            │           │           │          │
 │              │             │              │─ ask Qs ──→│            │           │            │           │         │
 │←── stream ──│←── SSE ─────│←─────────────│            │            │           │            │           │          │
 │── answers ─→│─ POST ─────→│──────────────→│            │            │           │            │           │         │
 │              │             │              │─ discover ─│            │           │            │           │         │
 │←── sub ctx ─│←── SSE ─────│←─────────────│ [sub ctx]  │            │           │            │           │          │
 │── answers ─→│─ POST ─────→│──────────────→│            │            │           │            │           │         │
 │              │             │              │─ complete ─→│            │           │            │           │        │
 │              │             │              │  [hand off] │            │           │            │           │        │
 │              │             │              │             │─ MCP call ─│           │            │           │        │
 │              │             │              │             │← schemas ──│           │            │           │        │
 │              │             │              │             │─ generate ─│           │            │           │        │
 │              │             │              │             │────────────→│─ fmt ────│            │           │        │
 │              │             │              │             │            │─ validate│            │           │         │
 │              │             │              │             │            │─ lint ───│            │           │         │
 │              │             │              │             │            │──────────→│─ naming ──│           │         │
 │              │             │              │             │            │          │─ tagging ──│           │         │
 │              │             │              │             │            │          │────────────→│─ scan     │        │
 │              │             │              │             │            │          │            │─ diagram ─→│        │
 │←── H1 ─────│←── approval_required ───────│             │            │          │            │           │          │
 │── approve ─→│─ POST approve ────────────→│─────────────│────────────│──────────│───────────│──────────→│           │
 │              │             │              │             │            │          │            │           │─ PR ───→│
 │              │             │              │             │            │          │            │           │← plan ──│
 │←── H2 ─────│←── approval_required ───────│             │            │          │            │           │          │
 │── approve ─→│─ POST approve ────────────→│─────────────│────────────│──────────│───────────│──────────→│─ apply ──→│
 │←── done ────│←── deployment_complete ────│             │            │          │            │           │          │
```

### B.2 Catalog Path (Template Deployment)

```
User        Frontend      Backend       CodeGen     Standards    PR Agent    Deploy
 │              │             │            │            │           │          │
 │─ browse ───→│─ GET catalog│            │            │           │          │
 │←── list ────│←────────────│            │            │           │          │
 │─ select ───→│─ GET detail │            │            │           │          │
 │←── params ──│←────────────│            │            │           │          │
 │─ deploy ───→│─ POST deploy│───────────→│─ hydrate ──│           │          │
 │              │             │            │─ validate ─→│           │          │
 │←── H1 ─────│←── approval_required ────│            │           │          │
 │── approve ─→│─ POST approve ──────────│────────────│──────────→│          │
 │              │             │            │            │           │─ PR ────→│
 │              │             │            │            │           │← plan ──│
 │←── H2 ─────│←── approval_required ────│            │           │          │
 │── approve ─→│─ POST approve ──────────│────────────│──────────→│─ apply ─→│
 │←── done ────│←── deployment_complete ─│            │           │          │
```

---

*End of Technical Specification Document*
