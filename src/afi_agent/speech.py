"""Turn a model reply into plain text a text-to-speech voice can read.

The prompt already asks for plain sentences; this catches what models produce anyway."""

import re

# Look-alike characters models emit: hyphens U+2010-U+2013 inside ids (an id written with
# U+2011 breaks exact matching), and no-break spaces U+00A0/U+202F that trip some TTS engines.
_HYPHENS = str.maketrans(
    {0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x00A0: " ", 0x202F: " "}
)

_MARKUP = [
    (re.compile(r"```.*?```", re.DOTALL), " "),
    (re.compile(r"\*\*|__|`"), ""),
    (re.compile(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)"), r"\1"),
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE), ""),
    (re.compile(r"\s*(?:→|=>|->)\s*"), ", "),
    (re.compile(r"[«»]"), ""),
]

_SENTENCE_END = re.compile(r"[.!?؟:،,;]$")


def to_speech_text(text: str) -> str:
    cleaned = text.translate(_HYPHENS)
    for pattern, replacement in _MARKUP:
        cleaned = pattern.sub(replacement, cleaned)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    # Joined list items need a pause between them, or TTS runs them together.
    parts = [line if _SENTENCE_END.search(line) else line + "." for line in lines[:-1]]
    if lines:
        parts.append(lines[-1])
    return re.sub(r"\s{2,}", " ", " ".join(parts)).strip()
