# LAD (Local AI Daemon)

A personal, locally hosted ChatGPT/Claude-style chat app: FastAPI backend,
React frontend, Postgres with pgvector, and Ollama for local LLM inference.
There is no external LLM API: inference runs on your machine, and the only
outbound request is the optional Tavily web search.

## Architecture

```
                      ┌─────────────┐
   browser  ───────▶  │    nginx    │  127.0.0.1:8000
                      │  (static +  │
                      │  /api proxy)│
                      └──────┬──────┘
                             │
                      ┌──────▼─────┐        ┌──────────────┐
                      │     API    │  ───▶  │   Postgres   │
                      │  (FastAPI) │        │  + pgvector  │
                      └──────┬─────┘        └──────────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
          run_command   web_search  recall_memory
          (sandbox svc)  (Tavily)   (pgvector search
                 │                   over chat summaries)
          ┌──────▼──────┐
          │   sandbox   │  internal network, offline,
          │  container  │  no credentials, capped
          └─────────────┘  resources

      the API talks to a local Ollama instance on the host
      (not containerized)
```

- **frontend/**: React + TypeScript + Vite + Tailwind chat UI
- **backend/**: async FastAPI + SQLAlchemy + Postgres; chat persistence, SSE
  replies, and the MCP-based tool-calling agent layer
- **sandbox/**: isolated, offline command-execution service behind the
  agent's `run_command` tool
- **infra/**: nginx config and Dockerfile, Postgres (pgvector) Dockerfile and
  env example

Each has its own README: [backend](backend/README.md) ·
[frontend](frontend/README.md) · [sandbox](sandbox/README.md)

## Chat modes

Every chat is either:

- **chat mode**: a lighter model for ordinary conversation. Tools:
  `web_search` and `recall_memory` (semantic search over your *other* chats'
  summaries).
- **agent mode**: a larger model, framed as a general-purpose coding agent.
  Adds `run_command`, a sandboxed shell for reading and writing files and
  running code, including an uploaded zip you tell it is a codebase. File
  uploads are only available in this mode.

The mode is fixed per chat and chosen when you create it.

## Prerequisites

- **Docker** and **Docker Compose**
- **[Ollama](https://ollama.com)** installed on the host (not containerized).
  You need enough RAM for the models you configure (defaults: `qwen3:8b`,
  `gemma4:12b`, `embeddinggemma`).

Developed on macOS with Docker Desktop. On Linux, containers reach the host's
Ollama through `host.docker.internal` (mapped via `host-gateway` in the compose
file), so Ollama must listen on an address the Docker bridge can reach, for
example `OLLAMA_HOST=0.0.0.0` for the Ollama process.

## Quickstart

```bash
cp backend/env_example backend/.env      # set TAVILY_API_KEY at minimum
cp infra/.db_env.example infra/.db_env   # credentials must match backend/.env
./start.sh
```

`start.sh` creates the Docker network if missing, starts (or creates) the
Postgres container, starts Ollama if it isn't running and pulls the models
named in your `.env`, then builds and starts nginx, the API and the sandbox with
`docker compose up --build -d`. The first start downloads the models.

Open **http://localhost:8000**. Stop everything with `./stop.sh`.

## Security model

LAD has no authentication and is meant for a single local user.

- nginx and Postgres are published on `127.0.0.1` only. Don't expose them.
- The API only accepts requests that come from nginx (`ALLOWED_CLIENT_HOSTS`),
  so the sandbox can't call back into it.
- The sandbox is on an internal Docker network with no internet and no route to
  the host, holds no credentials, runs as a non-root user with all
  capabilities dropped, and has CPU, memory and process limits.
- Chats are separated inside the sandbox by working directory only: a command
  in one chat can read another chat's directory. This prevents accidental
  overlap, not a deliberate command.
- The agent runs model-written commands, and what it reads (web search results,
  uploaded files) can influence it. The offline, credential-free sandbox limits
  the damage but doesn't remove the risk.
- The default Postgres credentials are for local development. Change them in
  both env files if the machine is shared.

## Running everything on one machine

- **Only one Ollama model is kept loaded at a time**
  (`OLLAMA_MAX_LOADED_MODELS=1`, set by `start.sh` only when it starts Ollama
  itself). Switching between a chat-mode and an agent-mode chat, or a summary
  being embedded, reloads a model, which shows up as extra latency on the next
  reply.
- **The sandbox is one shared container**, not one per chat, with a fixed
  `0.5 cpu` / `1g` / 128-process budget split across every agent chat running a
  command. Two agent chats running commands at once slow each other down.
- **Replies are bound by local inference.** The CRUD endpoints are plain
  database operations; anything that generates a reply is bottlenecked by
  Ollama, not by this codebase. `backend/scripts/load_test_crud.py` exercises
  the CRUD endpoints, and `backend/scripts/profile_llm.py` profiles replies
  instead of load testing them.

## Development

There is no migration tooling: schema changes require a database reset. Each
sub-project has its own test suite and CI workflow (`.github/workflows/`); see
the sub-project READMEs for the exact commands.