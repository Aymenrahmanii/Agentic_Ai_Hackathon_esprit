import json
import re
import time
from dataclasses import dataclass, replace
from typing import Any

from afi_agent.language import (
    detect_language,
    has_mixed_script_word,
    reply_language_instruction,
)
from afi_agent.llm import LLM, LLMError, LLMTurn
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
Egyptian or Gulf ones. Write ids exactly as tool results give them, in Latin characters (for \
example TICKET-0001 or L-KAI-001), even inside an Arabic-script reply; never spell them out \
in words. Keep proper nouns as tool results give them. Translate \
French sector and infrastructure terms into the reply language (plasturgie is البلاستيك in \
Arabic script), and never mix Arabic and Latin letters inside one word.

Grounding: every fact about lots, zones, prices, procedures and dossiers must come from a tool \
result in this conversation. Do not add details the tools did not return, such as where a \
notice is published, which office to visit, or extra documents. If the tools do not have the \
answer, say so and offer to hand over to an AFI agent, and call escalate_to_human only once \
the user accepts. When the user asks to talk to a person, call escalate_to_human straight away \
without asking for confirmation, then give them the ticket id. If a search had no sector \
filter, do not claim the lots suit the user's activity. Tool arguments use French names (for \
example the governorate "Kairouan"), whatever language the user speaks.

Scope: you only help with AFI industrial land services. For anything else, such as weather or \
general questions, say in one sentence what you can help with, without calling any tool.

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

REWRITE_PROMPT = """\
Rewrite the text you are given, keeping its language, meaning and length. No word may mix \
Arabic and Latin letters: write each foreign term fully in the script of the surrounding \
sentence, translating it if needed. Ids such as L-KAI-001 or DRAFT-0001 stay exactly as they \
are, in Latin characters, never spelled out in words. Reply with the rewritten text only.
"""

# Ids a reply must repeat to the user when a tool returned them.
REFERENCE_KEYS = ("ticket_id", "draft_id", "tracking_number")

GROUNDING_RETRY = (
    "\nYour previous answer gave lot ids or prices without looking them up. Call the tools "
    "to get the facts before answering; never answer from memory.\n"
)

_LOT_ID = re.compile(r"\bL-[A-Z]{3}-\d{3}\b")

# Matches the system prompt's "mention at most three" lots.
MAX_LOTS_MENTIONED = 3

# Words that only appear when a reply quotes prices or areas (French, English, Arabic, Arabizi).
_FACT_WORDS = re.compile(
    r"\b(dinars?|DT|TND|m²|m2|mètres? carrés?|square met(?:re|er)s?|hectares?|"
    r"metr\w*)\b|دينار|متر مربع|هكتار",
    re.IGNORECASE,
)
# A quoted amount: digits, or a number written as a word ("تسعين ألف", "alf", "mille").
_AMOUNT = re.compile(
    r"\d|ألف|آلاف|مائة|مية|\b(alf|mia|mille|cent|thousand|hundred)\b", re.IGNORECASE
)

