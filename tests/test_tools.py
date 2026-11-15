from dataclasses import replace

from afi_agent.tools import TOOLS, ToolContext, execute_tool, tool_schemas


def test_schemas_cover_every_tool_and_list_procedure_ids(ctx: ToolContext) -> None:
    schemas = {s["name"]: s for s in tool_schemas(ctx.store)}
    assert set(schemas) == {tool.name for tool in TOOLS}
    assert all(s["input_schema"]["type"] == "object" for s in schemas.values())
    assert "reservation_lot" in schemas["get_procedure"]["description"]


def test_search_lots_accepts_arabic_governorate(ctx: ToolContext) -> None:
    outcome = execute_tool("search_lots", {"governorate": "القيروان"}, ctx)
    assert not outcome.is_error
    assert outcome.output["count"] == 2
    assert outcome.output["lots"][0]["total_price_tnd"] == 90_000


def test_search_lots_sector_is_matched_loosely_and_filters(ctx: ToolContext) -> None:
    outcome = execute_tool("search_lots", {"sector": "Plasturgie"}, ctx)
    assert not outcome.is_error
    assert [lot["id"] for lot in outcome.output["lots"]] == ["L-SFX-001", "L-SFX-002"]


def test_search_lots_unknown_sector_lists_the_known_ones(ctx: ToolContext) -> None:
    outcome = execute_tool("search_lots", {"sector": "food processing"}, ctx)
    assert outcome.is_error
    assert "agroalimentaire" in outcome.output["error"]


def test_search_lots_description_lists_the_sectors(ctx: ToolContext) -> None:
    schemas = {s["name"]: s for s in tool_schemas(ctx.store)}
    assert "plasturgie" in schemas["search_lots"]["description"]


def test_search_lots_unknown_governorate_lists_known_ones(ctx: ToolContext) -> None:
    outcome = execute_tool("search_lots", {"governorate": "Atlantis"}, ctx)
    assert outcome.is_error
    assert "Kairouan" in outcome.output["error"]


def test_compare_zones_mixes_zone_ids_and_governorates(ctx: ToolContext) -> None:
    outcome = execute_tool("compare_zones", {"places": ["zi-kai-01", "Sidi Bouzid"]}, ctx)
    assert not outcome.is_error
    zones = {z["id"]: z for z in outcome.output["zones"]}
    assert set(zones) == {"ZI-KAI-01", "ZI-SBZ-01"}
    assert zones["ZI-KAI-01"]["available_lots"] == 2
    assert zones["ZI-SBZ-01"]["price_tnd_per_m2_range"] == [25, 25]


def test_get_procedure(ctx: ToolContext) -> None:
    outcome = execute_tool("get_procedure", {"procedure_id": "reservation_lot"}, ctx)
    assert not outcome.is_error
    assert outcome.output["documents"]

    unknown = execute_tool("get_procedure", {"procedure_id": "nope"}, ctx)
    assert unknown.is_error
    assert "reservation_lot" in unknown.output["error"]


BOOKING_MESSAGE = "Je m'appelle Test Investor et mon activité est le textile."


def booking(lot_id: str, **overrides: str) -> dict[str, str]:
    return {
        "lot_id": lot_id,
        "applicant_name": "Test Investor",
        "applicant_name_quote": "Test Investor",
        "activity": "textile",
        "activity_quote": "mon activité est le textile",
        **overrides,
    }


def test_prefill_creates_a_draft_but_submits_nothing(ctx: ToolContext) -> None:
    ctx = replace(ctx, user_messages=(BOOKING_MESSAGE,))
    outcome = execute_tool("prefill_request", booking("l-kai-001"), ctx)
    assert not outcome.is_error
    assert outcome.output["draft"]["status"] == "awaiting_confirmation"
    assert outcome.output["draft"]["tracking_number"] is None
    assert ctx.store.get_lot("L-KAI-001").status == "available"


