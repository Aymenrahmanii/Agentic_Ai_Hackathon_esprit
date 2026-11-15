"""Scoring for the golden set.

`passed` asks whether the agent picked the right tool with the right arguments. `style_ok` asks
whether the reply is speakable: right script, right language, no markdown, references given."""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from afi_agent import style_checks
from afi_agent.agent import AgentReply
from afi_agent.store import normalize

# Maps (argument name, value) to a canonical value before comparing, e.g. "القيروان" -> "Kairouan".
Canonicalize = Callable[[str, Any], Any]


class GoldenCase(BaseModel):
    id: str
    lang: str
    question: str
    # None: the agent should answer without the tools below, e.g. ask for missing details.
    expected_tool: str | None
    expected_args: dict[str, Any] = {}
    forbidden_tools: list[str] = []
    # Earlier user messages, sent through the agent first. Only the last turn is scored.
    history: list[str] = []


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    lang: str
    tool_ok: bool
    args_ok: bool
    called: list[str]
    latency_ms: float
    error: str | None = None
    # Forbidden tools the model tried that the code refused.
    blocked: list[str] = field(default_factory=list)
    script_ok: bool = False
    language_ok: bool = False
    # Checked on the model's raw text, before the speech cleanup, to track prompt compliance.
    markdown_free: bool = False
    references_ok: bool = False
    # Kept for human review: none of the checks judge the quality of the wording.
    reply: str = ""

    @property
    def passed(self) -> bool:
        return self.tool_ok and self.args_ok

    @property
    def style_ok(self) -> bool:
        return self.script_ok and self.language_ok and self.references_ok


def load_cases(path: Path) -> list[GoldenCase]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [GoldenCase.model_validate(json.loads(line)) for line in lines if line.strip()]


def _same(expected: Any, actual: Any) -> bool:
    if isinstance(expected, str) and isinstance(actual, str):
        return normalize(expected) == normalize(actual)
    if isinstance(expected, list) and isinstance(actual, list):
        return all(any(_same(e, a) for a in actual) for e in expected)
    return expected == actual


def args_match(
    expected: dict[str, Any], actual: dict[str, Any], canonicalize: Canonicalize | None = None
) -> bool:
    """True when every expected argument is present in `actual`; extra arguments are allowed."""
    canon = canonicalize or (lambda _key, value: value)
    return all(
        key in actual and _same(canon(key, value), canon(key, actual[key]))
        for key, value in expected.items()
    )


def score_case(
    case: GoldenCase, reply: AgentReply, canonicalize: Canonicalize | None = None
) -> CaseResult:
    forbidden = set(case.forbidden_tools)
    # A forbidden call the code rejected (e.g. a booking without the user's own details) did
    # nothing, so it does not fail the case; it is still counted under `blocked`.
    succeeded = {r.name for r in reply.tool_records if not r.is_error}
    blocked = sorted({r.name for r in reply.tool_records if r.is_error and r.name in forbidden})
    no_forbidden = not succeeded & forbidden
    if case.expected_tool is None:
        tool_ok, args_ok = no_forbidden, True
    else:
        calls = [r for r in reply.tool_records if r.name == case.expected_tool]
        tool_ok = bool(calls) and no_forbidden
        args_ok = any(args_match(case.expected_args, r.input, canonicalize) for r in calls)
    return CaseResult(
        case_id=case.id,
        lang=case.lang,
        tool_ok=tool_ok,
        args_ok=args_ok,
        called=[r.name for r in reply.tool_records],
        latency_ms=reply.latency_ms,
        blocked=blocked,
        script_ok=style_checks.script_ok(case.lang, reply.text),
        language_ok=style_checks.language_ok(case.lang, reply.text),
        markdown_free=not style_checks.has_markdown(reply.raw_text),
        references_ok=style_checks.references_ok(
            reply.text, (r.output for r in reply.tool_records if not r.is_error)
        ),
        reply=reply.text,
    )


def run_cases(
    cases: list[GoldenCase],
    ask: Callable[[GoldenCase], AgentReply],
    canonicalize: Canonicalize | None = None,
) -> list[CaseResult]:
    """`ask` plays a case's history and question in a fresh session and returns the reply to
    the question."""
    results = []
    for case in cases:
        try:
            results.append(score_case(case, ask(case), canonicalize))
        except Exception as exc:  # one failing case must not lose the rest of a paid run
            results.append(
                CaseResult(
                    case_id=case.id,
                    lang=case.lang,
                    tool_ok=False,
                    args_ok=False,
                    called=[],
                    latency_ms=0.0,
                    error=str(exc),
                )
            )
    return results


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    by_lang: dict[str, list[CaseResult]] = {}
    for result in results:
        by_lang.setdefault(result.lang, []).append(result)
    latencies = [r.latency_ms for r in results if r.error is None]
    answered = [r for r in results if r.error is None]

    def share(attribute: str) -> float | None:
        return sum(getattr(r, attribute) for r in answered) / len(answered) if answered else None

    return {
        "cases": len(results),
        "passed": sum(r.passed for r in results),
        "accuracy": sum(r.passed for r in results) / len(results) if results else 0.0,
        "accuracy_by_lang": {
            lang: sum(r.passed for r in group) / len(group) for lang, group in by_lang.items()
        },
        "style_ok": share("style_ok"),
        "script_ok": share("script_ok"),
        "language_ok": share("language_ok"),
        "references_ok": share("references_ok"),
        "markdown_free_raw": share("markdown_free"),
        "latency_ms_p50": _percentile(latencies, 0.5) if latencies else None,
        "latency_ms_p95": _percentile(latencies, 0.95) if latencies else None,
        "errors": sum(r.error is not None for r in results),
        "blocked_attempts": sum(len(r.blocked) for r in results),
    }


def results_to_json(results: list[CaseResult]) -> str:
    cases = [asdict(r) | {"passed": r.passed, "style_ok": r.style_ok} for r in results]
    payload = {"summary": summarize(results), "cases": cases}
    return json.dumps(payload, ensure_ascii=False, indent=2)
