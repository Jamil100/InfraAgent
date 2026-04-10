"""CodeGen agent — generates Bicep/Terraform from structured requirements."""

from __future__ import annotations

import json
import logging

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent, AgentThread, MessageRole

from src.core.models import (
    CodeGenOutput,
    GeneratedFile,
    RequirementsHandoff,
    ValidationFinding,
)
from src.core.ports import ICodeGenPort

logger = logging.getLogger(__name__)


class CodeGenAgent(ICodeGenPort):
    """Adapter that wraps the Foundry-hosted CodeGen agent."""

    def __init__(self, client: AIProjectClient, agent: Agent) -> None:
        self._client = client
        self._agent = agent

    async def generate(
        self,
        requirements: RequirementsHandoff,
        feedback: list[ValidationFinding] | None = None,
    ) -> CodeGenOutput:
        thread: AgentThread = await self._client.agents.create_thread()

        # Build the user message
        payload = requirements.model_dump(mode="json")
        user_msg = f"Generate IaC code for these requirements:\n\n```json\n{json.dumps(payload, indent=2)}\n```"

        if feedback:
            findings = [f.model_dump(mode="json") for f in feedback]
            user_msg += (
                f"\n\nThe previous iteration had these findings — fix them:\n\n"
                f"```json\n{json.dumps(findings, indent=2)}\n```"
            )

        await self._client.agents.create_message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=user_msg,
        )

        run = await self._client.agents.create_run(
            thread_id=thread.id,
            agent_id=self._agent.id,
        )

        # Poll until complete
        while run.status in ("queued", "in_progress", "requires_action"):
            import asyncio
            await asyncio.sleep(1)
            run = await self._client.agents.get_run(
                thread_id=thread.id,
                run_id=run.id,
            )

        if run.status != "completed":
            logger.error("CodeGen run failed: %s", run.last_error)
            return CodeGenOutput(explanation=f"Agent run failed: {run.last_error}")

        # Extract the assistant response
        messages = await self._client.agents.list_messages(thread_id=thread.id)
        assistant_msgs = [
            m for m in messages.data if m.role == MessageRole.AGENT
        ]
        if not assistant_msgs:
            return CodeGenOutput(explanation="No response from CodeGen agent.")

        content = assistant_msgs[0].content[0].text.value

        # Parse JSON from the response
        return _parse_codegen_response(content)


def _parse_codegen_response(text: str) -> CodeGenOutput:
    """Extract the JSON block from the agent's markdown response."""
    try:
        # Find ```json ... ``` block
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        raw = text[start:end].strip()
        data = json.loads(raw)

        files = [GeneratedFile(**f) for f in data.get("files", [])]
        return CodeGenOutput(
            files=files,
            mermaid_diagram=data.get("mermaid_diagram", ""),
            explanation=data.get("explanation", ""),
        )
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse CodeGen JSON: %s", exc)
        return CodeGenOutput(explanation=text)