def test_prefill_rejects_details_the_user_never_gave(ctx: ToolContext) -> None:
    ctx = replace(ctx, user_messages=("Réservez-moi le lot L-KAI-002, je m'appelle Karim.",))
    invented = booking(
        "L-KAI-002",
        applicant_name="Karim",
        applicant_name_quote="je m'appelle Karim",
        activity="industrie générale",
        activity_quote="industrie générale",
    )

    outcome = execute_tool("prefill_request", invented, ctx)

    assert outcome.is_error
    assert "ask the user for their activity" in outcome.output["error"]
    assert ctx.afizi.get_draft("DRAFT-0001") is None


def test_prefill_rejects_the_booking_request_quoted_as_the_activity(ctx: ToolContext) -> None:
    message = "Reserve lot L-SFX-001 for me, my name is Leila Ben Ali."
    ctx = replace(ctx, user_messages=(message,))
    loophole = booking(
        "L-SFX-001",
        applicant_name="Leila Ben Ali",
        applicant_name_quote="Leila Ben Ali",
        activity="Not specified",
        activity_quote="Reserve lot L-SFX-001 for me",
    )

    outcome = execute_tool("prefill_request", loophole, ctx)

    assert outcome.is_error
    assert "ask the user for their activity" in outcome.output["error"]


def test_prefill_rejects_placeholder_activities(ctx: ToolContext) -> None:
    ctx = replace(ctx, user_messages=("Je m'appelle Karim, activité inconnue pour l'instant",))
    placeholder = booking(
        "L-KAI-002",
        applicant_name="Karim",
        applicant_name_quote="Karim",
        activity="Inconnu",
        activity_quote="activité inconnue",
    )

    assert execute_tool("prefill_request", placeholder, ctx).is_error


def test_quotes_match_across_case_accents_and_arabic_diacritics(ctx: ToolContext) -> None:
    ctx = replace(ctx, user_messages=("نحب نحجز L-KAI-001، إسمي سامي والنشاط متاعي نسيج",))
    arabic = booking(
        "L-KAI-001",
        applicant_name="سامي",
        applicant_name_quote="إِسمي سامي",
        activity="textile",
        activity_quote="النشاط متاعي نسيج",
    )

    assert not execute_tool("prefill_request", arabic, ctx).is_error


def test_prefill_rejects_unavailable_lot(ctx: ToolContext) -> None:
    ctx = replace(ctx, user_messages=(BOOKING_MESSAGE,))
    outcome = execute_tool("prefill_request", booking("L-KAI-003"), ctx)
    assert outcome.is_error
    assert "sold" in outcome.output["error"]


def test_track_dossier_after_confirmation(ctx: ToolContext) -> None:
    draft = ctx.afizi.create_draft(
        lot_id="L-KAI-001",
        applicant_name="Test Investor",
        company_name=None,
        activity="textile",
        phone=None,
    )
    dossier = ctx.afizi.confirm(draft.id)

    found = execute_tool("track_dossier", {"tracking_number": dossier.tracking_number.lower()}, ctx)
    assert not found.is_error
    assert found.output["status"] == "received"
    assert ctx.store.get_lot("L-KAI-001").status == "reserved"

    missing = execute_tool("track_dossier", {"tracking_number": "DEMO-9999"}, ctx)
    assert missing.is_error


def test_escalate_returns_a_ticket(ctx: ToolContext) -> None:
    outcome = execute_tool("escalate_to_human", {"reason": "Demande de l'utilisateur"}, ctx)
    assert outcome.output["ticket_id"] == "TICKET-0001"


def test_invalid_input_and_unknown_tool_are_reported_not_raised(ctx: ToolContext) -> None:
    assert execute_tool("search_lots", {"limit": 0}, ctx).is_error
    assert execute_tool("search_lots", {"colour": "blue"}, ctx).is_error
    assert execute_tool("delete_everything", {}, ctx).is_error
