# AFI agent (hackathon scaffold)

A multilingual agent (Tunisian Derja, French, Arabic, English) that helps investors find
industrial lots, understand AFI procedures and prepare a lot request.

**Everything in `data/seed.json` is invented placeholder data.** Replace it with data collected
from AFI's public pages before any demo.

## Quickstart

```bash
uv sync
uv run pytest
cp .env.example .env   # then set AFI_API_KEY
uv run --env-file .env uvicorn afi_agent.api:create_app --factory --reload
```

Then open http://127.0.0.1:8000/docs and try `POST /chat`.

## Model provider

The default is any OpenAI-compatible endpoint, configured for Groq's free tier. Switch
provider or model in `.env` (`AFI_PROVIDER`, `AFI_BASE_URL`, `AFI_API_KEY`, `AFI_MODEL`);
`.env.example` lists Gemini, OpenRouter, Ollama and Anthropic settings. Compare candidates
with the eval before choosing one.

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
uv run --env-file .env python evals/run_eval.py --limit 3
```

Each case spends API quota (or money on a paid provider). Results are saved under `evals/results/`. Grow
`evals/golden.jsonl` towards 50 cases and have a native speaker review the Derja ones.

## Not built yet

- Speech-to-text and text-to-speech
- Neo4j-backed `KnowledgeStore`
- Frontend (chat, push-to-talk, map)
- Real AFI data
