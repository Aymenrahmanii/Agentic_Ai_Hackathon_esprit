"""Record real conversations through the API for the README animations.

Usage: uv run --env-file .env python scripts/capture_demo.py
Writes docs/demo/conversations.json. Every turn is a real model call.
"""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from afi_agent.api import create_app
from afi_agent.config import load_settings

OUT = Path(__file__).resolve().parents[1] / "docs" / "demo" / "conversations.json"

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "derja-booking",
        "title": "Tunisian Derja: find a lot, book it, confirm",
        "turns": [
            "نحب نحل معمل نسيج في القيروان، شنوة الأراضي الموجودة؟",
            "نحب نحجز L-KAI-001، إسمي سامي والنشاط متاعي نسيج",
        ],
        "confirm": True,
    },
    {
        "id": "multilingual",
        "title": "Same agent, three languages",
        "turns": [
            "n7eb nechri ardh sina3iya fi sfax, chnowa mawjoud?",
            "Quels documents faut-il pour réserver un lot ?",
            "Is there any land for a food processing plant under 200,000 dinars?",
        ],
        "separate_sessions": True,
    },
    {
        "id": "guardrails",
        "title": "Guardrails: missing details, out of scope, human hand-over",
        "turns": [
            "Réservez-moi le lot L-KAI-002.",
            "What's the weather going to be like in Tunis tomorrow?",
            "I want to talk to a human agent.",
        ],
        "separate_sessions": True,
    },
]


def run_scenario(client: TestClient, scenario: dict[str, Any]) -> dict[str, Any]:
    session_id: str | None = None
    turns = []
    for message in scenario["turns"]:
        if scenario.get("separate_sessions"):
            session_id = None
        body = client.post("/chat", json={"message": message, "session_id": session_id})
        body.raise_for_status()
        data = body.json()
        session_id = data["session_id"]
        turns.append(
            {
                "user": message,
                "tool_calls": [
                    {"name": t["name"], "input": t["input"], "is_error": t["is_error"]}
                    for t in data["tool_calls"]
                ],
                "reply": data["reply"],
                "latency_ms": round(data["latency_ms"]),
                "pending_draft": (data["pending_draft"] or {}).get("id"),
            }
        )
        draft = data["pending_draft"]
        if scenario.get("confirm") and draft:
            confirmed = client.post(f"/requests/{draft['id']}/confirm").json()
            turns[-1]["confirmed"] = confirmed["tracking_number"]
    return {"id": scenario["id"], "title": scenario["title"], "turns": turns}


def main() -> None:
    settings = load_settings()
    client = TestClient(create_app())
    recorded = {
        "model": settings.model,
        "scenarios": [run_scenario(client, scenario) for scenario in SCENARIOS],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(recorded, ensure_ascii=False, indent=2), encoding="utf-8")
    for scenario in recorded["scenarios"]:
        print(f"== {scenario['title']}")
        for turn in scenario["turns"]:
            tools = ", ".join(t["name"] for t in turn["tool_calls"]) or "no tool"
            print(f"  [{tools}] {turn['latency_ms']} ms  {turn['reply'][:110]}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
