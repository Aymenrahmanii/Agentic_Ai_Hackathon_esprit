import pytest

from afi_agent.language import dominant_script, latin_language
from afi_agent.style_checks import (
    has_markdown,
    language_ok,
    references_ok,
    script_ok,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("في القيروان عنا أرضين، الأرض L-KAI-001 مساحتها 2000 م²", "arabic"),
        ("Fi Sfax 3andna zouz araadhi, L-SFX-001 w L-SFX-002", "latin"),
        ("Le lot L-BEJ-001 fait 6000 m2.", "latin"),
        ("L-KAI-001", None),
    ],
)
def test_dominant_script_ignores_ids_and_units(text: str, expected: str | None) -> None:
    assert dominant_script(text) == expected


def test_arabizi_question_answered_in_arabic_script_fails_the_script_check() -> None:
    assert not script_ok("derja-latin", "عندنا في صفاقس زوز أراضي صناعية")
    assert script_ok("derja-latin", "3andna fi Sfax zouz araadhi")
    assert script_ok("unknown-tag", "anything")


def test_words_mixing_arabic_and_latin_letters_fail_the_script_check() -> None:
    reply = "Fi Sfax fama lot L-SFX-001. Nجم نعملlek draft."
    assert not script_ok("derja-latin", reply)
    # Separate words in different scripts are fine, as in an Arabic reply quoting an id, and so
    # is Arabic punctuation right after a Latin word.
    assert script_ok("derja-ar", "القطعة L-KAI-001 متوفرة في القيروان، تستخرج الاستمارة من AFI، ")


def test_latin_language_tells_french_from_english() -> None:
    assert latin_language("Votre demande a bien été transmise à un agent AFI.") == "fr"
    assert latin_language("You have been placed in the queue for a human agent.") == "en"
    assert latin_language("L-KAI-001") is None


def test_english_question_answered_in_french_fails_the_language_check() -> None:
    french = "Votre demande a bien été transmise à un agent AFI."
    assert not language_ok("en", french)
    assert language_ok("fr", french)
    assert language_ok("derja-ar", french)  # not checked for Arabic-script languages


@pytest.mark.parametrize(
    "text",
    ["Le lot **L-KAI-001**", "## Titre", "- premier point", "1. premier", "| a | b |", "`x`"],
)
def test_has_markdown_detects_common_markup(text: str) -> None:
    assert has_markdown(text)


def test_has_markdown_ignores_plain_sentences_and_negative_prices() -> None:
    assert not has_markdown("Le lot coûte 90 000 dinars - prix fixe. Il fait 2000 m².")


def test_references_must_appear_in_the_reply() -> None:
    outputs = [{"ticket_id": "TICKET-0001", "status": "queued"}, {"count": 2}]
    assert references_ok("Votre ticket est TICKET-0001.", outputs)
    assert not references_ok("Votre demande a été transmise.", outputs)
    assert references_ok("Aucune référence.", [{"count": 0}])
