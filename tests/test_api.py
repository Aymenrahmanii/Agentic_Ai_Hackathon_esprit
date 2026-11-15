from fastapi.testclient import TestClient

from afi_agent.api import create_app
from afi_agent.llm import ScriptedLLM, ToolCall, scripted_turn

PREFILL = ToolCall(
    "t1",
    "prefill_request",
    {"lot_id": "L-KAI-001", "applicant_name": "Test Investor", "activity": "textile"},
)


def test_health_needs_no_llm() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_keeps_the_session_across_turns() -> None:
    llm = ScriptedLLM([scripted_turn("Bonjour."), scripted_turn("Encore bonjour.")])
    client = TestClient(create_app(llm=llm))

    first = client.post("/chat", json={"message": "Salut"}).json()
    second = client.post("/chat", json={"message": "Re", "session_id": first["session_id"]}).json()

    assert first["reply"] == "Bonjour."
    assert first["pending_draft"] is None
    assert second["session_id"] == first["session_id"]
    assert second["reply"] == "Encore bonjour."


def test_request_is_submitted_only_by_the_confirm_endpoint() -> None:
    llm = ScriptedLLM(
        [scripted_turn(tool_calls=[PREFILL]), scripted_turn("Vérifiez le brouillon.")]
    )
    client = TestClient(create_app(llm=llm))

    chat = client.post("/chat", json={"message": "Réservez le lot L-KAI-001"}).json()
    draft = chat["pending_draft"]
    assert draft["status"] == "awaiting_confirmation"
    assert chat["tool_calls"][0]["name"] == "prefill_request"

    confirmed = client.post(f"/requests/{draft['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["tracking_number"] == "DEMO-0001"

    assert client.post(f"/requests/{draft['id']}/confirm").status_code == 409


def test_confirm_unknown_draft_is_404() -> None:
    client = TestClient(create_app(llm=ScriptedLLM([])))
    assert client.post("/requests/DRAFT-9999/confirm").status_code == 404


def test_llm_failure_becomes_a_gateway_error() -> None:
    client = TestClient(create_app(llm=ScriptedLLM([])))
    assert client.post("/chat", json={"message": "Salut"}).status_code == 502


def test_empty_message_is_rejected() -> None:
    client = TestClient(create_app(llm=ScriptedLLM([])))
    assert client.post("/chat", json={"message": ""}).status_code == 422
