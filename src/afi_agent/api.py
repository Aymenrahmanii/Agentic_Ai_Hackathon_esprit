from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from afi_agent.afizi_mock import AfiziConflict, AfiziMock, AfiziNotFound
from afi_agent.agent import Agent
from afi_agent.config import Settings, load_settings
from afi_agent.llm import LLM, LLMError, build_llm
from afi_agent.models import Dossier, RequestDraft
from afi_agent.store import InMemoryStore, KnowledgeStore
from afi_agent.tools import ToolContext

WEB_DIR = Path(__file__).resolve().parent / "web"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ToolCallOut(BaseModel):
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    is_error: bool


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[ToolCallOut]
    # Set when the agent prepared a request; the UI shows it with a Confirm button.
    pending_draft: RequestDraft | None
    latency_ms: float
    # Which model wrote the reply, e.g. the fallback when the main provider was down.
    model: str | None


class StatusOut(BaseModel):
    model: str
    fallback: str | None
    synthetic_data: bool
    data_note: str


@dataclass
class _State:
    settings: Settings
    ctx: ToolContext
    llm: LLM | None
    sessions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def agent(self) -> Agent:
        # Built on first use so the app starts (and /health answers) without credentials.
        if self.llm is None:
            self.llm = build_llm(self.settings)
        return Agent(self.llm, self.ctx, max_steps=self.settings.max_agent_steps)


def map_data(store: KnowledgeStore) -> dict[str, Any]:
    """Zones with their lots, for the map. Only data the agent can also see."""
    zones = []
    for zone in store.zones():
        lots = store.lots_in_zone(zone.id)
        zones.append(
            {
                **zone.model_dump(),
                "lots": [lot.model_dump() for lot in lots],
                "available": sum(lot.status == "available" for lot in lots),
            }
        )
    return {"zones": zones}


def make_store(settings: Settings) -> InMemoryStore:
    if settings.store == "neo4j":
        from afi_agent.graph_store import Neo4jStore, neo4j_driver  # optional `graph` extra

        return Neo4jStore(neo4j_driver())
    if settings.store != "memory":
        raise ValueError(f"Unknown AFI_STORE '{settings.store}' (use memory or neo4j)")
    return InMemoryStore.from_file(settings.seed_path)


def create_app(llm: LLM | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = make_store(settings)
    afizi = AfiziMock(store)
    state = _State(settings=settings, ctx=ToolContext(store=store, afizi=afizi), llm=llm)
    app = FastAPI(title="AFI agent")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status")
    def status() -> StatusOut:
        configured = "replay (offline)" if settings.provider == "replay" else settings.model
        return StatusOut(
            model=configured if llm is None else getattr(llm, "last_model", None) or "scripted",
            fallback=settings.fallback_provider if llm is None else None,
            synthetic_data=store.synthetic,
            data_note=store.data_note,
        )

    @app.get("/map")
    def map_endpoint() -> dict[str, Any]:
        return map_data(store)

    @app.post("/chat")
    def chat(request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or uuid4().hex
        messages = state.sessions.setdefault(session_id, [])
        try:
            agent = state.agent()
            reply = agent.respond(messages, request.message)
        except LLMError as exc:
            raise HTTPException(503 if exc.retryable else 502, detail=str(exc)) from exc

        draft = afizi.get_draft(reply.pending_draft_id) if reply.pending_draft_id else None
        return ChatResponse(
            session_id=session_id,
            reply=reply.text,
            tool_calls=[
                ToolCallOut(name=r.name, input=r.input, output=r.output, is_error=r.is_error)
                for r in reply.tool_records
            ],
            pending_draft=draft,
            latency_ms=reply.latency_ms,
            model=getattr(state.llm, "last_model", None),
        )

    @app.post("/requests/{draft_id}/confirm")
    def confirm_request(draft_id: str) -> Dossier:
        """The only path that submits a request. Called by the UI on the user's click."""
        try:
            return afizi.confirm(draft_id)
        except AfiziNotFound as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        except AfiziConflict as exc:
            raise HTTPException(409, detail=str(exc)) from exc

    if WEB_DIR.is_dir():

        @app.middleware("http")
        async def revalidate_static(request: Request, call_next):  # type: ignore[no-untyped-def]
            # The interface changes often before a demo; never serve a stale script or style.
            response = await call_next(request)
            if request.url.path == "/" or request.url.path.startswith("/static/"):
                response.headers["Cache-Control"] = "no-cache"
            return response

        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(WEB_DIR / "index.html")

    return app
