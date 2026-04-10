"""Agent factory — creates Azure AI Foundry agents with system prompts."""

from __future__ import annotations

import logging
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent

from src.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


async def create_agent(
    client: AIProjectClient,
    name: str,
    *,
    model: str | None = None,
    tools: list | None = None,
) -> Agent:
    """Create a Foundry-hosted agent with the matching system prompt."""
    system_prompt = _load_prompt(name)
    agent = await client.agents.create_agent(
        model=model or settings.model_deployment,
        name=f"infraagent-{name}",
        instructions=system_prompt,
        tools=tools or [],
    )
    logger.info("Created agent %s (id=%s)", name, agent.id)
    return agent
