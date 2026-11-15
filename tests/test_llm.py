import json
from dataclasses import replace
from typing import Any

import httpx
import openai
import pytest
from openai.types.chat import ChatCompletion

from afi_agent.agent import Agent
from afi_agent.config import load_settings
from afi_agent.llm import (
    INVALID_ARGUMENTS_KEY,
    AnthropicLLM,
    LLMError,
    OpenAICompatLLM,
    ToolCall,
    build_llm,
    scripted_turn,
    to_openai_messages,
    to_openai_tools,
)
from afi_agent.tools import ToolContext, tool_schemas


def completion(message: dict[str, Any], finish_reason: str) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish_reason,
                    "message": {"role": "assistant"} | message,
                }
            ],
        }
    )


def tool_call_message(call_id: str, name: str, arguments: str) -> dict[str, Any]:
    return {
        "content": None,
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}
        ],
    }


class FakeOpenAIClient:
    """Stands in for openai.OpenAI: replays completions and records each request."""

    def __init__(self, completions: list[ChatCompletion]) -> None:
        self._completions = iter(completions)
        self.requests: list[dict[str, Any]] = []
        self.chat = self
        self.completions = self

    def create(self, **request: Any) -> ChatCompletion:
        self.requests.append(json.loads(json.dumps(request)))
        return next(self._completions)


def compat_llm(client: FakeOpenAIClient, **kwargs: Any) -> OpenAICompatLLM:
    return OpenAICompatLLM(model="test-model", base_url="", api_key="", client=client, **kwargs)


def test_tools_are_wrapped_as_functions(ctx: ToolContext) -> None:
    schemas = tool_schemas(ctx.store)
    converted = to_openai_tools(schemas)

    assert [t["function"]["name"] for t in converted] == [s["name"] for s in schemas]
    assert all(t["type"] == "function" for t in converted)
    assert converted[0]["function"]["parameters"] == schemas[0]["input_schema"]


def test_transcript_is_translated_to_openai_messages() -> None:
    turn = scripted_turn(
        "Je cherche.",
        [
            ToolCall("t1", "search_lots", {"governorate": "القيروان"}),
            ToolCall("t2", "get_procedure", {"procedure_id": "reservation_lot"}),
        ],
    )
    transcript = [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": turn.assistant_content},
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "{}", "is_error": False},
                {"type": "tool_result", "tool_use_id": "t2", "content": "{}", "is_error": True},
            ],
        },
    ]

    converted = to_openai_messages("SYSTEM", transcript)

    assert [m["role"] for m in converted] == ["system", "user", "assistant", "tool", "tool"]
    assert converted[0]["content"] == "SYSTEM"
    assistant = converted[2]
    assert assistant["content"] == "Je cherche."
    assert [c["id"] for c in assistant["tool_calls"]] == ["t1", "t2"]
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {
        "governorate": "القيروان"
    }
    assert [m["tool_call_id"] for m in converted[3:]] == ["t1", "t2"]


def test_assistant_message_without_text_or_tools() -> None:
    transcript = [{"role": "assistant", "content": scripted_turn("Bonjour").assistant_content}]

    assistant = to_openai_messages("S", transcript)[1]

    assert assistant == {"role": "assistant", "content": "Bonjour"}


def test_complete_parses_a_tool_call() -> None:
    client = FakeOpenAIClient(
        [
            completion(
                tool_call_message("c1", "search_lots", '{"governorate": "Sfax"}'), "tool_calls"
            )
        ]
    )

    turn = compat_llm(client).complete(system="S", messages=[], tools=[])

    assert turn.stop_reason == "tool_use"
    assert turn.tool_calls == [ToolCall("c1", "search_lots", {"governorate": "Sfax"})]
    assert turn.assistant_content == [
        {"type": "tool_use", "id": "c1", "name": "search_lots", "input": {"governorate": "Sfax"}}
    ]
    assert "max_completion_tokens" not in client.requests[0]


def test_complete_parses_text_and_sends_max_tokens_when_set() -> None:
    client = FakeOpenAIClient([completion({"content": "Bonjour"}, "stop")])

    turn = compat_llm(client, max_tokens=500).complete(system="S", messages=[], tools=[])

    assert (turn.text, turn.stop_reason, turn.tool_calls) == ("Bonjour", "end_turn", [])
    assert client.requests[0]["max_completion_tokens"] == 500


