"""LLM seam. The agent keeps its transcript in the Anthropic Messages shape (text, tool_use and
tool_result blocks); each adapter translates that shape to its provider inside `complete`."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic
import openai

from afi_agent.config import Settings

_ANTHROPIC_DEFAULT_MAX_TOKENS = 16000

_OPENAI_STOP_REASONS = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}

# Key that no tool accepts. Tool inputs forbid unknown keys, so unparseable arguments come back
# to the model as a validation error instead of running the tool with empty input.
INVALID_ARGUMENTS_KEY = "invalid_arguments_json"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class LLMTurn:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    # What to append to the transcript as the assistant message content.
    assistant_content: Any


class LLMError(Exception):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLM(Protocol):
    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMTurn: ...


def _content_blocks(text: str, tool_calls: Sequence[ToolCall]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}] if text else []
    blocks.extend(
        {"type": "tool_use", "id": call.id, "name": call.name, "input": call.input}
        for call in tool_calls
    )
    return blocks


class AnthropicLLM:
    def __init__(self, *, model: str, effort: str, max_tokens: int | None) -> None:
        self._client = anthropic.Anthropic()
        self._model = model
        self._effort = effort
        self._max_tokens = max_tokens or _ANTHROPIC_DEFAULT_MAX_TOKENS

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMTurn:
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
                tools=tools,
                output_config={"effort": self._effort},
                # If a safety classifier declines, the API reruns the request on a fallback
                # model inside the same call instead of failing the turn.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise LLMError("Rate limited by the model provider", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(
                f"Model provider error ({exc.status_code}): {exc.message}",
                retryable=exc.status_code >= 500,
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the model provider", retryable=True) from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        tool_calls = [
            ToolCall(id=block.id, name=block.name, input=dict(block.input))
            for block in response.content
            if block.type == "tool_use"
        ]
        return LLMTurn(
            text=text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            assistant_content=response.content,
        )


def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            converted.append({"role": message["role"], "content": content})
        elif message["role"] == "assistant":
            converted.append(_assistant_to_openai(content))
        else:
            converted.extend(
                {"role": "tool", "tool_call_id": block["tool_use_id"], "content": block["content"]}
                for block in content
                if block["type"] == "tool_result"
            )
    return converted


def _assistant_to_openai(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    text = "".join(block["text"] for block in blocks if block["type"] == "text")
    tool_calls = [
        {
            "id": block["id"],
            "type": "function",
            "function": {
                "name": block["name"],
                "arguments": json.dumps(block["input"], ensure_ascii=False),
            },
        }
        for block in blocks
        if block["type"] == "tool_use"
    ]
    message: dict[str, Any] = {"role": "assistant", "content": text or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {INVALID_ARGUMENTS_KEY: raw}
    return parsed if isinstance(parsed, dict) else {INVALID_ARGUMENTS_KEY: raw}


class OpenAICompatLLM:
    """Any endpoint that speaks the OpenAI chat completions format: Groq, Gemini, OpenRouter,
    a local Ollama."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        max_tokens: int | None = None,
        client: openai.OpenAI | None = None,
    ) -> None:
        self._client = client or openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMTurn:
        request: dict[str, Any] = {
            "model": self._model,
            "messages": to_openai_messages(system, messages),
            "tools": to_openai_tools(tools),
        }
        if self._max_tokens is not None:
            request["max_completion_tokens"] = self._max_tokens
        try:
            response = self._client.chat.completions.create(**request)
        except openai.RateLimitError as exc:
            raise LLMError("Rate limited by the model provider", retryable=True) from exc
        except openai.APIStatusError as exc:
            raise LLMError(
                f"Model provider error ({exc.status_code}): {exc.message}",
                retryable=exc.status_code >= 500,
            ) from exc
        except openai.APIConnectionError as exc:
            raise LLMError("Could not reach the model provider", retryable=True) from exc

        choice = response.choices[0]
        text = choice.message.content or ""
        tool_calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                input=_parse_arguments(call.function.arguments),
            )
            for call in choice.message.tool_calls or []
            if call.type == "function"
        ]
        return LLMTurn(
            text=text,
            tool_calls=tool_calls,
            stop_reason=_OPENAI_STOP_REASONS.get(choice.finish_reason, choice.finish_reason),
            assistant_content=_content_blocks(text, tool_calls),
        )


def build_llm(settings: Settings) -> LLM:
    if settings.provider == "anthropic":
        return AnthropicLLM(
            model=settings.model, effort=settings.effort, max_tokens=settings.max_tokens
        )
    if settings.provider == "openai_compat":
        if not settings.api_key:
            raise LLMError("AFI_API_KEY is not set", retryable=False)
        return OpenAICompatLLM(
            model=settings.model,
            base_url=settings.base_url,
            api_key=settings.api_key,
            max_tokens=settings.max_tokens,
        )
    raise LLMError(
        f"Unknown AFI_PROVIDER '{settings.provider}' (use openai_compat or anthropic)",
        retryable=False,
    )


def scripted_turn(
    text: str = "", tool_calls: Sequence[ToolCall] = (), stop_reason: str | None = None
) -> LLMTurn:
    return LLMTurn(
        text=text,
        tool_calls=list(tool_calls),
        stop_reason=stop_reason or ("tool_use" if tool_calls else "end_turn"),
        assistant_content=_content_blocks(text, tool_calls),
    )


@dataclass
class ScriptedLLM:
    """Replays fixed turns. For tests, and for a no-network demo fallback."""

    turns: list[LLMTurn]
    call_count: int = field(default=0, init=False)
    systems: list[str] = field(default_factory=list, init=False)

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMTurn:
        self.systems.append(system)
        if self.call_count >= len(self.turns):
            raise LLMError("ScriptedLLM ran out of turns", retryable=False)
        turn = self.turns[self.call_count]
        self.call_count += 1
        return turn
