"""Cheap automatic checks on reply style. They catch regressions; they do not judge Derja
quality, which still needs a native speaker."""

import re
from collections.abc import Iterable
from typing import Any

from afi_agent.language import ARABIC_LETTERS, Script, dominant_script, latin_language

# Golden-set language tag -> script the reply must be written in.
EXPECTED_SCRIPT: dict[str, Script] = {
    "derja-ar": "arabic",
    "ar": "arabic",
    "derja-latin": "latin",
    "fr": "latin",
    "en": "latin",
}

_MARKDOWN = re.compile(
    r"\*\*|__|`|^\s{0,3}#{1,6}\s|^\s*(?:[-*•]|\d{1,2}[.)])\s+\S|^\s*\|.*\|\s*$",
    re.MULTILINE,
)

REFERENCE_KEYS = ("ticket_id", "draft_id", "tracking_number")


def has_markdown(text: str) -> bool:
    return bool(_MARKDOWN.search(text))


_MIXED_SCRIPT_WORD = re.compile(f"[A-Za-zÀ-ÿ][{ARABIC_LETTERS}]|[{ARABIC_LETTERS}][A-Za-zÀ-ÿ]")


def has_mixed_script_word(text: str) -> bool:
    """Arabic and Latin letters inside one word, e.g. "Nجم", which TTS cannot read."""
    return bool(_MIXED_SCRIPT_WORD.search(text))


def script_ok(lang: str, reply: str) -> bool:
    if has_mixed_script_word(reply):
        return False
    expected = EXPECTED_SCRIPT.get(lang)
    return expected is None or dominant_script(reply) == expected


def language_ok(lang: str, reply: str) -> bool:
    """Only French and English are told apart; for the others the script check is the test."""
    if lang not in ("fr", "en"):
        return True
    detected = latin_language(reply)
    return detected is None or detected == lang


def references_ok(reply: str, tool_outputs: Iterable[dict[str, Any]]) -> bool:
    """Every id a successful tool call handed back must appear in the reply."""
    references = [
        str(output[key]) for output in tool_outputs for key in REFERENCE_KEYS if key in output
    ]
    return all(ref in reply for ref in references)
