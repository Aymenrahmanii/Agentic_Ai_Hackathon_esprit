from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from afi_agent.afizi_mock import AfiziConflict, AfiziMock, AfiziNotFound
from afi_agent.agent import Agent
from afi_agent.config import Settings, load_settings
from afi_agent.llm import LLM, LLMError, build_llm
from afi_agent.models import Dossier, RequestDraft
from afi_agent.store import InMemoryStore
from afi_agent.tools import ToolContext


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


def create_app(llm: LLM | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = InMemoryStore.from_file(settings.seed_path)
    afizi = AfiziMock(store)
    state = _State(settings=settings, ctx=ToolContext(store=store, afizi=afizi), llm=llm)
    app = FastAPI(title="AFI agent")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or uuid4().hex
        messages = state.sessions.setdefault(session_id, [])
        try:
            reply = state.agent().respond(messages, request.message)
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

    return app
