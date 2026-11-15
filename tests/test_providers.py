from dataclasses import replace

import pytest

from afi_agent.config import GEMINI_BASE_URL, GROQ_BASE_URL, load_settings, with_provider_preset
from afi_agent.llm import (
    FallbackLLM,
    LLMError,
    OpenAICompatLLM,
    ScriptedLLM,
    ToolCall,
    build_llm,
    scripted_turn,
    to_openai_messages,
)

_ENV_VARS = (
    "AFI_PROVIDER",
    "AFI_FALLBACK_PROVIDER",
    "AFI_MODEL",
    "AFI_BASE_URL",
    "AFI_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class FailingLLM:
    def __init__(self, *, retryable: bool) -> None:
        self.calls = 0
        self._retryable = retryable

    def complete(self, **_: object) -> object:
        self.calls += 1
        raise LLMError("primary down", retryable=self._retryable)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def ask(llm: object) -> str:
    return llm.complete(system="S", messages=[], tools=[]).text  # type: ignore[attr-defined]


def test_default_is_gemini_with_groq_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")

    settings = load_settings()

    assert settings.provider == "openai_compat"
    assert settings.base_url == GEMINI_BASE_URL
    assert settings.api_key == "test-gemini"
    assert settings.model == "gemini-3.5-flash-lite"
    assert settings.fallback_provider == "groq"


def test_preset_model_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    settings = load_settings()

    assert (settings.base_url, settings.model) == (GROQ_BASE_URL, "qwen/qwen3.8-27b")


def test_fallback_to_the_same_provider_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFI_PROVIDER", "groq")
    assert load_settings().fallback_provider is None


def test_empty_fallback_disables_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFI_FALLBACK_PROVIDER", "")
    assert load_settings().fallback_provider is None


def test_unknown_preset_is_rejected() -> None:
    with pytest.raises(ValueError, match="gemini"):
        with_provider_preset(load_settings(), "mystery")


def test_build_llm_wraps_with_fallback_only_when_the_backup_has_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    assert isinstance(build_llm(load_settings()), OpenAICompatLLM)

    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    assert isinstance(build_llm(load_settings()), FallbackLLM)


def test_missing_primary_key_names_the_variables() -> None:
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        build_llm(load_settings())


def test_fallback_answers_and_sticks_to_the_backup_during_the_cooldown() -> None:
    primary = FailingLLM(retryable=True)
    backup = ScriptedLLM([scripted_turn("one"), scripted_turn("two"), scripted_turn("three")])
    clock = Clock()
    llm = FallbackLLM(primary, backup, cooldown_s=60, clock=clock)

    assert ask(llm) == "one"
    clock.now = 30
    assert ask(llm) == "two"
    assert primary.calls == 1  # not retried during the cooldown
    assert llm.using_backup

    clock.now = 61
    assert ask(llm) == "three"
    assert primary.calls == 2  # tried again after the cooldown


def test_primary_is_used_while_it_works() -> None:
    primary = ScriptedLLM([scripted_turn("primary")])
    backup = ScriptedLLM([])

    assert ask(FallbackLLM(primary, backup)) == "primary"
    assert backup.call_count == 0


def test_non_retryable_errors_are_not_hidden_by_the_fallback() -> None:
    backup = ScriptedLLM([scripted_turn("backup")])
    llm = FallbackLLM(FailingLLM(retryable=False), backup)

    with pytest.raises(LLMError, match="primary down"):
        ask(llm)
    assert backup.call_count == 0


def test_gemini_signatures_are_not_sent_to_other_providers() -> None:
    call = ToolCall("c1", "search_lots", {}, extra_content={"google": {"thought_signature": "x"}})
    transcript = [
        {"role": "assistant", "content": scripted_turn(tool_calls=[call]).assistant_content}
    ]

    to_gemini = to_openai_messages("S", transcript)[1]["tool_calls"][0]
    to_groq = to_openai_messages("S", transcript, send_extra_content=False)[1]["tool_calls"][0]

    assert "extra_content" in to_gemini
    assert "extra_content" not in to_groq


def test_only_the_gemini_adapter_sends_signatures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    settings = load_settings()

    gemini = build_llm(replace(settings, fallback_provider=None))
    groq = build_llm(replace(with_provider_preset(settings, "groq"), fallback_provider=None))

    assert gemini._send_extra_content is True  # type: ignore[attr-defined]
    assert groq._send_extra_content is False  # type: ignore[attr-defined]
