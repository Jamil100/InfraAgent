"""Unit tests for AzureOpenAIAdapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

from src.application.ports.llm_port import LLMMessage, TaskProfile, ToolDefinition
from src.infrastructure.adapters.azure_openai_adapter import AzureOpenAIAdapter


def _fake_response(
    *,
    content: str = "",
    tool_calls: list[SimpleNamespace] | None = None,
    model: str = "gpt-4o",
    prompt_tokens: int = 1,
    completion_tokens: int = 2,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        model=model,
    )


def _adapter_with_create(create_mock: mock.AsyncMock) -> AzureOpenAIAdapter:
    openai_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
    project_client = SimpleNamespace(get_openai_client=mock.Mock(return_value=openai_client))
    return AzureOpenAIAdapter(project_client=project_client, base_backoff_seconds=0.001)


@pytest.mark.asyncio
async def test_complete_routes_task_profile_and_tracks_usage() -> None:
    create_mock = mock.AsyncMock(
        return_value=_fake_response(content="done", model="gpt-4o-mini", prompt_tokens=10, completion_tokens=5)
    )
    adapter = _adapter_with_create(create_mock)

    response = await adapter.complete(
        "system",
        [LLMMessage(role="user", content="hello")],
        task_profile=TaskProfile(profile="analysis", max_tokens=123, temperature=0.1),
    )

    assert response.content == "done"
    assert response.model_used == "gpt-4o-mini"
    assert response.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    kwargs = create_mock.await_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["extra_body"]["model_router_profile"] == "analysis"
    assert kwargs["max_tokens"] == 123
    assert kwargs["temperature"] == 0.1


@pytest.mark.asyncio
async def test_complete_falls_back_model_on_rate_limit_error_text() -> None:
    create_mock = mock.AsyncMock(
        side_effect=[
            Exception("rate limit exceeded"),
            _fake_response(content="ok", model="gpt-4o-mini"),
        ]
    )
    adapter = _adapter_with_create(create_mock)

    response = await adapter.complete(
        "system",
        [LLMMessage(role="user", content="hello")],
        task_profile=TaskProfile(profile="complex-reasoning"),
    )

    assert response.content == "ok"
    first_call = create_mock.await_args_list[0].kwargs
    second_call = create_mock.await_args_list[1].kwargs
    assert first_call["model"] == "gpt-4o"
    assert second_call["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_complete_retries_with_exponential_backoff() -> None:
    create_mock = mock.AsyncMock(
        side_effect=[TimeoutError("temporary timeout"), _fake_response(content="retry success")]
    )
    adapter = _adapter_with_create(create_mock)

    with mock.patch("asyncio.sleep", new=mock.AsyncMock()) as sleep_mock:
        response = await adapter.complete("system", [LLMMessage(role="user", content="hello")])

    assert response.content == "retry success"
    sleep_mock.assert_awaited_once_with(0.001)


@pytest.mark.asyncio
async def test_complete_with_tools_executes_tool_loop() -> None:
    first = _fake_response(
        tool_calls=[
            SimpleNamespace(
                id="call-1",
                type="function",
                function=SimpleNamespace(name="lookup", arguments='{"id":"42"}'),
            )
        ],
    )
    second = _fake_response(content="final answer")
    create_mock = mock.AsyncMock(side_effect=[first, second])
    adapter = _adapter_with_create(create_mock)
    tool_executor = mock.AsyncMock(return_value={"value": "result"})

    response = await adapter.complete_with_tools(
        "system",
        [LLMMessage(role="user", content="fetch it")],
        tools=[ToolDefinition(name="lookup", description="Lookup data", input_schema={"type": "object"})],
        tool_executor=tool_executor,
        task_profile=TaskProfile(profile="code-generation"),
    )

    assert response.content == "final answer"
    tool_executor.assert_awaited_once_with("lookup", {"id": "42"})
    second_call_messages = create_mock.await_args_list[1].kwargs["messages"]
    assert any(msg.get("role") == "tool" and msg.get("tool_call_id") == "call-1" for msg in second_call_messages)
