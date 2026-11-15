import pytest

from afi_agent.speech import to_speech_text


def test_strips_bold_bullets_and_arrows_from_a_real_reply() -> None:
    raw = (
        "عندنا في صفاقس زوز أراضي صناعية متوفرة في «Zone industrielle Sfax Nord»:\n\n"
        "1. Lot **L‑SFX‑001** – مساحة 1500 م²، السعر 120 د.ت للـم² → الكل ≈ 180 000 د.ت.\n"
        "2. Lot **L‑SFX‑002** – مساحة 8000 م²\n"
    )

    spoken = to_speech_text(raw)

    for marker in ("**", "«", "»", "→", "\n", "1. ", "2. "):
        assert marker not in spoken
    assert "L-SFX-001" in spoken and "L-SFX-002" in spoken
    assert "180 000" in spoken


def test_list_items_are_separated_by_a_pause() -> None:
    assert to_speech_text("Documents:\n- Formulaire\n- Pièce d'identité") == (
        "Documents: Formulaire. Pièce d'identité"
    )


def test_headings_tables_and_code_are_removed() -> None:
    raw = "## Résumé\n| a | b |\n|---|---|\nTexte `code` final.\n```\nx = 1\n```"
    assert to_speech_text(raw) == "Résumé. Texte code final."


@pytest.mark.parametrize(
    "text",
    [
        "Bonjour, le lot L-KAI-001 coûte 90 000 dinars.",
        "باش تحجز أرض صناعية يلزمك أربعة وثائق.",
        "Fi Sfax 3andna zouz araadhi.",
    ],
)
def test_plain_text_is_left_alone(text: str) -> None:
    assert to_speech_text(text) == text


def test_single_asterisk_emphasis_is_removed_but_math_is_not() -> None:
    assert to_speech_text("C'est *très* simple.") == "C'est très simple."
    assert to_speech_text("2 * 3 = 6") == "2 * 3 = 6"
