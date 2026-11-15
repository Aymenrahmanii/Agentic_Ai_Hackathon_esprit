# AFI agent (hackathon scaffold)

A multilingual agent (Tunisian Derja, French, Arabic, English) that helps investors find
industrial lots, understand AFI procedures and prepare a lot request.

**Everything in `data/seed.json` is invented placeholder data.** Replace it with data collected
from AFI's public pages before any demo.

## Quickstart

```bash
uv sync
uv run pytest
cp .env.example .env   # then set GEMINI_API_KEY and GROQ_API_KEY
uv run --env-file .env uvicorn afi_agent.api:create_app --factory --reload
```

Then open http://127.0.0.1:8000/docs and try `POST /chat`.

## Model provider

The default is Gemini 3.5 Flash-Lite, with Groq's `openai/gpt-oss-120b` as the fallback. If
Gemini is rate-limited or unreachable, the agent answers with Groq and stays on it for 60
seconds before trying Gemini again. The fallback is skipped when `GROQ_API_KEY` is empty.

On the 31-case golden set both models pass 30 cases, but Gemini answers in about 2.4 s
(median) against 5–10 s for Groq's free tier, which also allows only about 200,000 tokens a
day. Settings are in `.env` (`AFI_PROVIDER`, `AFI_FALLBACK_PROVIDER`, `GEMINI_MODEL`,
`GROQ_MODEL`); `.env.example` also lists OpenRouter, Ollama and Anthropic. Compare candidates
with the eval before switching.

## How it fits together

| Path | Role |
|---|---|
| `src/afi_agent/agent.py` | Tool-calling loop and system prompt |
| `src/afi_agent/tools.py` | The six tools the model can call, with validated inputs |
| `src/afi_agent/store.py` | `KnowledgeStore` protocol and the in-memory implementation |
| `src/afi_agent/afizi_mock.py` | Stand-in for AFI's request back office |
| `src/afi_agent/llm.py` | Model seam: `OpenAICompatLLM`, `AnthropicLLM`, and `ScriptedLLM` for tests and offline demos |
| `src/afi_agent/api.py` | FastAPI app: `/chat`, `/requests/{id}/confirm`, `/health` |
| `src/afi_agent/evaluation.py`, `evals/` | Golden set and scoring |
| `graph/`, `src/afi_agent/graph_export.py` | Neo4j schema and seed export |

The agent can prepare a request draft but cannot submit one. Only
`POST /requests/{draft_id}/confirm`, called by the UI when the user clicks Confirm, submits it.

## Knowledge graph

```bash
uv run python -m afi_agent.graph_export graph/seed.cypher
docker compose --env-file .env up -d
docker compose exec neo4j cypher-shell -u neo4j -p <password> -f /graph/schema.cypher
docker compose exec neo4j cypher-shell -u neo4j -p <password> -f /graph/seed.cypher
```

The agent still reads from `InMemoryStore`. A Neo4j-backed store only has to implement the
`KnowledgeStore` protocol in `store.py`.

## Evaluation

```bash
uv run --env-file .env python evals/run_eval.py --pause 2
```

Useful options: `--only id1,id2` runs selected cases, `--provider groq` (or `gemini`) picks
the provider, and `--model` overrides its model. The eval never uses the fallback, so each run
measures exactly one model.

Each case spends API quota (or money on a paid provider). Results, including every reply, are
saved under `evals/results/`.

Each case scores two things. **Passed**: the right tool was called with the right arguments,
or, for cases with `"expected_tool": null`, no forbidden tool was called (for example, not
preparing a request when the applicant's name is missing). **Style**: the reply is in the user's
language and script, contains no markdown, and gives any ticket or draft id the tools returned.
Neither judges the quality of the Derja, so have a native speaker review the replies. Grow
`evals/golden.jsonl` towards 50 cases.

## Not built yet

- Speech-to-text and text-to-speech
- Neo4j-backed `KnowledgeStore`
- Frontend (chat, push-to-talk, map)
- Real AFI data
