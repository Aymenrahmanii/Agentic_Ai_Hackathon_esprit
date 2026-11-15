from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from afi_agent.api import create_app
from afi_agent.config import PROJECT_ROOT, load_settings
from afi_agent.llm import build_llm
from afi_agent.replay import OFFLINE_REPLY, ReplayLLM

RECORDED = PROJECT_ROOT / "docs" / "demo" / "conversations.json"


@pytest.fixture
def offline_settings(monkeypatch: pytest.MonkeyPatch):
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "AFI_FALLBACK_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AFI_PROVIDER", "replay")
    return load_settings()


def test_replay_mode_needs_no_key_and_no_fallback(offline_settings) -> None:
    assert offline_settings.fallback_provider is None
    assert isinstance(build_llm(offline_settings), ReplayLLM)


def test_recorded_booking_runs_offline_with_real_tools_and_confirm(offline_settings) -> None:
    replay = ReplayLLM.from_file(RECORDED)
    search, booking = replay.questions[0], replay.questions[1]
    client = TestClient(create_app(settings=offline_settings))

    first = client.post("/chat", json={"message": search}).json()
    second = client.post(
        "/chat", json={"message": booking, "session_id": first["session_id"]}
    ).json()
    confirmed = client.post(f"/requests/{second['pending_draft']['id']}/confirm")

    assert [t["name"] for t in first["tool_calls"]] == ["search_lots"]
    assert first["tool_calls"][0]["output"]["count"] == 2  # the tool really ran
    assert "offline" in first["model"]
    assert second["pending_draft"]["lot_id"] == "L-KAI-001"
    assert confirmed.json()["tracking_number"] == "DEMO-0001"


def test_every_recorded_question_replays_with_its_tools(offline_settings) -> None:
    client = TestClient(create_app(settings=offline_settings))
    replay = ReplayLLM.from_file(RECORDED)

    for question in replay.questions:
        response = client.post("/chat", json={"message": question})
        assert response.status_code == 200, question
        assert response.json()["reply"] != OFFLINE_REPLY


def test_unrecorded_questions_get_the_offline_notice(offline_settings) -> None:
    client = TestClient(create_app(settings=offline_settings))

    reply = client.post("/chat", json={"message": "Quel temps fera-t-il demain ?"}).json()

    assert reply["reply"] == OFFLINE_REPLY
    assert reply["tool_calls"] == []


def test_status_reports_offline_mode(offline_settings) -> None:
    client = TestClient(create_app(settings=replace(offline_settings)))
    assert client.get("/status").json()["model"] == "replay (offline)"
