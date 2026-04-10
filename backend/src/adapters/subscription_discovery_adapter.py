"""Subscription discovery adapter — queries Azure for existing resources."""

from __future__ import annotations

import logging

from azure.core.exceptions import HttpResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.resource.aio import ResourceManagementClient

from src.core.models import SubscriptionContext
from src.core.ports import ISubscriptionDiscoveryPort

logger = logging.getLogger(__name__)


class AzureSubscriptionDiscoveryAdapter(ISubscriptionDiscoveryPort):
    """Queries the live Azure control plane to populate SubscriptionContext."""

    async def discover(self, subscription_id: str) -> SubscriptionContext:
        if not subscription_id:
            logger.warning("No subscription_id provided — returning empty context")
            return SubscriptionContext()

        async with DefaultAzureCredential() as credential:
            resource_groups = await _list_resource_groups(credential, subscription_id)
            vnets = await _list_vnets(credential, subscription_id)
            naming_patterns = _infer_naming_patterns(resource_groups, vnets)

        return SubscriptionContext(
            subscription_id=subscription_id,
            resource_groups=resource_groups,
            existing_vnets=vnets,
            naming_patterns=naming_patterns,
        )


async def _list_resource_groups(
    credential: DefaultAzureCredential, subscription_id: str
) -> list[str]:
    names: list[str] = []
    try:
        async with ResourceManagementClient(credential, subscription_id) as rm_client:
            async for rg in rm_client.resource_groups.list():
                if rg.name:
                    names.append(rg.name)
    except HttpResponseError as exc:
        logger.error("Failed to list resource groups: %s", exc.message)
    return names


async def _list_vnets(
    credential: DefaultAzureCredential, subscription_id: str
) -> list[dict]:
    vnets: list[dict] = []
    try:
        async with NetworkManagementClient(credential, subscription_id) as net_client:
            async for vnet in net_client.virtual_networks.list_all():
                vnets.append(
                    {
                        "name": vnet.name,
                        "location": vnet.location,
                        "address_space": (
                            vnet.address_space.address_prefixes
                            if vnet.address_space
                            else []
                        ),
                        "resource_group": _rg_from_id(vnet.id or ""),
                    }
                )
    except HttpResponseError as exc:
        logger.error("Failed to list VNets: %s", exc.message)
    return vnets


def _rg_from_id(resource_id: str) -> str:
    """Extract resource group name from a resource ID."""
    parts = resource_id.lower().split("/")
    try:
        idx = parts.index("resourcegroups")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return ""


def _infer_naming_patterns(
    resource_groups: list[str], vnets: list[dict]
) -> list[str]:
    """Derive common naming conventions from existing resource names."""
    patterns: list[str] = []
    all_names = resource_groups + [v["name"] for v in vnets if v.get("name")]

    separators = {"-": 0, "_": 0}
    for name in all_names:
        for sep in separators:
            if sep in name:
                separators[sep] += 1

    dominant_sep = max(separators, key=lambda k: separators[k])
    if separators[dominant_sep] > 0:
        patterns.append(f"Uses '{dominant_sep}' as separator in resource names")

    # Look for env prefixes/suffixes
    envs = ("dev", "test", "staging", "prod", "uat")
    for name in all_names:
        for env in envs:
            if name.lower().startswith(env) or name.lower().endswith(env):
                patterns.append(f"Environment token '{env}' detected in resource names")
                break

    return list(dict.fromkeys(patterns))  # deduplicate, preserve order
