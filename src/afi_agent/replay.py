"""Offline demo mode: answer recorded questions without any model provider.

Replays docs/demo/conversations.json (written by scripts/capture_demo.py). The tools still run
for real, so drafts, the Confirm button and tracking numbers behave as in a live demo. Use it
when the venue network or a free API fails: AFI_PROVIDER=replay.
"""

import json
from pathlib import Path
from typing import Any

from afi_agent.llm import LLMTurn, ToolCall, scripted_turn
from afi_agent.store import normalize

OFFLINE_REPLY = (
    "Mode hors ligne : je ne peux répondre qu'aux questions de démonstration enregistrées. "
    "Essayez l'un des exemples proposés."
)


class ReplayLLM:
    def __init__(self, recorded: dict[str, Any]) -> None:
        self.last_model = f"replay of {recorded.get('model', 'recorded answers')} (offline)"
        self._turns: dict[str, dict[str, Any]] = {}
        for scenario in recorded["scenarios"]:
            for turn in scenario["turns"]:
                self._turns[normalize(turn["user"])] = turn

    @classmethod
    def from_file(cls, path: Path) -> "ReplayLLM":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def questions(self) -> list[str]:
        return [turn["user"] for turn in self._turns.values()]

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMTurn:
        if not tools:  # a rewrite request: recorded replies are already final
            return scripted_turn(str(messages[-1]["content"]))
        question_index = max(
            i
            for i, m in enumerate(messages)
            if m["role"] == "user" and isinstance(m["content"], str)
        )
        recorded = self._turns.get(normalize(messages[question_index]["content"]))
        if recorded is None:
            return scripted_turn(OFFLINE_REPLY)
        steps_taken = sum(m["role"] == "assistant" for m in messages[question_index:])
        calls = recorded["tool_calls"]
        if steps_taken == 0 and calls:
            return scripted_turn(
                tool_calls=[
                    ToolCall(f"replay-{i}", call["name"], dict(call["input"]))
                    for i, call in enumerate(calls)
                ]
            )
        return scripted_turn(recorded["reply"])
