from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from afi_agent.afizi_mock import AfiziConflict, AfiziMock, AfiziNotFound
from afi_agent.models import Lot, Zone
from afi_agent.store import KnowledgeStore, normalize


class ToolError(Exception):
    """A failure the model can read and recover from."""


@dataclass(frozen=True)
class ToolContext:
    store: KnowledgeStore
    afizi: AfiziMock


@dataclass(frozen=True)
class ToolOutcome:
    output: dict[str, Any]
    is_error: bool


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    run: Callable[[Any, ToolContext], dict[str, Any]]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchLotsInput(_Input):
    governorate: str | None = Field(
        default=None, description="Governorate name in French, e.g. 'Kairouan'."
    )
    sector: str | None = Field(
        default=None,
        description="Map the user's activity to one of the known sectors (listed in the tool "
        "description), e.g. a food processing plant is 'agroalimentaire'. Set it whenever the "
        "user names an activity.",
    )
    min_area_m2: float | None = Field(default=None, ge=0)
    max_price_tnd: float | None = Field(
        default=None, ge=0, description="Maximum total price of the lot in Tunisian dinars."
    )
    limit: int = Field(default=5, ge=1, le=20)


class CompareZonesInput(_Input):
    places: list[str] = Field(
        min_length=2,
        max_length=4,
        description="Zone ids (e.g. 'ZI-KAI-01') or governorate names in French.",
    )


class GetProcedureInput(_Input):
    procedure_id: str


class PrefillRequestInput(_Input):
    lot_id: str
    applicant_name: str = Field(min_length=1, description="As the user stated it.")
    activity: str = Field(
        min_length=1,
        description="What the investor plans to produce, as the user stated it. If the user "
        "has not said, do not call this tool: ask them first. Never guess or use a generic "
        "value.",
    )
    company_name: str | None = None
    phone: str | None = None


class TrackDossierInput(_Input):
    tracking_number: str


class EscalateInput(_Input):
    reason: str = Field(min_length=1, description="Why a human agent is needed, in French.")


def _lot_summary(lot: Lot, zone: Zone) -> dict[str, Any]:
    return {
        **lot.model_dump(),
        "zone_name": zone.name,
        "governorate": zone.governorate,
        "sectors": zone.sectors,
    }


def _resolve_governorate(text: str, store: KnowledgeStore) -> str:
    resolved = store.resolve_governorate(text)
    if resolved is None:
        known = ", ".join(store.governorates())
        raise ToolError(f"Unknown governorate '{text}'. Known governorates: {known}")
    return resolved


def known_sectors(store: KnowledgeStore) -> list[str]:
    return sorted({sector for zone in store.zones() for sector in zone.sectors})


def _resolve_sector(text: str, store: KnowledgeStore) -> str:
    wanted = normalize(text)
    for sector in known_sectors(store):
        if normalize(sector) == wanted:
            return sector
    known = ", ".join(known_sectors(store))
    raise ToolError(f"Unknown sector '{text}'. Use one of: {known}")


def _search_lots(args: SearchLotsInput, ctx: ToolContext) -> dict[str, Any]:
    governorate = _resolve_governorate(args.governorate, ctx.store) if args.governorate else None
    sector = _resolve_sector(args.sector, ctx.store) if args.sector else None
    matches = ctx.store.search_lots(
        governorate=governorate,
        sector=sector,
        min_area_m2=args.min_area_m2,
        max_price_tnd=args.max_price_tnd,
        limit=args.limit,
    )
    return {"count": len(matches), "lots": [_lot_summary(lot, zone) for lot, zone in matches]}


def _zones_for_place(place: str, store: KnowledgeStore) -> list[Zone]:
    zone = store.get_zone(place.strip().upper())
    if zone is not None:
        return [zone]
    governorate = store.resolve_governorate(place)
    if governorate is None:
        raise ToolError(f"'{place}' is neither a zone id nor a known governorate")
    return [z for z in store.zones() if z.governorate == governorate]


def _zone_summary(zone: Zone, store: KnowledgeStore) -> dict[str, Any]:
    available = [lot for lot in store.lots_in_zone(zone.id) if lot.status == "available"]
    prices = [lot.price_tnd_per_m2 for lot in available]
    areas = [lot.area_m2 for lot in available]
    return {
        **zone.model_dump(),
        "available_lots": len(available),
        "price_tnd_per_m2_range": [min(prices), max(prices)] if prices else None,
        "lot_area_m2_range": [min(areas), max(areas)] if areas else None,
    }


