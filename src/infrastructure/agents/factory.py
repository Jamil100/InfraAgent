"""Agent factory — creates Azure AI Foundry agents with system prompts."""

from __future__ import annotations

import logging
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent

from src.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Map agent name → which MCP servers it should receive
_AGENT_MCP_SERVERS: dict[str, list[str]] = {
    "codegen": ["bicep", "terraform", "azure"],
    "standards": ["bicep", "azure"],
    "security": ["bicep", "terraform"],
    "consulting": ["azure"],
}


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def _build_mcp_tools(agent_name: str) -> list:
    """Build MCP tool definitions for servers configured in env vars."""
    server_urls: dict[str, str] = {
        "bicep": settings.mcp_bicep_url,
        "terraform": settings.mcp_terraform_url,
        "azure": settings.mcp_azure_url,
    }
    wanted = _AGENT_MCP_SERVERS.get(agent_name, [])

    tools = []
    for key in wanted:
        url = server_urls.get(key, "")
        if not url:
            logger.debug("MCP server '%s' not configured — skipping for agent '%s'", key, agent_name)
            continue
        try:
            # azure-ai-projects ≥ 1.0.0b8 exposes McpTool / McpToolDefinition
            from azure.ai.projects.models import McpTool  # type: ignore[import]
            tools.append(McpTool(server_url=url, server_label=f"mcp-{key}"))
            logger.info("Attached MCP server '%s' (%s) to agent '%s'", key, url, agent_name)
        except ImportError:
            logger.warning(
                "McpTool not available in this SDK version — MCP grounding skipped for '%s'",
                key,
            )
    return tools


async def create_agent(
    client: AIProjectClient,
    name: str,
    *,
    model: str | None = None,
    tools: list | None = None,
) -> Agent:
    """Create a Foundry-hosted agent with the matching system prompt and MCP tools."""
    system_prompt = _load_prompt(name)
    resolved_tools = tools if tools is not None else _build_mcp_tools(name)
    agent = await client.agents.create_agent(
        model=model or settings.model_deployment,
        name=f"infraagent-{name}",
        instructions=system_prompt,
        tools=resolved_tools,
    )
    logger.info("Created agent %s (id=%s, tools=%d)", name, agent.id, len(resolved_tools))
    return agent
