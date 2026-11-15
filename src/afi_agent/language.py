"""Rough detection of the script and language a message is written in."""

import re
from typing import Literal

Script = Literal["arabic", "latin"]
Language = Literal["arabic_script", "arabizi", "fr", "en"]

# Arabic letters only (U+0621-U+064A and the extended block U+0671-U+06D3), so Arabic
# punctuation such as the comma U+060C does not count. Built from code points because the
# formatter rewrites unicode escapes into invisible literal characters.
ARABIC_LETTERS = f"{chr(0x0621)}-{chr(0x064A)}{chr(0x0671)}-{chr(0x06D3)}"
_ARABIC = re.compile(f"[{ARABIC_LETTERS}]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
# Ids, codes and units are Latin even inside an Arabic message, so they must not count.
_IDS_AND_UNITS = re.compile(r"\b[A-Z0-9][A-Z0-9-]*\d[A-Z0-9-]*\b|\bAFI\b|\bm²|\bm2\b")
# Arabizi writes Arabic sounds with digits inside words: n7eb, 3andi, sina3iya, 9irwen.
_ARABIZI_DIGIT = re.compile(r"[a-z][2-9]|[2-9][a-z]")

_FRENCH_WORDS = frozenset(
    "le la les des du une est sont vous votre vos pour avec dans sur je nous pas "
    "aucun aucune été souhaitez quels quelle comment où faut".split()
)
_ENGLISH_WORDS = frozenset(
    "the a an is are you your for with in on i we not no have has been would what "
    "where how want".split()
)
_WORD = re.compile(r"[a-zà-ÿ']+")


def dominant_script(text: str) -> Script | None:
    stripped = _IDS_AND_UNITS.sub(" ", text)
    arabic, latin = len(_ARABIC.findall(stripped)), len(_LATIN.findall(stripped))
    if arabic == latin == 0:
        return None
    return "arabic" if arabic > latin else "latin"


def latin_language(text: str) -> Literal["fr", "en"] | None:
    words = _WORD.findall(_IDS_AND_UNITS.sub(" ", text).casefold())
    french = sum(word in _FRENCH_WORDS for word in words)
    english = sum(word in _ENGLISH_WORDS for word in words)
    if french == english:
        return None
    return "fr" if french > english else "en"


def is_arabizi(text: str) -> bool:
    return bool(_ARABIZI_DIGIT.search(_IDS_AND_UNITS.sub(" ", text).casefold()))


def detect_language(text: str) -> Language | None:
    script = dominant_script(text)
    if script == "arabic":
        return "arabic_script"
    if script is None:
        return None
    if is_arabizi(text):
        return "arabizi"
    return latin_language(text)


_REPLY_INSTRUCTIONS: dict[Language, str] = {
    "arabic_script": (
        "The user's latest message is in Arabic script. Reply in Arabic script, in the same "
        "variety they used (Tunisian Derja or Modern Standard Arabic)."
    ),
    "arabizi": (
        "The user's latest message is Tunisian Derja written in Latin letters and digits. "
        "Reply the same way, as Tunisians type it: plain Latin letters with 3, 7, 9 and 5 for "
        "Arabic sounds, no Arabic script and no accented letters."
    ),
    "fr": "The user's latest message is in French. Reply in French.",
    "en": (
        "The user's latest message is in English. Reply in English, even though the tool "
        "results are in French."
    ),
}


def reply_language_instruction(user_text: str) -> str | None:
    language = detect_language(user_text)
    return _REPLY_INSTRUCTIONS[language] if language else None