def _compare_zones(args: CompareZonesInput, ctx: ToolContext) -> dict[str, Any]:
    zones: dict[str, Zone] = {}
    for place in args.places:
        for zone in _zones_for_place(place, ctx.store):
            zones[zone.id] = zone
    return {"zones": [_zone_summary(zone, ctx.store) for zone in zones.values()]}


def _get_procedure(args: GetProcedureInput, ctx: ToolContext) -> dict[str, Any]:
    procedure = ctx.store.get_procedure(args.procedure_id)
    if procedure is None:
        known = ", ".join(p.id for p in ctx.store.procedures())
        raise ToolError(f"Unknown procedure '{args.procedure_id}'. Known procedures: {known}")
    return procedure.model_dump()


def _prefill_request(args: PrefillRequestInput, ctx: ToolContext) -> dict[str, Any]:
    try:
        draft = ctx.afizi.create_draft(
            lot_id=args.lot_id.strip().upper(),
            applicant_name=args.applicant_name,
            company_name=args.company_name,
            activity=args.activity,
            phone=args.phone,
        )
    except (AfiziNotFound, AfiziConflict) as exc:
        raise ToolError(str(exc)) from exc
    return {
        "draft_id": draft.id,
        "draft": draft.model_dump(),
        "next_step": "Not submitted. The user must review the draft and confirm on screen.",
    }


def _track_dossier(args: TrackDossierInput, ctx: ToolContext) -> dict[str, Any]:
    dossier = ctx.afizi.get_dossier(args.tracking_number)
    if dossier is None:
        raise ToolError(f"No dossier found for tracking number '{args.tracking_number}'")
    return dossier.model_dump()


def _escalate(args: EscalateInput, ctx: ToolContext) -> dict[str, Any]:
    return {"ticket_id": ctx.afizi.escalate(), "reason": args.reason, "status": "queued"}


TOOLS: tuple[Tool, ...] = (
    Tool(
        "search_lots",
        "Find available industrial lots, cheapest first. All filters are optional.",
        SearchLotsInput,
        _search_lots,
    ),
    Tool(
        "compare_zones",
        "Compare industrial zones side by side: sectors, infrastructure, incentives status, "
        "available lots and price range.",
        CompareZonesInput,
        _compare_zones,
    ),
    Tool(
        "get_procedure",
        "Get the steps and required documents of an AFI procedure.",
        GetProcedureInput,
        _get_procedure,
    ),
    Tool(
        "prefill_request",
        "Prepare a draft lot request for the user to review. This does not submit anything; "
        "only the user can submit, by confirming on screen.",
        PrefillRequestInput,
        _prefill_request,
    ),
    Tool(
        "track_dossier",
        "Look up the status of a submitted request by its tracking number.",
        TrackDossierInput,
        _track_dossier,
    ),
    Tool(
        "escalate_to_human",
        "Hand the conversation to a human AFI agent. Only call it when the user asks to talk "
        "to a person, or has just accepted your offer of one. Never call it for questions "
        "unrelated to AFI land services.",
        EscalateInput,
        _escalate,
    ),
)

_BY_NAME = {tool.name: tool for tool in TOOLS}


def tool_schemas(store: KnowledgeStore) -> list[dict[str, Any]]:
    """Tool definitions in the Messages API shape (name, description, input_schema)."""
    procedure_ids = ", ".join(p.id for p in store.procedures())
    sectors = ", ".join(known_sectors(store))
    schemas = []
    for tool in TOOLS:
        description = tool.description
        if tool.name == "get_procedure":
            description += f" Available procedure ids: {procedure_ids}."
        if tool.name == "search_lots":
            description += f" Known sectors: {sectors}."
        schemas.append(
            {
                "name": tool.name,
                "description": description,
                "input_schema": tool.input_model.model_json_schema(),
            }
        )
    return schemas


def execute_tool(name: str, raw_input: dict[str, Any], ctx: ToolContext) -> ToolOutcome:
    tool = _BY_NAME.get(name)
    if tool is None:
        return ToolOutcome({"error": f"Unknown tool '{name}'"}, is_error=True)
    try:
        args = tool.input_model.model_validate(raw_input)
        return ToolOutcome(tool.run(args, ctx), is_error=False)
    except ValidationError as exc:
        return ToolOutcome({"error": f"Invalid input: {exc}"}, is_error=True)
    except ToolError as exc:
        return ToolOutcome({"error": str(exc)}, is_error=True)