@pytest.mark.parametrize("arguments", ["{not json", "[1, 2]"])
def test_unparseable_arguments_become_a_tool_error(ctx: ToolContext, arguments: str) -> None:
    client = FakeOpenAIClient(
        [
            completion(tool_call_message("c1", "search_lots", arguments), "tool_calls"),
            completion({"content": "Pardon, je réessaie."}, "stop"),
        ]
    )

    reply = Agent(compat_llm(client), ctx).respond([], "Des lots ?")

    assert reply.tool_records[0].input == {INVALID_ARGUMENTS_KEY: arguments}
    assert reply.tool_records[0].is_error


def test_full_turn_round_trips_through_the_adapter(ctx: ToolContext) -> None:
    client = FakeOpenAIClient(
        [
            completion(
                tool_call_message("c1", "search_lots", '{"governorate": "Kairouan"}'), "tool_calls"
            ),
            completion({"content": "Deux lots sont disponibles."}, "stop"),
        ]
    )

    reply = Agent(compat_llm(client), ctx).respond([], "Des lots à Kairouan ?")

    assert reply.text == "Deux lots sont disponibles."
    assert reply.tool_records[0].output["count"] == 2
    second_request = client.requests[1]["messages"]
    assert [m["role"] for m in second_request] == ["system", "user", "assistant", "tool"]
    assert second_request[3]["tool_call_id"] == "c1"
    assert json.loads(second_request[3]["content"])["count"] == 2


def bad_request(message: str) -> openai.BadRequestError:
    response = httpx.Response(400, request=httpx.Request("POST", "https://example.invalid"))
    return openai.BadRequestError(message, response=response, body={"error": {"message": message}})


class FlakyClient(FakeOpenAIClient):
    def __init__(self, failures: list[Exception], completions: list[ChatCompletion]) -> None:
        super().__init__(completions)
        self._failures = iter(failures)

    def create(self, **request: Any) -> ChatCompletion:
        failure = next(self._failures, None)
        if failure is not None:
            self.requests.append(request)
            raise failure
        return super().create(**request)


def test_gemini_thought_signature_is_sent_back_with_the_tool_call(ctx: ToolContext) -> None:
    signature = {"google": {"thought_signature": "c2lnbmF0dXJl"}}
    first = tool_call_message("c1", "search_lots", '{"governorate": "Sfax"}')
    first["tool_calls"][0]["extra_content"] = signature
    client = FakeOpenAIClient(
        [completion(first, "tool_calls"), completion({"content": "Deux lots."}, "stop")]
    )

    Agent(compat_llm(client), ctx).respond([], "Lots à Sfax ?")

    echoed = client.requests[1]["messages"][2]["tool_calls"][0]
    assert echoed["extra_content"] == signature


def test_calls_without_extras_send_no_extra_content() -> None:
    client = FakeOpenAIClient(
        [completion(tool_call_message("c1", "search_lots", "{}"), "tool_calls")]
    )

    turn = compat_llm(client).complete(system="S", messages=[], tools=[])

    assert turn.tool_calls[0].extra_content is None
    assert "extra_content" not in turn.assistant_content[0]


def test_malformed_tool_call_400_is_retried() -> None:
    client = FlakyClient(
        [bad_request("Failed to parse tool call arguments as JSON")],
        [completion({"content": "Bonjour"}, "stop")],
    )

    turn = compat_llm(client).complete(system="S", messages=[], tools=[])

    assert turn.text == "Bonjour"
    assert len(client.requests) == 2


def test_other_400s_and_repeated_tool_failures_are_not_hidden() -> None:
    other = FlakyClient([bad_request("model not found")], [])
    with pytest.raises(LLMError, match="model not found"):
        compat_llm(other).complete(system="S", messages=[], tools=[])
    assert len(other.requests) == 1

    malformed = bad_request("tool_use_failed")
    always = FlakyClient([malformed, malformed, malformed], [])
    with pytest.raises(LLMError):
        compat_llm(always).complete(system="S", messages=[], tools=[])
    assert len(always.requests) == 3


def test_build_llm_selects_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-placeholder")

    compat = build_llm(replace(settings, provider="openai_compat", api_key="test-placeholder"))
    claude = build_llm(replace(settings, provider="anthropic", model="claude-opus-5-5"))

    assert isinstance(compat, OpenAICompatLLM)
    assert isinstance(claude, AnthropicLLM)


def test_build_llm_reports_missing_key_and_unknown_provider() -> None:
    settings = load_settings()

    with pytest.raises(LLMError, match="AFI_API_KEY"):
        build_llm(replace(settings, provider="openai_compat", api_key=""))
    with pytest.raises(LLMError, match="Unknown AFI_PROVIDER"):
        build_llm(replace(settings, provider="mystery"))


def test_settings_repr_hides_the_key() -> None:
    settings = replace(load_settings(), api_key="super-secret-value")
    assert "super-secret-value" not in repr(settings)
