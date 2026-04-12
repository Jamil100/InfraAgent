"""Subscription Discovery port interface.

Contract between the application layer and Azure subscription discovery (Azure MCP Server).
Ref: TechSpec Section 2.1, lines 390-404
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
