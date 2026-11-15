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


def test_prefill_creates_a_draft_but_submits_nothing(ctx: ToolContext) -> None:
    outcome = execute_tool(
        "prefill_request",
        {"lot_id": "l-kai-001", "applicant_name": "Test Investor", "activity": "textile"},
        ctx,
    )
    assert not outcome.is_error
    assert outcome.output["draft"]["status"] == "awaiting_confirmation"
    assert outcome.output["draft"]["tracking_number"] is None
    assert ctx.store.get_lot("L-KAI-001").status == "available"


def test_prefill_rejects_unavailable_lot(ctx: ToolContext) -> None:
    outcome = execute_tool(
        "prefill_request",
        {"lot_id": "L-KAI-003", "applicant_name": "Test Investor", "activity": "textile"},
        ctx,
    )
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
