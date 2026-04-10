"""Consulting agent — gathers requirements through conversation."""

from __future__ import annotations

import json
import logging

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent, AgentThread, MessageRole

from src.core.models import IaCLanguage, RequirementsHandoff

logger = logging.getLogger(__name__)


class ConsultingAgent:
    """Wraps the Foundry-hosted Consulting agent."""

    def __init__(self, client: AIProjectClient, agent: Agent) -> None:
        self._client = client
        self._agent = agent
        self._thread: AgentThread | None = None

    async def chat(self, user_message: str) -> tuple[str, RequirementsHandoff | None]:
        """Send a message and return (reply_text, structured_requirements_or_None)."""
        if self._thread is None:
            self._thread = await self._client.agents.create_thread()

        await self._client.agents.create_message(
            thread_id=self._thread.id,
            role=MessageRole.USER,
            content=user_message,
        )

        run = await self._client.agents.create_run(
            thread_id=self._thread.id,
            agent_id=self._agent.id,
        )

        while run.status in ("queued", "in_progress", "requires_action"):
            import asyncio
            await asyncio.sleep(1)
            run = await self._client.agents.get_run(
                thread_id=self._thread.id,
                run_id=run.id,
            )

        if run.status != "completed":
            logger.error("Consulting run failed: %s", run.last_error)
            return f"Error: {run.last_error}", None

        messages = await self._client.agents.list_messages(thread_id=self._thread.id)
        assistant_msgs = [
            m for m in messages.data if m.role == MessageRole.AGENT
        ]
        if not assistant_msgs:
            return "No response from agent.", None

        reply = assistant_msgs[0].content[0].text.value

        # Try to extract structured requirements
        requirements = _try_extract_requirements(reply)
        return reply, requirements


def _try_extract_requirements(text: str) -> RequirementsHandoff | None:
    """Attempt to parse a RequirementsHandoff JSON from the agent reply."""
    try:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        raw = text[start:end].strip()
        data = json.loads(raw)
        return RequirementsHandoff(
            project_name=data.get("project_name", ""),
            description=data.get("description", ""),
            iac_language=IaCLanguage(data.get("iac_language", "bicep")),
            azure_region=data.get("azure_region", "westeurope"),
            environment=data.get("environment", "dev"),
            resources_needed=data.get("resources_needed", []),
            constraints=data.get("constraints", []),
        )
    except (ValueError, json.JSONDecodeError, KeyError):
        return None
