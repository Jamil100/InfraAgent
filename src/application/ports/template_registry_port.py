"""Template Registry port interface.

Contract between the application layer and the knowledge wiki / template registry.
Ref: TechSpec Section 2.1, lines 323-338
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
