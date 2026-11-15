from fastapi.testclient import TestClient

from afi_agent.api import create_app
from afi_agent.llm import ScriptedLLM, ToolCall, scripted_turn

PREFILL = ToolCall(
    "t1",
    "prefill_request",
    {
        "lot_id": "L-KAI-001",
        "applicant_name": "Test Investor",
        "applicant_name_quote": "Test Investor",
        "activity": "textile",
        "activity_quote": "textile",
    },
)


def test_interface_is_served_and_always_revalidated() -> None:
    client = TestClient(create_app(llm=ScriptedLLM([])))

    page = client.get("/")
    script = client.get("/static/app.js")

    assert page.status_code == 200 and "Assistant foncier" in page.text
    assert script.status_code == 200
    assert page.headers["cache-control"] == script.headers["cache-control"] == "no-cache"


def test_map_lists_every_zone_with_its_lots() -> None:
    client = TestClient(create_app(llm=ScriptedLLM([])))

    zones = client.get("/map").json()["zones"]

    assert {z["id"] for z in zones} == {"ZI-KAI-01", "ZI-SFX-01", "ZI-BEJ-01", "ZI-SBZ-01"}
    kairouan = next(z for z in zones if z["id"] == "ZI-KAI-01")
    assert kairouan["available"] == 2 and len(kairouan["lots"]) == 3


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

    message = "Réservez le lot L-KAI-001 pour Test Investor, activité textile"
    chat = client.post("/chat", json={"message": message}).json()
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
