# LAD backend

FastAPI + SQLAlchemy + Postgres (pgvector) service that powers LAD: chat
persistence, streaming replies, and the MCP-based tool-calling agent layer.

## Stack

- **FastAPI** + **Uvicorn** — HTTP API, SSE streaming
- **SQLAlchemy** + **Postgres** (with **pgvector**) — persistence and
  semantic search over conversation summaries
- **Ollama** — local LLM inference (chat model, agent model, embedding
  model — see [Configuration](#configuration) below)
- **MCP** (`mcp` package) — tool-calling protocol; each tool is its own
  small MCP server, launched as a subprocess per call (see
  [Tools](#tools-mcp-servers))
- **Poetry** — dependency management

## Project layout

```
src/lad/
  core/          framework glue: DB session/engine, LLM client, MCP client,
                 SSE formatting, embeddings, web search client, app startup
  helpers/       business logic: chat orchestration, the tool-calling loop,
                 message persistence, upload validation, prompt text
  models/        SQLAlchemy models (Chat, Messages, ConversationSummary)
  routes/        FastAPI routers (chat CRUD/streaming, chat listing)
  schemas/       Pydantic request/response models and Settings (env config)
  tools/         MCP tool servers: run_command (sandbox), web_search,
                 recall_memory
scripts/         standalone scripts run against a live stack (see below)
tests/
  unit_tests/        fast, fully mocked — no real DB, Ollama, or network
  integration_tests/ real Postgres via testcontainers; Ollama/embeddings
                      are still faked, this suite is DB-only by design
```

## Running it

Normally you don't run the backend on its own — `./start.sh` at the repo
root brings up Ollama, Postgres, and the full Docker Compose stack
(nginx + api + sandbox) together. See the [root README](../README.md).

To run just the backend locally against an already-running Postgres and
Ollama (e.g. for faster iteration while developing):

```bash
cd backend
poetry install
poetry run uvicorn lad.main:app --reload --port 8000
```

You'll need a `.env` file (see `.env` in this directory for the current
one) with at least `DB_*`, `OLLAMA_*`, and `MCP_SERVERS`. If running
outside Docker, set `DB_HOST=localhost` instead of `host.docker.internal`.

The database schema is created on startup (`core/startup.py` calls
`init_db()`); there is no migration tooling in this project. If you change
a model, drop and recreate the database.

## Configuration

All settings live in `schemas/config.py` (a `pydantic-settings` `Settings`
class) and are read from `.env`. The ones most worth knowing:

| Variable | Purpose |
|---|---|
| `OLLAMA_MODEL` | model used for plain chat mode |
| `OLLAMA_AGENT_MODEL` | model used for agent mode |
| `OLLAMA_EMBED_MODEL` | model used to embed conversation summaries for `recall_memory` |
| `MCP_SERVERS` | JSON list of `{"name", "command", "args"}` — which tool servers are available at all (see [Tools](#tools-mcp-servers)) |
| `MAX_TOOL_ITERATIONS` | tool-call loop cap for chat mode (small — chat mode rarely needs more than one tool call) |
| `AGENT_MAX_TOOL_ITERATIONS` | tool-call loop cap for agent mode (larger — real exploration needs more room) |
| `SUMMARY_THRESHOLD` / `RECENT_MESSAGES_TO_KEEP` | when a chat's unsummarized tail hits the threshold, everything except the last N messages gets folded into a rolling summary, which also gets embedded for `recall_memory` |
| `TAVILY_API_KEY` | required for the `web_search` tool |

## API

All routes are under `/chat` except chat listing, which is under `/app`.

| Method | Path | Notes |
|---|---|---|
| `POST` | `/chat/create` | `{title?, mode: "chat" \| "agent"}` |
| `GET` | `/app/` | list all chats |
| `GET` | `/chat/{chat_id}` | look up one chat (used by the frontend to learn an existing chat's mode) |
| `GET` | `/chat/messages?chat_id=` | full message history for a chat |
| `PATCH` | `/chat/title` | `{chat_id, title}` |
| `DELETE` | `/chat/{chat_id}` | also removes the chat's sandbox directory |
| `POST` | `/chat/msg/stream` | **multipart**: `chat_id`, `msg`, optional `files[]` — streams an SSE reply |
| `POST` | `/chat/msg/retry` | `{chat_id}` — regenerates a reply for the last unanswered turn |

`/chat/{chat_id}` is deliberately registered *after* `/chat/messages` in
`routes/chat.py` — FastAPI/Starlette match routes in registration order,
so a `{chat_id}` path parameter registered first would swallow requests to
the literal `/chat/messages` path. This has bitten the project once
already; if you add a new literal route under `/chat/`, it needs to come
before `/chat/{chat_id}`, not after.

### Streaming protocol

`/chat/msg/stream` and `/chat/msg/retry` respond with `text/event-stream`.
Events: `chunk` (a piece of the reply), `tool_call` / `tool_result` (one
per tool invocation, full serialized message), `done` (final assistant
message), `error`.

## Chat modes and the agent loop

A chat has one fixed `mode` for its whole lifetime, chosen at creation:

- **`chat`** — lighter model (`OLLAMA_MODEL`), tools: `web_search`,
  `recall_memory`
- **`agent`** — larger model (`OLLAMA_AGENT_MODEL`), tools: `run_command`,
  `web_search`, `recall_memory`; framed as a general-purpose coding agent,
  not tied to this project's own codebase

Both modes run through the same underlying loop
(`helpers/agent.py::_run_tool_turn`), parameterized by system prompt,
model, allowed tool set, and iteration cap — `run_chat_turn` and
`run_agent_turn` are thin wrappers over it. If a model calls a tool
outside its allowed set (a real risk with a smaller model under a
restricted toolset), the loop returns an error to the model instead of
dispatching the call, rather than trusting the model's own tool list
adherence.

Tool calls receive the current chat's ID via an injected subprocess
environment variable (`LAD_CHAT_ID`), never as a model-visible parameter —
this is deliberate, so the model can never spoof or misdirect which chat a
tool call is scoped to.

## Tools (MCP servers)

Each tool is a standalone MCP server under `tools/`, launched as its own
subprocess per call (configured via `MCP_SERVERS`):

- **`run_command`** (`sandbox_server.py`) — proxies to the sandbox
  container's `/execute` endpoint; agent mode only
- **`web_search`** (`web_search_server.py`) — Tavily search
- **`recall_memory`** (`memory_server.py`) — semantic search over other
  chats' embedded summaries (never the current chat — see below)

### Memory / recall_memory

There is no per-file or per-codebase RAG in this project (an earlier
version embedded this project's own source for a `search_docs` tool; it
was removed once the agent stopped being LAD-specific — a general coding
agent has no reason to know about LAD's own source, and the agent already
has real filesystem tools for anything a user actually hands it). The one
remaining semantic-search use case is cross-chat memory: `ConversationSummary`
rows (one per chat, created once a chat's unsummarized tail crosses
`SUMMARY_THRESHOLD`) get embedded via `OLLAMA_EMBED_MODEL`, and
`recall_memory` does a pgvector cosine-distance search over them,
excluding the current chat.

This means very short or brand-new chats aren't recallable yet — a
summary (and its embedding) only exists once a chat has actually
accumulated enough messages to trigger one.

## File uploads

Uploaded files are saved into a shared, chat-scoped directory
(`chat_sandboxes/{chat_id}/`) bind-mounted into both the `api` and
`sandbox` containers — one physical location, no sync step. Same filename
overwrites (no versioning). There's no server-side zip extraction; the
agent has shell access via `run_command` and unzips things itself when a
user tells it what an uploaded archive is.

## Testing

```bash
poetry run pytest tests/unit_tests            # fast, fully mocked
poetry run pytest tests/integration_tests      # real Postgres via testcontainers (needs Docker)
poetry run ruff check .
poetry run mypy .
```

The integration suite fakes `embed_texts` for every test (autouse fixture
in `tests/integration_tests/conftest.py`) — it's deliberately scoped to
testing against a real database, not a real Ollama instance.

## Scripts

`scripts/` holds standalone scripts you run against an already-running
stack (`./start.sh` at the repo root), not part of the test suite:

- `load_test_crud.py` — real concurrent load test of the CRUD endpoints
  (create/list/messages/update/delete). None of these touch Ollama, so
  this is a fair throughput/latency test.
- `profile_llm.py` — **profiling, not load testing**, for anything that
  touches the LLM. Local inference is the bottleneck for these endpoints,
  not this codebase, so throwing concurrency at them mostly measures how a
  single machine's model queues under load rather than anything actionable
  about the app. Part 1 times a few fixed, simple message cases
  sequentially; part 2 runs two agent-mode chats concurrently to check for
  cross-chat contamination in the shared sandbox container (a real
  correctness check) and to quantify — not judge — how much a second
  simultaneous chat slows things down under the sandbox's fixed resource
  budget.

Both take `--base-url` (default `http://localhost:8000/api`); see each
script's `--help` for the rest.

## Known limitations

- **One Ollama model loaded at a time** (`start.sh` sets
  `OLLAMA_MAX_LOADED_MODELS=1`). Switching between chat mode and agent
  mode in the same session forces a model reload, which shows up as extra
  latency on the first message after a switch — this is a hardware/config
  tradeoff for running multiple models on a single local machine, not a
  bug in the app.
- **The sandbox container is shared, not per-chat.** Isolation between
  chats is directory-based (`chat_sandboxes/{chat_id}/`), not
  container-level — every agent-mode chat's `run_command` calls share one
  container's fixed `0.5 cpu` / `512m` budget. Verified safe from
  cross-chat contamination under real concurrency (see `profile_llm.py`),
  but concurrent agent-mode chats will visibly slow each other down.
- **No migration tooling.** Schema changes require a DB reset.