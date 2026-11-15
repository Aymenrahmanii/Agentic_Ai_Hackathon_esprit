from pathlib import Path

from afi_agent.agent import Agent, AgentReply
from afi_agent.evaluation import (
    CaseResult,
    GoldenCase,
    args_match,
    load_cases,
    run_cases,
    summarize,
)
from afi_agent.llm import ScriptedLLM, ToolCall, scripted_turn
from afi_agent.tools import TOOLS, ToolContext

GOLDEN = Path(__file__).resolve().parents[1] / "evals" / "golden.jsonl"


def test_golden_set_is_valid_and_targets_real_tools() -> None:
    cases = load_cases(GOLDEN)
    tool_names = {tool.name for tool in TOOLS}
    assert len(cases) >= 10
    assert len({case.id for case in cases}) == len(cases)
    assert {case.expected_tool for case in cases} <= tool_names


def test_args_match_is_loose_on_strings_and_allows_extras() -> None:
    assert args_match({"governorate": "Béja"}, {"governorate": "beja", "limit": 5})
    assert args_match({"min_area_m2": 5000}, {"min_area_m2": 5000.0})
    assert args_match({"places": ["Kairouan"]}, {"places": ["Sidi Bouzid", "kairouan"]})
    assert not args_match({"governorate": "Béja"}, {"governorate": "Sfax"})
    assert not args_match({"governorate": "Béja"}, {})


def test_args_match_uses_the_canonicalizer() -> None:
    def canon(key: str, value: object) -> object:
        return "Kairouan" if value == "القيروان" else value

    assert args_match({"governorate": "Kairouan"}, {"governorate": "القيروان"}, canon)


def test_run_cases_scores_tool_choice_and_arguments(ctx: ToolContext) -> None:
    cases = [
        GoldenCase(
            id="hit",
            lang="fr",
            question="Lots à Sfax ?",
            expected_tool="search_lots",
            expected_args={"governorate": "Sfax"},
        ),
        GoldenCase(
            id="wrong-args",
            lang="fr",
            question="Lots à Béja ?",
            expected_tool="search_lots",
            expected_args={"governorate": "Béja"},
        ),
        GoldenCase(
            id="no-tool", lang="en", question="Human please", expected_tool="escalate_to_human"
        ),
    ]
    search_sfax = scripted_turn(tool_calls=[ToolCall("t", "search_lots", {"governorate": "Sfax"})])
    scripts = iter(
        [
            [search_sfax, scripted_turn("ok")],
            [search_sfax, scripted_turn("ok")],
            [scripted_turn("I cannot do that.")],
        ]
    )

    def ask(question: str) -> AgentReply:
        return Agent(ScriptedLLM(next(scripts)), ctx).respond([], question)

    results = run_cases(cases, ask)

    assert [(r.tool_ok, r.args_ok) for r in results] == [
        (True, True),
        (True, False),
        (False, False),
    ]
    summary = summarize(results)
    assert summary["passed"] == 1
    assert summary["accuracy_by_lang"] == {"fr": 0.5, "en": 0.0}


def test_run_cases_records_failures_instead_of_stopping() -> None:
    cases = [GoldenCase(id="boom", lang="fr", question="?", expected_tool="search_lots")]

    def ask(question: str) -> AgentReply:
        raise RuntimeError("network down")

    results = run_cases(cases, ask)

    assert results == [CaseResult("boom", "fr", False, False, [], 0.0, error="network down")]
    assert summarize(results)["errors"] == 1
