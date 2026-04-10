"""Review agent — runs Standards + Security checks via Foundry agents."""

from __future__ import annotations

import json
import logging

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent, AgentThread, MessageRole

from src.core.models import GeneratedFile, Severity, ValidationFinding
from src.core.ports import ISecurityPort, IStandardsPort

logger = logging.getLogger(__name__)


class _ReviewAgentBase:
    """Shared logic for Standards and Security agents."""

    def __init__(
        self, client: AIProjectClient, agent: Agent, checker_name: str
    ) -> None:
        self._client = client
        self._agent = agent
        self._checker = checker_name

    async def _run_review(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        thread: AgentThread = await self._client.agents.create_thread()

        files_payload = [f.model_dump(mode="json") for f in files]
        user_msg = (
            f"Review this IaC code:\n\n```json\n{json.dumps(files_payload, indent=2)}\n```"
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

        while run.status in ("queued", "in_progress", "requires_action"):
            import asyncio
            await asyncio.sleep(1)
            run = await self._client.agents.get_run(
                thread_id=thread.id,
                run_id=run.id,
            )

        if run.status != "completed":
            logger.error("%s review failed: %s", self._checker, run.last_error)
            return [
                ValidationFinding(
                    checker=self._checker,
                    severity=Severity.ERROR,
                    message=f"Agent run failed: {run.last_error}",
                )
            ]

        messages = await self._client.agents.list_messages(thread_id=thread.id)
        assistant_msgs = [
            m for m in messages.data if m.role == MessageRole.AGENT
        ]
        if not assistant_msgs:
            return []

        content = assistant_msgs[0].content[0].text.value
        return _parse_findings(content, self._checker)


class StandardsAgent(_ReviewAgentBase, IStandardsPort):
    def __init__(self, client: AIProjectClient, agent: Agent) -> None:
        super().__init__(client, agent, "standards")

    async def check(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        return await self._run_review(files)


class SecurityAgent(_ReviewAgentBase, ISecurityPort):
    def __init__(self, client: AIProjectClient, agent: Agent) -> None:
        super().__init__(client, agent, "security")

    async def scan(self, files: list[GeneratedFile]) -> list[ValidationFinding]:
        return await self._run_review(files)


def _parse_findings(text: str, default_checker: str) -> list[ValidationFinding]:
    """Parse a JSON array of findings from the agent response."""
    try:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        raw = text[start:end].strip()
        data = json.loads(raw)
        if not isinstance(data, list):
            data = [data]
        return [
            ValidationFinding(
                checker=item.get("checker", default_checker),
                severity=Severity(item.get("severity", "info")),
                resource=item.get("resource", ""),
                file=item.get("file", ""),
                line=item.get("line", 0),
                message=item.get("message", ""),
                remediation=item.get("remediation", ""),
            )
            for item in data
        ]
    except (ValueError, json.JSONDecodeError, KeyError):
        return []
