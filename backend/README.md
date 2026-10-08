# LAD backend

Async FastAPI + SQLAlchemy + Postgres (pgvector) service that powers LAD: chat
persistence, SSE replies, and the MCP-based tool-calling agent layer.

## Stack

- **FastAPI** + **Uvicorn**: HTTP API and SSE
- **SQLAlchemy 2 (asyncio)** + **psycopg** + **Postgres with pgvector**:
  persistence and semantic search over conversation summaries
- **httpx (async)**: Ollama client for chat, tool calling and embeddings
- **MCP** (`mcp` package): tool-calling protocol. Each tool is its own small
  MCP server, launched as a stdio subprocess
- **Poetry** for dependency management

## Project layout

```
src/lad/
  core/      app factory (+ client allowlist), async DB engine/sessions, Ollama
             client, embeddings, MCP client, JSON logging, SSE formatting,
             lifespan startup, Tavily client
  helpers/   chat orchestration and summaries, the tool-calling loop, message
             persistence, upload handling, prompts
  models/    SQLAlchemy models (Chat, Messages, ConversationSummary)
  routes/    FastAPI routers (chat, chat listing) and shared error handling
  schemas/   Pydantic request/response models and Settings (env config)
  tools/     MCP tool servers: run_command, web_search, recall_memory
scripts/     standalone scripts run against a live stack
tests/
  unit_tests/         fast, fully mocked: no DB, Ollama or network
  integration_tests/  real Postgres via testcontainers; Ollama/embeddings
                      are faked
```

## Running it

Normally you don't run the backend alone: `./start.sh` at the repo root brings
up Ollama, Postgres and the Docker Compose stack (nginx, api, sandbox). See the
[root README](../README.md).

To iterate on just the backend against a running stack:

```bash
cd backend
poetry install
poetry run uvicorn lad.main:app --reload --port 8001
```

Use a `.env` copied from `env_example`, with `DB_HOST=localhost` (Postgres is
published on `127.0.0.1:5432`) and `OLLAMA_HOST=http://localhost:11434`. The
`run_command` tool needs the sandbox from the compose stack, which isn't
reachable from outside Docker, so agent commands only work through the stack.

The schema is created on startup in a background task that retries every 30
seconds until the database is reachable; requests made before it succeeds get a
`503`. There is no migration tooling: if you change a model, drop and recreate
the database.

## Configuration

All settings live in `schemas/config.py` and are read from `.env`
(see `env_example`).

| Variable | Default | Purpose |
|---|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT` | none / `5432` | Postgres connection. Use `DB_HOST=lad-db` inside Docker |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama base URL |
| `OLLAMA_MODEL` | `qwen3:8b` | model for chat mode (and summaries of chat-mode chats) |
| `OLLAMA_AGENT_MODEL` | `gemma4:12b` | model for agent mode (and summaries of agent chats) |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma` | embeds summaries for `recall_memory` |
| `EMBEDDING_DIM` | `768` | vector size; must match the embedding model (changing it needs a DB reset) |
| `OLLAMA_TIMEOUT` | `120.0` | seconds per Ollama request |
| `OLLAMA_NUM_CTX` | `8192` | context window requested from Ollama |
| `SUMMARY_THRESHOLD` / `RECENT_MESSAGES_TO_KEEP` | `20` / `8` | when a chat's unsummarized tail reaches the threshold, everything except the last N messages is folded into a rolling summary |
| `MCP_SERVERS` | `[]` | JSON list of `{"name", "command", "args"}`: which tool servers exist |
| `MAX_TOOL_ITERATIONS` | `3` | tool-call loop cap, chat mode |
| `AGENT_MAX_TOOL_ITERATIONS` | `8` | tool-call loop cap, agent mode |
| `MAX_TOOL_OUTPUT_CHARS` | `6000` | tool output longer than this is cut (head and tail kept) before it reaches the model and the database |
| `TAVILY_API_KEY` | empty | required for `web_search` |
| `SANDBOX_URL` | `http://sandbox:8000` | where `run_command` sends commands |
| `ALLOWED_CLIENT_HOSTS` | empty | comma-separated hostnames; if set, only requests from those hosts' IPs are accepted (compose sets `lad-nginx`). Empty means no restriction |

## API

All routes are under `/chat`, except chat listing under `/app`.

