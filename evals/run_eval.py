"""Run the golden set against the real model. Every case spends API quota (or money).

Usage: uv run --env-file .env python evals/run_eval.py [--limit N]
"""

import argparse
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from afi_agent.afizi_mock import AfiziMock
from afi_agent.agent import Agent, AgentReply
from afi_agent.config import load_settings
from afi_agent.evaluation import load_cases, results_to_json, run_cases, summarize
from afi_agent.llm import build_llm
from afi_agent.store import InMemoryStore
from afi_agent.tools import ToolContext

EVALS_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=EVALS_DIR / "golden.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases.")
    parser.add_argument("--model", default=None, help="Override AFI_MODEL for this run.")
    args = parser.parse_args()

    settings = load_settings()
    if args.model:
        settings = replace(settings, model=args.model)
    llm = build_llm(settings)
    reference_store = InMemoryStore.from_file(settings.seed_path)

    def ask(question: str) -> AgentReply:
        # Fresh store and back office per case so one case cannot affect the next.
        store = InMemoryStore.from_file(settings.seed_path)
        ctx = ToolContext(store=store, afizi=AfiziMock(store))
        return Agent(llm, ctx, max_steps=settings.max_agent_steps).respond([], question)

    def canonicalize(key: str, value: Any) -> Any:
        if key == "governorate" and isinstance(value, str):
            return reference_store.resolve_governorate(value) or value
        if key == "places" and isinstance(value, list):
            return [reference_store.resolve_governorate(v) or v for v in value]
        return value

    cases = load_cases(args.golden)[: args.limit]
    results = run_cases(cases, ask, canonicalize)

    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        detail = r.error or ", ".join(r.called) or "no tool called"
        style_flags = [
            name
            for name, ok in (
                ("script", r.script_ok),
                ("language", r.language_ok),
                ("references", r.references_ok),
                ("markdown", r.markdown_free),
            )
            if not ok
        ]
        style = "style ok" if not style_flags else "style: " + ", ".join(style_flags)
        if r.error:
            style = ""
        print(f"{mark}  {r.case_id:<24} {r.latency_ms:>7.0f} ms  {detail:<20} {style}")
    summary = summarize(results)
    print(f"\n{summary['passed']}/{summary['cases']} passed  |  model={settings.model}")
    print(f"by language: {summary['accuracy_by_lang']}")
    print(
        f"style ok: {summary['style_ok']}  (script {summary['script_ok']}, "
        f"language {summary['language_ok']}, references {summary['references_ok']}); "
        f"raw replies without markdown: {summary['markdown_free_raw']}"
    )
    print(f"latency p50={summary['latency_ms_p50']} ms  p95={summary['latency_ms_p95']} ms")

    out_dir = EVALS_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    model_slug = settings.model.replace("/", "_")
    out_path = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{model_slug}.json"
    out_path.write_text(results_to_json(results), encoding="utf-8")
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
