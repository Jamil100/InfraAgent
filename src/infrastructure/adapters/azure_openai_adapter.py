"""Azure OpenAI adapter implementing ILLMCompletionPort with ModelRouter-aware routing."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Callable
from typing import Any

from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from src.application.ports.llm_port import (
    ILLMCompletionPort,
    LLMMessage,
    LLMResponse,
    TaskProfile,
    ToolDefinition,
)
from src.config import settings

logger = logging.getLogger(__name__)
_MODEL_ROUTER_PARAM_SUPPORT_CACHE: dict[int, bool] = {}
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_TOKENS = 4096

_PROFILE_TO_MODEL = {
    "complex-reasoning": "gpt-4o",
    "code-generation": "gpt-4o",
    "analysis": "gpt-4o-mini",
    "fast-lightweight": "gpt-4o-mini",
    "orchestration": "gpt-4o",
}
_FALLBACK_MODEL = {
    "gpt-4o": "gpt-4o-mini",
}


def _supports_model_router_profile_param(create_callable: Any) -> bool:
    cache_key = id(create_callable)
    if cache_key not in _MODEL_ROUTER_PARAM_SUPPORT_CACHE:
        _MODEL_ROUTER_PARAM_SUPPORT_CACHE[cache_key] = "model_router_profile" in inspect.signature(
            create_callable
        ).parameters
    return _MODEL_ROUTER_PARAM_SUPPORT_CACHE[cache_key]


class AzureOpenAIAdapter(ILLMCompletionPort):
    """Adapter for chat completions through Azure AI Foundry / ModelRouter."""

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        credential: AsyncTokenCredential | None = None,
        project_client: AIProjectClient | None = None,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        max_tool_iterations: int = 8,
    ) -> None:
        self._project_client = project_client or AIProjectClient(
            endpoint=endpoint or settings.project_endpoint,
            credential=credential or DefaultAzureCredential(),
        )
        self._openai_client: AsyncOpenAI = self._project_client.get_openai_client()
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._max_tool_iterations = max_tool_iterations
        self._supports_model_router_profile_param = _supports_model_router_profile_param(
            self._openai_client.chat.completions.create
        )

    async def complete(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        openai_messages = self._build_messages(system_prompt, messages)
        response = await self._complete_raw(
            messages=openai_messages,
            task_profile=task_profile,
            tools=None,
        )
        return self._to_llm_response(response)

    async def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
        tool_executor: Callable[..., Any],
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        conversation = self._build_messages(system_prompt, messages)
        openai_tools = self._build_tools(tools)
        latest_response: LLMResponse | None = None

        for _ in range(self._max_tool_iterations):
            response = await self._complete_raw(
                messages=conversation,
                task_profile=task_profile,
                tools=openai_tools,
            )
            latest_response = self._to_llm_response(response)
            tool_calls = latest_response.tool_calls or []

            if not tool_calls:
                return latest_response

            conversation.append(
                {
                    "role": "assistant",
                    "content": latest_response.content,
                    "tool_calls": [self._to_openai_tool_call(tc) for tc in tool_calls],
                }
            )

            for tool_call in tool_calls:
                tool_name = str(tool_call.get("name", ""))
                args = tool_call.get("arguments") or {}
                result = await self._execute_tool(tool_executor, tool_name, args, tool_call)
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": self._serialize_tool_result(result),
                    }
                )

        return latest_response or LLMResponse(content="")

    async def _complete_raw(
        self,
        *,
        messages: list[dict[str, Any]],
        task_profile: TaskProfile | None,
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        profile = task_profile.profile if task_profile else None
        primary_model = _PROFILE_TO_MODEL.get(profile or "", settings.model_deployment)
        fallback_model = _FALLBACK_MODEL.get(primary_model)

        model_to_use = primary_model
        fallback_tried = False
        attempt = 0

        while True:
            try:
                request_kwargs = self._build_request_kwargs(
                    model=model_to_use,
                    task_profile=task_profile,
                    messages=messages,
                    tools=tools,
                )
                return await self._openai_client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                if fallback_model and not fallback_tried and self._should_fallback_model(exc):
                    logger.warning("Switching to fallback model '%s' after error: %s", fallback_model, exc)
                    model_to_use = fallback_model
                    fallback_tried = True
                    continue
                if attempt >= self._max_retries or not self._should_retry(exc):
                    raise
                await asyncio.sleep(self._base_backoff_seconds * (2**attempt))
                attempt += 1

    def _build_request_kwargs(
        self,
        *,
        model: str,
        task_profile: TaskProfile | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": task_profile.temperature if task_profile else _DEFAULT_TEMPERATURE,
            "max_tokens": task_profile.max_tokens if task_profile else _DEFAULT_MAX_TOKENS,
        }
        if tools:
            kwargs["tools"] = tools

        if task_profile:
            # SDK verification (azure-ai-projects 2.0.1, inspected 2026-04): no first-class
            # model_router_profile parameter on chat.completions.create, so use extra_body.
            if self._supports_model_router_profile_param:
                kwargs["model_router_profile"] = task_profile.profile
            else:
                kwargs["extra_body"] = {"model_router_profile": task_profile.profile}

        return kwargs

    def _build_messages(self, system_prompt: str, messages: list[LLMMessage]) -> list[dict[str, str]]:
        mapped = [{"role": "system", "content": system_prompt}]
        for message in messages:
            mapped.append({"role": message.role, "content": message.content})
        return mapped

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in tools
        ]

    def _to_llm_response(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        content = self._extract_content(getattr(choice.message, "content", ""))
        tool_calls = self._extract_tool_calls(getattr(choice.message, "tool_calls", None))
        usage = self._extract_usage(getattr(response, "usage", None))
        model_used = getattr(response, "model", None)
        return LLMResponse(content=content, tool_calls=tool_calls, usage=usage, model_used=model_used)

    def _extract_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        chunks.append(str(text))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        chunks.append(str(text))
            return "".join(chunks)
        return str(content)

    def _extract_tool_calls(self, tool_calls: Any) -> list[dict[str, Any]] | None:
        if not tool_calls:
            return None
        extracted: list[dict[str, Any]] = []
        for call in tool_calls:
            function = getattr(call, "function", None)
            name = getattr(function, "name", None)
            arguments_raw = getattr(function, "arguments", "{}")
            arguments = self._parse_json_dict(arguments_raw)
            extracted.append(
                {
                    "id": getattr(call, "id", None),
                    "type": getattr(call, "type", "function"),
                    "name": name,
                    "arguments": arguments,
                    "arguments_raw": arguments_raw,
                }
            )
        return extracted

    def _extract_usage(self, usage: Any) -> dict[str, Any] | None:
        if usage is None:
            return None
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    def _parse_json_dict(self, value: str | dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Failed to parse tool arguments as JSON; using empty dict")
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError, TimeoutError)):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code in (408, 409, 425, 429, 500, 502, 503, 504)
        text = str(exc).lower()
        return any(token in text for token in ("timeout", "temporary", "temporarily", "rate limit"))

    def _should_fallback_model(self, exc: Exception) -> bool:
        if isinstance(exc, RateLimitError):
            return True
        if isinstance(exc, APIStatusError) and exc.status_code in (404, 429, 500, 502, 503):
            return True
        text = str(exc).lower()
        return "rate limit" in text or ("model" in text and ("not found" in text or "unavailable" in text))

    def _to_openai_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        raw_arguments = tool_call.get("arguments_raw")
        if raw_arguments is None:
            raw_arguments = json.dumps(tool_call.get("arguments", {}))
        return {
            "id": tool_call.get("id"),
            "type": "function",
            "function": {
                "name": tool_call.get("name"),
                "arguments": raw_arguments,
            },
        }

    async def _execute_tool(
        self,
        tool_executor: Callable[..., Any],
        name: str,
        args: dict[str, Any],
        raw_call: dict[str, Any],
    ) -> Any:
        try:
            result = tool_executor(name, args)
        except TypeError as exc:
            logger.warning("Tool executor signature mismatch for '%s': %s; retrying with raw call", name, exc)
            result = tool_executor(raw_call)
        if inspect.isawaitable(result):
            return await result
        return result

    def _serialize_tool_result(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result)
