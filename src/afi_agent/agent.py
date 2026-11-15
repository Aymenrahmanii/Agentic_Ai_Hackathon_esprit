import json
import time
from dataclasses import dataclass
from typing import Any

from afi_agent.language import reply_language_instruction
from afi_agent.llm import LLM, LLMTurn
from afi_agent.speech import to_speech_text
from afi_agent.tools import ToolContext, execute_tool, tool_schemas

SYSTEM_PROMPT = """\
You are the virtual assistant of AFI (Agence Foncière Industrielle, Tunisia). You help \
investors find industrial lots, understand procedures and prepare a lot request.

Language: answer in the same language and the same script as the user's latest message. \
English gets English, French gets French, Modern Standard Arabic gets Modern Standard Arabic. \
Tunisian Derja written in Arabic script gets Tunisian Derja in Arabic script. Tunisian Derja \
written in Latin letters and digits ("Arabizi", e.g. "n7eb nechri ardh fi sfax") gets Tunisian \
Derja in Latin letters and digits, never Arabic script. Use Tunisian words, not Moroccan, \
Egyptian or Gulf ones. Keep ids and proper nouns exactly as tool results give them.

Grounding: every fact about lots, zones, prices, procedures and dossiers must come from a tool \
result in this conversation. Do not add details the tools did not return, such as where a \
notice is published, which office to visit, or extra documents. If the tools do not have the \
answer, say so and offer to hand over to an AFI agent with escalate_to_human. Tool arguments \
use French names (for example the governorate "Kairouan"), whatever language the user speaks.

References: when a tool returns a ticket id, draft id or tracking number, always tell the user \
that reference.

Requests: prefill_request only prepares a draft. You cannot submit it; the user submits by \
pressing Confirm on screen. After preparing a draft, summarise it and ask the user to check it \
and press Confirm. If the applicant's name or activity is missing, ask for it instead of \
inventing it.

Style: your replies are spoken by a text-to-speech voice. Write plain sentences only: no \
markdown, no bold, no bullet points, no numbered lists, no tables, no arrows or emoji. Keep it \
to at most four short sentences. If there are several lots, mention at most three, each in \
one sentence. Give prices in dinars.
"""

_REFUSAL_REPLY = "Désolé, je ne peux pas répondre à cette demande."
_MAX_STEPS_REPLY = "Désolé, je n'ai pas pu terminer cette demande. Pouvez-vous reformuler ?"


@dataclass(frozen=True)
class ToolRecord:
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    is_error: bool


@dataclass(frozen=True)
class AgentReply:
    text: str  # cleaned for text-to-speech
    raw_text: str  # exactly what the model wrote
    tool_records: list[ToolRecord]
    pending_draft_id: str | None
    stop_reason: str
    latency_ms: float


class Agent:
    def __init__(self, llm: LLM, ctx: ToolContext, *, max_steps: int = 6) -> None:
        self._llm = llm
        self._ctx = ctx
        self._max_steps = max_steps

    def respond(self, messages: list[dict[str, Any]], user_text: str) -> AgentReply:
        """Answer one user turn. `messages` is the session transcript and is extended in place;
        it is left untouched if the turn fails or is refused."""
        started = time.perf_counter()
        turn_start = len(messages)
        messages.append({"role": "user", "content": user_text})
        records: list[ToolRecord] = []
        tools = tool_schemas(self._ctx.store)
        # Models drift to the language of the tool data (French); a hint per turn holds better
        # than the general rule in the system prompt.
        hint = reply_language_instruction(user_text)
        system = f"{SYSTEM_PROMPT}\n{hint}\n" if hint else SYSTEM_PROMPT
        text, stop_reason = _MAX_STEPS_REPLY, "max_steps"

        try:
            for _ in range(self._max_steps):
                turn = self._llm.complete(system=system, messages=messages, tools=tools)
                if turn.stop_reason == "refusal":
                    del messages[turn_start:]
                    text, stop_reason = _REFUSAL_REPLY, "refusal"
                    break
                messages.append({"role": "assistant", "content": turn.assistant_content})
                if not turn.tool_calls:
                    text, stop_reason = turn.text, turn.stop_reason
                    break
                messages.append({"role": "user", "content": self._run_tools(turn, records)})
        except Exception:
            del messages[turn_start:]
            raise

        return AgentReply(
            text=to_speech_text(text),
            raw_text=text,
            tool_records=records,
            pending_draft_id=_pending_draft_id(records),
            stop_reason=stop_reason,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _run_tools(self, turn: LLMTurn, records: list[ToolRecord]) -> list[dict[str, Any]]:
        # All results of one assistant turn go back in a single user message.
        results = []
        for call in turn.tool_calls:
            outcome = execute_tool(call.name, call.input, self._ctx)
            records.append(ToolRecord(call.name, call.input, outcome.output, outcome.is_error))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": json.dumps(outcome.output, ensure_ascii=False),
                    "is_error": outcome.is_error,
                }
            )
        return results


def _pending_draft_id(records: list[ToolRecord]) -> str | None:
    for record in reversed(records):
        if record.name == "prefill_request" and not record.is_error:
            return record.output["draft_id"]
    return None
