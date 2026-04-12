"""Domain models for the InfraAgent pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IaCLanguage(str, Enum):
    BICEP = "bicep"
    TERRAFORM = "terraform"


class PipelineStage(str, Enum):
    CONSULTING = "consulting"
    CODEGEN = "codegen"
    VALIDATION = "validation"
    STANDARDS = "standards"
    SECURITY = "security"
    HUMAN_REVIEW_CODE = "human_review_code"
    PR_CREATED = "pr_created"
    PLAN = "plan"
    HUMAN_REVIEW_PLAN = "human_review_plan"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# --- Pipeline State ---


class InfraRequest(BaseModel):
    """Initial infrastructure request from the user."""

    user_message: str
    iac_language: IaCLanguage = IaCLanguage.BICEP
    session_id: str = ""


class SubscriptionContext(BaseModel):
    """Discovered Azure subscription state."""

    subscription_id: str = ""
    resource_groups: list[str] = Field(default_factory=list)
    existing_vnets: list[dict[str, Any]] = Field(default_factory=list)
    naming_patterns: list[str] = Field(default_factory=list)


class RequirementsHandoff(BaseModel):
    """Structured output from Consulting Agent to CodeGen."""

    project_name: str = ""
    description: str = ""
    iac_language: IaCLanguage = IaCLanguage.BICEP
    azure_region: str = "westeurope"
    environment: str = "dev"
    resources_needed: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    subscription_context: SubscriptionContext = Field(default_factory=SubscriptionContext)


class GeneratedFile(BaseModel):
    """A single generated IaC file."""

    path: str
    content: str


class ValidationFinding(BaseModel):
    """A finding from validation, standards, or security checks."""

    checker: str
    severity: Severity
    resource: str = ""
    file: str = ""
    line: int = 0
    message: str = ""
    remediation: str = ""


class CodeGenOutput(BaseModel):
    """Output from the CodeGen agent."""

    files: list[GeneratedFile] = Field(default_factory=list)
    mermaid_diagram: str = ""
    explanation: str = ""


class PlanResult(BaseModel):
    """Output from terraform plan / bicep what-if."""

    success: bool = False
    output: str = ""
    error: str = ""
    resources_to_create: list[str] = Field(default_factory=list)
    resources_to_update: list[str] = Field(default_factory=list)
    resources_to_delete: list[str] = Field(default_factory=list)


class PipelineState(BaseModel):
    """Full state of a pipeline run."""

    session_id: str = ""
    stage: PipelineStage = PipelineStage.CONSULTING
    request: InfraRequest | None = None
    requirements: RequirementsHandoff | None = None
    codegen_output: CodeGenOutput | None = None
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    plan_result: PlanResult | None = None
    pr_url: str = ""
    loop1_iteration: int = 0
    loop2_iteration: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    error: str = ""
