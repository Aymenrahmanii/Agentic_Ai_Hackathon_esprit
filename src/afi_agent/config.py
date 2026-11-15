import os
from dataclasses import dataclass, field, replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass(frozen=True)
class ProviderPreset:
    base_url: str
    key_env: str
    model_env: str
    default_model: str


# OpenAI-compatible endpoints, each with its own key and model variables so several providers
# can be configured in one .env. Check each console for the models your account can use.
PROVIDER_PRESETS = {
    "gemini": ProviderPreset(
        GEMINI_BASE_URL, "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-3.5-flash-lite"
    ),
    "groq": ProviderPreset(GROQ_BASE_URL, "GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-120b"),
}

# For AFI_PROVIDER=openai_compat (any endpoint, set AFI_BASE_URL) or anthropic.
_DEFAULT_MODELS = {"openai_compat": "", "anthropic": "claude-opus-5-5"}


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    base_url: str
    api_key: str = field(repr=False)
    effort: str
    max_tokens: int | None
    max_agent_steps: int
    seed_path: Path
    # Preset name used when the primary provider is rate-limited or down; None disables it.
    fallback_provider: str | None = None


def with_provider_preset(settings: Settings, name: str) -> Settings:
    if name not in PROVIDER_PRESETS:
        known = ", ".join(sorted(PROVIDER_PRESETS))
        raise ValueError(f"Unknown provider preset '{name}' (known: {known})")
    preset = PROVIDER_PRESETS[name]
    return replace(
        settings,
        provider="openai_compat",
        base_url=preset.base_url,
        api_key=os.environ.get(preset.key_env, ""),
        model=os.environ.get(preset.model_env) or preset.default_model,
    )


def load_settings() -> Settings:
    provider = os.environ.get("AFI_PROVIDER", "gemini")
    max_tokens = os.environ.get("AFI_MAX_TOKENS")
    settings = Settings(
        provider=provider,
        model=os.environ.get("AFI_MODEL") or _DEFAULT_MODELS.get(provider, ""),
        # openai_compat only: any OpenAI-compatible endpoint (OpenRouter, Ollama, ...).
        base_url=os.environ.get("AFI_BASE_URL", ""),
        api_key=os.environ.get("AFI_API_KEY", ""),
        # anthropic only. Replies are spoken, so latency matters more than depth; raise it if
        # the eval shows tool-routing mistakes.
        effort=os.environ.get("AFI_EFFORT", "low"),
        # Unset means the provider's own default (free tiers often cap output well below 16k).
        max_tokens=int(max_tokens) if max_tokens else None,
        max_agent_steps=int(os.environ.get("AFI_MAX_AGENT_STEPS", "6")),
        seed_path=Path(os.environ.get("AFI_SEED_PATH", PROJECT_ROOT / "data" / "seed.json")),
        fallback_provider=os.environ.get("AFI_FALLBACK_PROVIDER", "groq") or None,
    )
    if provider in PROVIDER_PRESETS:
        settings = with_provider_preset(settings, provider)
    if settings.fallback_provider == provider:
        settings = replace(settings, fallback_provider=None)
    return settings
