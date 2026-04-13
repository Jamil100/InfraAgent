"""Integration-style test for AzureOpenAIAdapter using a mocked Azure endpoint."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.application.ports.llm_port import LLMMessage, TaskProfile
import src.infrastructure.adapters.azure_openai_adapter as azure_openai_adapter


@pytest.mark.asyncio
async def test_complete_uses_mocked_azure_endpoint_and_model_router_param(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    async def create_completion(*, messages, model, model_router_profile=None, **kwargs):  # noqa: ANN001
        observed["messages"] = messages
        observed["model"] = model
        observed["model_router_profile"] = model_router_profile
        observed["kwargs"] = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            model=model,
        )

    fake_openai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_completion)))

    class FakeProjectClient:
        def __init__(self, *, endpoint, credential):  # noqa: ANN001
            observed["endpoint"] = endpoint
            observed["credential"] = credential

        def get_openai_client(self):  # noqa: ANN201
            return fake_openai

    monkeypatch.setattr(azure_openai_adapter, "AIProjectClient", FakeProjectClient)

    adapter = azure_openai_adapter.AzureOpenAIAdapter(
        endpoint="https://mocked-azure-endpoint.example",
        credential=SimpleNamespace(),
    )
    result = await adapter.complete(
        "system",
        [LLMMessage(role="user", content="hello")],
        task_profile=TaskProfile(profile="orchestration"),
    )

    assert observed["endpoint"] == "https://mocked-azure-endpoint.example"
    assert observed["model"] == "gpt-4o"
    assert observed["model_router_profile"] == "orchestration"
    assert result.content == "ok"