# Shown instead of a reply that still states unverified facts after the retry.
_UNVERIFIED_REPLY = {
    "arabic_script": "خليني نثبت في المعطيات قبل ما نجاوبك. تنجم تعاود السؤال من فضلك؟",
    "arabizi": "Khalini nthabet fil ma3loumet 9bal ma njewbek. Tnajjem t3awed el so2el?",
    "fr": "Je préfère vérifier ces informations avant de répondre. Pouvez-vous reposer "
    "la question ?",
    "en": "I'd rather check that information before answering. Could you ask again?",
}

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
        ctx = replace(self._ctx, user_messages=_user_texts(messages))
        # Models drift to the language of the tool data (French); a hint per turn holds better
        # than the general rule in the system prompt.
        hint = reply_language_instruction(user_text)
        system = f"{SYSTEM_PROMPT}\n{hint}\n" if hint else SYSTEM_PROMPT

        try:
            text, stop_reason = self._loop(system, messages, tools, records, ctx, turn_start)
            # A reply quoting lot ids or prices no tool returned was answered from memory.
            # Drop it and try once more, telling the model to look the facts up.
            if stop_reason != "refusal" and _ungrounded(text, messages):
                del messages[turn_start + 1 :]
                records.clear()
                text, stop_reason = self._loop(
                    system + GROUNDING_RETRY, messages, tools, records, ctx, turn_start
                )
                if stop_reason != "refusal" and _ungrounded(text, messages):
                    # Never show invented prices: say so and leave nothing false in the history.
                    text = _UNVERIFIED_REPLY[detect_language(user_text) or "fr"]
                    stop_reason = "unverified"
                    del messages[turn_start + 1 :]
                    records.clear()
                    messages.append({"role": "assistant", "content": text})
        except Exception:
            del messages[turn_start:]
            raise

        if messages and messages[-1]["role"] == "assistant":
            references = _references(records)
            if has_mixed_script_word(text) or _missing(references, text):
                text = self._rewrite(text, references)
                messages[-1] = {"role": "assistant", "content": text}

        return AgentReply(
            text=to_speech_text(text),
            raw_text=text,
            tool_records=records,
            pending_draft_id=_pending_draft_id(records),
            stop_reason=stop_reason,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _loop(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        records: list[ToolRecord],
        ctx: ToolContext,
        turn_start: int,
    ) -> tuple[str, str]:
        for _ in range(self._max_steps):
            turn = self._llm.complete(system=system, messages=messages, tools=tools)
            if turn.stop_reason == "refusal":
                del messages[turn_start:]
                return _REFUSAL_REPLY, "refusal"
            messages.append({"role": "assistant", "content": turn.assistant_content})
            if not turn.tool_calls:
                return turn.text, turn.stop_reason
            messages.append({"role": "user", "content": self._run_tools(turn, records, ctx)})
        return _MAX_STEPS_REPLY, "max_steps"

    def _rewrite(self, text: str, references: list[str]) -> str:
        """One extra call to fix what a voice or the user cannot use: words like "أavis", or an
        id such as DRAFT-0001 spelled out in words. Keeps the original unless the rewrite
        fixes both problems."""
        system = REWRITE_PROMPT
        if references:
            system += f"The text must contain these ids written exactly: {', '.join(references)}.\n"
        try:
            turn = self._llm.complete(
                system=system, messages=[{"role": "user", "content": text}], tools=[]
            )
        except LLMError:
            return text
        rewritten = turn.text.strip()
        fixed = rewritten and not has_mixed_script_word(rewritten)
        return rewritten if fixed and not _missing(references, rewritten) else text

    def _run_tools(
        self, turn: LLMTurn, records: list[ToolRecord], ctx: ToolContext
    ) -> list[dict[str, Any]]:
        # All results of one assistant turn go back in a single user message.
        results = []
        for call in turn.tool_calls:
            outcome = execute_tool(call.name, call.input, ctx)
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


def _tool_result_text(messages: list[dict[str, Any]]) -> str:
    return " ".join(
        str(block.get("content", ""))
        for m in messages
        if m["role"] == "user" and isinstance(m["content"], list)
        for block in m["content"]
        if block.get("type") == "tool_result"
    )


def _ungrounded(text: str, messages: list[dict[str, Any]]) -> bool:
    """True when the reply states facts no tool returned in this conversation:

    - a lot id that neither a tool result nor the user's own messages contain, or
    - prices or areas (in any language, digits or words) when no tool has run at all.
    Ids can be spelled out in words, which the first check misses; the second catches that."""
    tool_text = _tool_result_text(messages)
    seen = tool_text + " " + " ".join(_user_texts(messages))
    if any(lot_id not in seen for lot_id in _LOT_ID.findall(text)):
        return True
    return not tool_text and bool(_FACT_WORDS.search(text)) and bool(_AMOUNT.search(text))


def _references(records: list[ToolRecord]) -> list[str]:
    """Ids the reply must contain: tickets, drafts and tracking numbers, and the first lots a
    search found (the prompt allows mentioning at most three)."""
    references = [
        str(r.output[key])
        for r in records
        if not r.is_error
        for key in REFERENCE_KEYS
        if key in r.output
    ]
    for r in records:
        if r.name == "search_lots" and not r.is_error:
            references += [lot["id"] for lot in r.output.get("lots", [])[:MAX_LOTS_MENTIONED]]
    return list(dict.fromkeys(references))


def _missing(references: list[str], text: str) -> list[str]:
    return [ref for ref in references if ref not in text]


def _user_texts(messages: list[dict[str, Any]]) -> tuple[str, ...]:
    # Tool results also travel as role "user", but as lists of blocks, not strings.
    return tuple(
        m["content"] for m in messages if m["role"] == "user" and isinstance(m["content"], str)
    )


def _pending_draft_id(records: list[ToolRecord]) -> str | None:
    for record in reversed(records):
        if record.name == "prefill_request" and not record.is_error:
            return record.output["draft_id"]
    return None