| Method | Path | Notes |
|---|---|---|
| `POST` | `/chat/create` | `{title?, mode: "chat" \| "agent"}` |
| `GET` | `/app/` | list all chats |
| `GET` | `/chat/{chat_id}` | one chat (the frontend uses it to learn an existing chat's mode) |
| `GET` | `/chat/messages?chat_id=` | full message history |
| `PATCH` | `/chat/title` | `{chat_id, title}` |
| `DELETE` | `/chat/{chat_id}` | also removes the chat's sandbox directory |
| `POST` | `/chat/msg/stream` | **multipart**: `chat_id`, `msg`, optional `files[]` (agent chats only, otherwise `400`); responds with an SSE stream |
| `POST` | `/chat/msg/retry` | `{chat_id}`: regenerates a reply for the last unanswered turn |

Errors: `403` for requests that don't come from an allowed client, `503` while
the database is starting.

`/chat/{chat_id}` is registered *after* `/chat/messages` in `routes/chat.py`:
Starlette matches routes in registration order, so a `{chat_id}` route
registered first would swallow the literal `/chat/messages` path. Any new
literal route under `/chat/` must be registered before it.

### SSE protocol

`/chat/msg/stream` and `/chat/msg/retry` respond with `text/event-stream`.
Events: `chunk` (a piece of the reply), `tool_call` / `tool_result` (one per
tool invocation, the full persisted message), `done` (final assistant message),
`error`.

Tool calls and results arrive as they happen. The final answer, however, is
generated in full by Ollama (`stream: false`) and then sent as 40-character
`chunk` events, so the first text appears after generation finishes.

## Chat modes and the agent loop

- **`chat`**: `OLLAMA_MODEL`, tools `web_search` and `recall_memory`
- **`agent`**: `OLLAMA_AGENT_MODEL`, tools `run_command`, `web_search` and
  `recall_memory`; framed as a general-purpose coding agent

Both run through the same loop (`helpers/agent.py::_run_tool_turn`),
parameterized by system prompt, model, allowed tools and iteration cap.

- Tool definitions are discovered once per process by launching each MCP
  server, then cached; adding or changing a tool requires restarting the API.
- A tool call outside the mode's allowed set is not dispatched: the model gets
  an error result instead of being trusted to follow its tool list.
- On the final iteration no tools are offered, and any tool calls the model
  emits anyway are ignored, so a turn always ends with an answer or an `error`.
- Tool failures are returned to the model as error text rather than aborting
  the turn.
- Tool output is truncated to `MAX_TOOL_OUTPUT_CHARS`, keeping the beginning
  and end.

Tool calls get the chat's ID through a subprocess environment variable
(`LAD_CHAT_ID`), never as a model-visible parameter, so the model can't pass a
different chat to a tool. This is not a boundary inside `run_command`, where a
shell command can still read other chats' directories (see the
[sandbox README](../sandbox/README.md)).

## Tools (MCP servers)

Each tool is a standalone MCP server under `tools/`, launched as its own
subprocess for every call (configured via `MCP_SERVERS`):

- **`run_command`** (`sandbox_server.py`): proxies to the sandbox
  container's `/execute` endpoint; agent mode only
- **`web_search`** (`web_search_server.py`): Tavily search; `max_results` is
  clamped to 3-10
- **`recall_memory`** (`memory_server.py`): semantic search over other chats'
  embedded summaries; `top_k` is clamped to 3-10

### Memory

Cross-chat memory is the only semantic-search feature. Once a chat's
unsummarized tail reaches `SUMMARY_THRESHOLD`, older messages are folded into a
rolling `ConversationSummary` (one row per chat). A summary never separates a
tool result from the tool call that produced it, and is generated with the
chat's own model. The summary is embedded with `OLLAMA_EMBED_MODEL`, and
`recall_memory` runs an exact pgvector cosine-distance scan over those
embeddings, excluding the current chat. There is no ANN index.

Brand-new or short chats aren't recallable yet: a summary only exists once a
chat has accumulated enough messages.

## File uploads

Agent chats can attach up to 10 files per message, 20 MB each, with an
extension from an allowlist (source files, text and data formats, `.pdf`,
`.zip`; see `helpers/uploads.py`). Files are saved to
`chat_sandboxes/{chat_id}/`, bind-mounted into both the `api` and `sandbox`
containers, so there is no sync step. A file with the same name overwrites the
old one. There is no server-side extraction: the agent unzips archives itself
with `run_command`. Go, Rust and Java files can be uploaded and read, but the
sandbox has no compilers for them.

## Async design

Every layer is async: SQLAlchemy `AsyncSession`, the Ollama client, the MCP
client and the streaming generators. Things to know when changing it:

- Sessions use `expire_on_commit=False`, because `AsyncSession` can't lazy-load
  expired attributes. Don't `rollback()` objects you still need afterwards:
  rollback expires them regardless.
- A session holds a pooled connection while a transaction is open, so the
  code commits before slow LLM and tool calls.
- Blocking file work (saving uploads, deleting a chat's sandbox directory)
  runs through `asyncio.to_thread`.

## Logging

Logs are JSON lines on stdout (`core/logging.py`), with the traceback in a
`traceback` field for `logger.exception` calls.

## Testing

```bash
poetry run pytest tests/unit_tests          # fast, fully mocked
poetry run pytest tests/integration_tests   # real Postgres via testcontainers (needs Docker)
poetry run ruff check .
poetry run mypy .
```

Tests use pytest-asyncio in auto mode. The integration suite fakes the
embedding calls (autouse fixture in `tests/integration_tests/conftest.py`): it
tests against a real database, not a real Ollama instance.

## Scripts

`scripts/` holds standalone scripts you run against an already running stack
(`./start.sh`); they aren't part of the test suite. Both take `--base-url`
(default `http://localhost:8000/api`):

- `load_test_crud.py`: concurrent load test of the CRUD endpoints (create,
  list, messages, update, delete). None of these touch Ollama. `/chat/messages`
  is measured against empty chats, since creating messages requires the LLM.
- `profile_llm.py`: **profiling, not load testing**, for endpoints that touch
  the LLM. Part 1 times a few fixed, simple cases sequentially. Part 2 runs two
  agent chats solo and then concurrently to quantify the slowdown from the
  shared sandbox budget, and checks that the two chats' files don't overwrite
  each other in normal use (a correctness check, not a security test).

## Known limitations

- **One Ollama model loaded at a time** (when `start.sh` starts Ollama).
  Switching modes, or embedding a summary, reloads a model and adds latency to
  the next reply.
- **The sandbox is shared, and chats are separated by directory only.**
  Concurrent agent chats slow each other down, and a command can read other
  chats' files.
- **No authentication.** The API is only reachable through nginx on localhost;
  running the backend outside Docker applies no client restriction.
- **No migrations.** Schema changes require a database reset.
- **Tool discovery is cached** for the process lifetime.
- **Every tool call launches a subprocess**, which adds overhead per call.