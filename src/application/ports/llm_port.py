"""LLM Completion port interface.

Contract between the application layer and any LLM provider (Azure OpenAI, Anthropic, etc.).
Ref: TechSpec Section 2.1, lines 153-172
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """A message in an LLM conversation.

    Fields:
        role: "user" | "assistant" | "system"
        content: The message text
    """
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM completion call.

    Fields:
        content: The generated text
        tool_calls: List of tool invocations (if any)
        usage: Token/cost metrics
        model_used: Actual model selected by ModelRouter (for logging/audit)
    """
    content: str
    tool_calls: list[dict] | None = None
    usage: dict | None = None
    model_used: str | None = None


@dataclass
class ToolDefinition:
    """Definition of a tool the LLM can call.

    Fields:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON schema for tool inputs
    """
    name: str
    description: str
    input_schema: dict


@dataclass
class TaskProfile:
    """Declares agent intent for ModelRouter-based model selection.

    Used to route different LLM tasks to appropriate models:
    - "complex-reasoning": Chain-of-thought, multi-step problems
    - "code-generation": IaC generation, structured outputs
    - "analysis": Report generation, summarization
    - "fast-lightweight": Quick decisions, simple responses
    - "orchestration": Multi-agent coordination

    Fields:
        profile: Task type (above values)
        max_tokens: Maximum response tokens
        temperature: Sampling temperature (0.0-1.0)
    """
    profile: str  # "complex-reasoning" | "code-generation" | "analysis" | "fast-lightweight" | "orchestration"
    max_tokens: int = 4096
    temperature: float = 0.2


class ILLMCompletionPort(ABC):
    """Abstracts over LLM providers (Azure OpenAI, Anthropic, etc.) with ModelRouter support.

    Methods route tasks through ModelRouter for intelligent model selection based on TaskProfile.
    """

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        """Generate a completion from an LLM.

        Args:
            system_prompt: System role message
            messages: Conversation history
            task_profile: Optional profile for ModelRouter-based model selection

        Returns:
            LLMResponse with generated content and model_used
        """
        ...

    @abstractmethod
    async def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
        tool_executor: callable,
        task_profile: TaskProfile | None = None,
    ) -> LLMResponse:
        """Generate a completion with tool-calling capability.

        Args:
            system_prompt: System role message
            messages: Conversation history
            tools: Available tools the LLM can invoke
            tool_executor: Callable to execute tool calls and return results
            task_profile: Optional profile for ModelRouter-based model selection

        Returns:
            LLMResponse with tool calls and final content
        """
        ...
