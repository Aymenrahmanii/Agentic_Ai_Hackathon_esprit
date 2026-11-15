import json

import pytest

from afi_agent.agent import Agent
from afi_agent.llm import LLMError, ScriptedLLM, ToolCall, scripted_turn
from afi_agent.tools import ToolContext


def test_tool_call_then_answer(ctx: ToolContext) -> None:
    llm = ScriptedLLM(
        [
            scripted_turn(tool_calls=[ToolCall("t1", "search_lots", {"governorate": "القيروان"})]),
            scripted_turn("لقيت زوز أراضي في القيروان."),
        ]
    )
    messages: list = []

    reply = Agent(llm, ctx).respond(messages, "شنوة الأراضي الموجودة في القيروان؟")

    assert reply.text == "لقيت زوز أراضي في القيروان."
    assert reply.stop_reason == "end_turn"
    assert [r.name for r in reply.tool_records] == ["search_lots"]
    assert reply.tool_records[0].output["count"] == 2
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    tool_result = messages[2]["content"][0]
    assert tool_result["tool_use_id"] == "t1"
    assert json.loads(tool_result["content"])["count"] == 2


def test_reply_is_cleaned_for_speech_and_raw_text_is_kept(ctx: ToolContext) -> None:
    raw = "Voici :\n- Lot **L‑KAI‑001**"
    reply = Agent(ScriptedLLM([scripted_turn(raw)]), ctx).respond([], "Des lots ?")

    assert reply.text == "Voici : Lot L-KAI-001"
    assert reply.raw_text == raw


def test_parallel_tool_results_go_back_in_one_message(ctx: ToolContext) -> None:
    llm = ScriptedLLM(
        [
            scripted_turn(
                tool_calls=[
                    ToolCall("t1", "search_lots", {"governorate": "Sfax"}),
                    ToolCall("t2", "get_procedure", {"procedure_id": "reservation_lot"}),
                ]
            ),
            scripted_turn("Voici les lots et la procédure."),
        ]
    )
    messages: list = []

    Agent(llm, ctx).respond(messages, "Lots à Sfax et procédure ?")

    assert [block["tool_use_id"] for block in messages[2]["content"]] == ["t1", "t2"]


def test_tool_errors_are_returned_to_the_model(ctx: ToolContext) -> None:
    llm = ScriptedLLM(
        [
            scripted_turn(tool_calls=[ToolCall("t1", "search_lots", {"governorate": "Atlantis"})]),
            scripted_turn("Je ne connais pas ce gouvernorat."),
        ]
    )
    messages: list = []

    reply = Agent(llm, ctx).respond(messages, "Des lots à Atlantis ?")

    assert reply.tool_records[0].is_error
    assert messages[2]["content"][0]["is_error"] is True


def test_prefill_surfaces_a_pending_draft(ctx: ToolContext) -> None:
    call = ToolCall(
        "t1",
        "prefill_request",
        {"lot_id": "L-KAI-001", "applicant_name": "Test Investor", "activity": "textile"},
    )
    llm = ScriptedLLM([scripted_turn(tool_calls=[call]), scripted_turn("Vérifiez et confirmez.")])

    reply = Agent(llm, ctx).respond([], "Réservez le lot L-KAI-001")

    assert reply.pending_draft_id == "DRAFT-0001"
    assert ctx.afizi.get_draft("DRAFT-0001").status == "awaiting_confirmation"


def test_stops_after_max_steps(ctx: ToolContext) -> None:
    looping = scripted_turn(tool_calls=[ToolCall("t", "search_lots", {})])
    llm = ScriptedLLM([looping, looping, looping])

    reply = Agent(llm, ctx, max_steps=2).respond([], "boucle")

    assert llm.call_count == 2
    assert reply.stop_reason == "max_steps"
    assert reply.text


def test_refusal_leaves_the_transcript_untouched(ctx: ToolContext) -> None:
    llm = ScriptedLLM([scripted_turn(stop_reason="refusal")])
    messages: list = []

    reply = Agent(llm, ctx).respond(messages, "...")

    assert reply.stop_reason == "refusal"
    assert messages == []


def test_llm_failure_rolls_back_the_turn(ctx: ToolContext) -> None:
    messages = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "ok"}]

    with pytest.raises(LLMError):
        Agent(ScriptedLLM([]), ctx).respond(messages, "new question")

    assert len(messages) == 2
