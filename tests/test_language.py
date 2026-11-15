import json
from pathlib import Path

import pytest

from afi_agent.agent import SYSTEM_PROMPT, Agent
from afi_agent.language import detect_language, reply_language_instruction
from afi_agent.llm import ScriptedLLM, scripted_turn
from afi_agent.tools import ToolContext

GOLDEN = Path(__file__).resolve().parents[1] / "evals" / "golden.jsonl"
# Golden-set tag -> what detect_language should say about the question.
_EXPECTED = {
    "derja-ar": "arabic_script",
    "ar": "arabic_script",
    "derja-latin": "arabizi",
    "fr": "fr",
    "en": "en",
}


@pytest.mark.parametrize(
    "case",
    [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line],
    ids=lambda case: case["id"],
)
def test_every_golden_question_is_detected_correctly(case: dict) -> None:
    assert detect_language(case["question"]) == _EXPECTED[case["lang"]]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Je veux le lot L-KAI-001", "fr"),
        ("I want lot L-SBZ-002 please", "en"),
        ("Compare Kairouan and Sidi Bouzid zones.", "en"),
        ("Comparer les zones de Sfax et Béja", "fr"),
        ("Show me plots in Sfax", "en"),
        ("Terrains disponibles à Kairouan ?", "fr"),
        ("3andi projet fi Beja", "arabizi"),
        ("L-KAI-001", None),
        ("👍", None),
    ],
)
def test_ids_do_not_count_as_arabizi_and_unclear_text_gets_no_label(
    text: str, expected: str | None
) -> None:
    assert detect_language(text) == expected


def test_agent_adds_the_language_hint_to_the_system_prompt(ctx: ToolContext) -> None:
    question = "Compare the industrial zones in Kairouan and Sidi Bouzid."
    llm = ScriptedLLM([scripted_turn("Here is the comparison.")])

    Agent(llm, ctx).respond([], question)

    assert llm.systems[0].startswith(SYSTEM_PROMPT)
    assert reply_language_instruction(question) in llm.systems[0]
    assert "Reply in English" in llm.systems[0]


def test_no_hint_when_the_language_is_unclear(ctx: ToolContext) -> None:
    llm = ScriptedLLM([scripted_turn("?")])

    Agent(llm, ctx).respond([], "L-KAI-001")

    assert llm.systems == [SYSTEM_PROMPT]
