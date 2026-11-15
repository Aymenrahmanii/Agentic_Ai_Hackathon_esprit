import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Check the provider's console for the models your account can use, then set AFI_MODEL.
_DEFAULT_MODELS = {"openai_compat": "openai/gpt-oss-120b", "anthropic": "claude-opus-5-5"}


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


def load_settings() -> Settings:
    provider = os.environ.get("AFI_PROVIDER", "openai_compat")
    max_tokens = os.environ.get("AFI_MAX_TOKENS")
    return Settings(
        provider=provider,
        model=os.environ.get("AFI_MODEL") or _DEFAULT_MODELS.get(provider, ""),
        # openai_compat only: any OpenAI-compatible endpoint (Groq, Gemini, OpenRouter, Ollama).
        base_url=os.environ.get("AFI_BASE_URL", GROQ_BASE_URL),
        api_key=os.environ.get("AFI_API_KEY", ""),
        # anthropic only. Replies are spoken, so latency matters more than depth; raise it if
        # the eval shows tool-routing mistakes.
        effort=os.environ.get("AFI_EFFORT", "low"),
        # Unset means the provider's own default (free tiers often cap output well below 16k).
        max_tokens=int(max_tokens) if max_tokens else None,
        max_agent_steps=int(os.environ.get("AFI_MAX_AGENT_STEPS", "6")),
        seed_path=Path(os.environ.get("AFI_SEED_PATH", PROJECT_ROOT / "data" / "seed.json")),
    )
