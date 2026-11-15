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
        {
            "lot_id": "L-KAI-001",
            "applicant_name": "Sami",
            "applicant_name_quote": "je suis Sami",
            "activity": "textile",
            "activity_quote": "textile",
        },
    )
    llm = ScriptedLLM([scripted_turn(tool_calls=[call]), scripted_turn("Vérifiez et confirmez.")])

    reply = Agent(llm, ctx).respond([], "Réservez le lot L-KAI-001, je suis Sami, textile")

    assert reply.pending_draft_id == "DRAFT-0001"
    assert ctx.afizi.get_draft("DRAFT-0001").status == "awaiting_confirmation"


def test_booking_details_from_an_earlier_turn_count(ctx: ToolContext) -> None:
    call = ToolCall(
        "t1",
        "prefill_request",
        {
            "lot_id": "L-KAI-001",
            "applicant_name": "Sami",
            "applicant_name_quote": "Sami",
            "activity": "textile",
            "activity_quote": "textile",
        },
    )
    history = [
        {"role": "user", "content": "Je m'appelle Sami."},
        {"role": "assistant", "content": "Quelle est votre activité ?"},
    ]
    llm = ScriptedLLM([scripted_turn(tool_calls=[call]), scripted_turn("Confirmez.")])

    reply = Agent(llm, ctx).respond(history, "textile, lot L-KAI-001")

    assert not reply.tool_records[0].is_error


def test_mixed_script_reply_is_rewritten_once(ctx: ToolContext) -> None:
    llm = ScriptedLLM(
        [
            scripted_turn("لازمك تطلع على أavis de vente"),
            scripted_turn("لازمك تطلع على إعلان البيع"),
        ]
    )
    messages: list = []

    reply = Agent(llm, ctx).respond(messages, "كيفاش نشارك في البتة؟")

    assert reply.text == "لازمك تطلع على إعلان البيع"
    assert llm.systems[1].startswith("Rewrite the text")
    assert messages[-1] == {"role": "assistant", "content": "لازمك تطلع على إعلان البيع"}


def test_spelled_out_draft_id_is_rewritten_with_the_exact_id(ctx: ToolContext) -> None:
    call = ToolCall(
        "t1",
        "prefill_request",
        {
            "lot_id": "L-KAI-001",
            "applicant_name": "سامي",
            "applicant_name_quote": "سامي",
            "activity": "textile",
            "activity_quote": "نسيج",
        },
    )
    llm = ScriptedLLM(
        [
            scripted_turn(tool_calls=[call]),
            scripted_turn("حضرتلك مطلب بالمرجع درافت صفر صفر واحد"),
            scripted_turn("حضرتلك مطلب بالمرجع DRAFT-0001"),
        ]
    )

    reply = Agent(llm, ctx).respond([], "نحجز L-KAI-001، إسمي سامي، نسيج")

    assert reply.text == "حضرتلك مطلب بالمرجع DRAFT-0001"
    assert "DRAFT-0001" in llm.systems[2]


def test_spelled_out_lot_ids_are_rewritten_exactly(ctx: ToolContext) -> None:
    search = scripted_turn(tool_calls=[ToolCall("t1", "search_lots", {"governorate": "Kairouan"})])
    llm = ScriptedLLM(
        [
            search,
            scripted_turn("لقيتلك القطعة ال كي صفر صفر واحد والقطعة ال كي صفر صفر اثنين"),
            scripted_turn("لقيتلك القطعة L-KAI-001 والقطعة L-KAI-002"),
        ]
    )

    reply = Agent(llm, ctx).respond([], "شنوة الأراضي في القيروان؟")

    assert reply.text == "لقيتلك القطعة L-KAI-001 والقطعة L-KAI-002"
    assert "L-KAI-001, L-KAI-002" in llm.systems[2]


def test_rewrite_that_still_lacks_the_id_is_discarded(ctx: ToolContext) -> None:
    call = ToolCall("t1", "escalate_to_human", {"reason": "demande"})
    llm = ScriptedLLM(
        [
            scripted_turn(tool_calls=[call]),
            scripted_turn("Un agent va vous contacter."),
            scripted_turn("Un conseiller va vous rappeler."),
        ]
    )

    reply = Agent(llm, ctx).respond([], "Je veux parler à quelqu'un")

    assert reply.text == "Un agent va vous contacter."


def test_reply_inventing_lot_ids_is_retried_with_a_lookup(ctx: ToolContext) -> None:
    invented = scripted_turn("عنا القطعة L-KAI-001 بخمسة آلاف متر مربع.")
    search = scripted_turn(tool_calls=[ToolCall("t1", "search_lots", {"governorate": "Kairouan"})])
    grounded = scripted_turn("عنا زوز: L-KAI-001 و L-KAI-002.")
    llm = ScriptedLLM([invented, search, grounded])
    messages: list = []

    reply = Agent(llm, ctx).respond(messages, "شنوة الأراضي في القيروان؟")

    assert reply.text == "عنا زوز: L-KAI-001 و L-KAI-002."
    assert [r.name for r in reply.tool_records] == ["search_lots"]
    assert "never answer from memory" in llm.systems[1]
    # The invented answer is not left in the transcript.
    assert all("بخمسة آلاف" not in str(m["content"]) for m in messages)


def test_spelled_out_prices_without_any_lookup_are_retried(ctx: ToolContext) -> None:
    invented = scripted_turn("عنا أرض برمز أل كا صفر واحد بسعر خمسة وثمانين ألف دينار.")
    search = scripted_turn(tool_calls=[ToolCall("t1", "search_lots", {"governorate": "Kairouan"})])
    grounded = scripted_turn("عنا L-KAI-001 و L-KAI-002 بتسعين ألف دينار للأولى.")
    llm = ScriptedLLM([invented, search, grounded])

    reply = Agent(llm, ctx).respond([], "شنوة الأراضي في القيروان؟")

    assert [r.name for r in reply.tool_records] == ["search_lots"]
    assert "خمسة وثمانين" not in reply.text


def test_still_invented_after_the_retry_shows_a_safe_message(ctx: ToolContext) -> None:
    invented = scripted_turn("Le lot coûte 85 000 dinars.")
    messages: list = []
    llm = ScriptedLLM([invented, invented])

    reply = Agent(llm, ctx).respond(messages, "Combien coûte un terrain à Sfax ?")

    assert reply.stop_reason == "unverified"
    assert "vérifier" in reply.text and "85" not in reply.text
    assert "85" not in str(messages)


def test_questions_about_budget_are_not_flagged(ctx: ToolContext) -> None:
    llm = ScriptedLLM([scripted_turn("Quel est votre budget en dinars ?")])

    reply = Agent(llm, ctx).respond([], "Je cherche un terrain")

    assert llm.call_count == 1
    assert reply.text == "Quel est votre budget en dinars ?"


def test_ids_the_user_typed_or_an_earlier_tool_returned_are_not_flagged(ctx: ToolContext) -> None:
    llm = ScriptedLLM([scripted_turn("Le lot L-KAI-002 est-il celui que vous voulez ?")])

    reply = Agent(llm, ctx).respond([], "Je pense au lot L-KAI-002")

    assert llm.call_count == 1
    assert reply.text.startswith("Le lot L-KAI-002")


def test_failed_rewrite_keeps_the_original(ctx: ToolContext) -> None:
    llm = ScriptedLLM([scripted_turn("على أavis de vente")])  # no turn left for the rewrite

    reply = Agent(llm, ctx).respond([], "?")

    assert reply.text == "على أavis de vente"


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
