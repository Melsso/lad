# LAD (Local AI Daemon)

A personal, locally-hosted ChatGPT/Claude-style chat app: FastAPI backend,
React frontend, Postgres, and Ollama for local LLM inference — no external
model API, everything runs on your own machine.

## Architecture

```
                      ┌─────────────┐
   browser  ───────▶  │    nginx    │  :8000
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
                                     over chat summaries)
                             │
                      ┌──────▼──────┐
                      │   sandbox   │  isolated network,
                      │  container  │  no credentials,
                      └─────────────┘  capped resources

          api + sandbox both talk to a local Ollama
          instance on the host (not containerized)
```

- **frontend/** — React + TypeScript + Vite + Tailwind chat UI
- **backend/** — FastAPI + SQLAlchemy + Postgres, chat persistence,
  streaming replies, the MCP-based tool-calling agent layer
- **sandbox/** — isolated command-execution service backing the agent's
  `run_command` tool
- **infra/** — nginx config/Dockerfile, Postgres (pgvector) Dockerfile

Each has its own README with real detail:
[backend](backend/README.md) · [frontend](frontend/README.md) ·
[sandbox](sandbox/README.md)

## Chat modes

Every chat is either:

- **chat mode** — a lighter model, for ordinary conversation. Has two
  tools available: `web_search` and `recall_memory` (semantic search over
  your *other* chats' summaries — lets it recall things you discussed
  elsewhere without you restating them).
- **agent mode** — a larger model, framed as a general-purpose coding
  agent (not specific to this project). Has those same two tools plus
  `run_command` — a real sandboxed shell, so it can read/write files, run
  code, and explore anything you hand it, including an uploaded zip you
  tell it is a codebase.

Mode is fixed per chat, chosen when you create it.

## Prerequisites

- **Docker** + **Docker Compose**
- **[Ollama](https://ollama.com)** installed on the host (not
  containerized — `start.sh` runs `ollama serve`/`ollama pull` directly).
  Needs enough RAM for whichever chat/agent/embedding models you configure
  (defaults: `qwen3:8b`, `gemma4:12b`, `embeddinggemma`).

## Quickstart

```bash
cp backend/.env.example backend/.env   # fill in TAVILY_API_KEY at minimum
./start.sh
```

`start.sh` will, in order: create the Docker network if missing, start (or
create) the Postgres container, start Ollama if it isn't already running
and pull whichever models your `.env` names, then build and bring up the
rest of the stack (nginx, api, sandbox) via `docker compose up --build`.

Once it's up, the app is at **http://localhost:8000**.

## A note on running everything on one local machine

This is built to run entirely on a single personal machine, which shapes
a few things worth knowing going in:

- **Only one Ollama model is kept loaded at a time**
  (`OLLAMA_MAX_LOADED_MODELS=1`, set by `start.sh`). Switching between a
  chat-mode chat and an agent-mode chat forces a model reload, which shows
  up as extra latency on the first message after the switch.
- **The sandbox is one shared container, not one per chat** — a fixed
  `0.5 cpu` / `512m` budget split across every agent-mode chat currently
  running a command. Isolation between chats is directory-based and holds
  up under concurrency (each `run_command` call is its own OS subprocess
  with a chat-scoped working directory), but performance isn't isolated —
  two agent-mode chats running commands at the same time will both slow
  down.
- **Load-testing this app doesn't look like load-testing a normal web
  service.** The CRUD endpoints (create/list/delete a chat, fetch
  history) are ordinary DB operations and take concurrency fine. Anything
  that generates a reply is bottlenecked by local model inference, not by
  this codebase — see `backend/scripts/profile_llm.py`'s docstring for
  why that script profiles rather than load-tests.

## Development

No migration tooling — schema changes require a DB reset. Each
sub-project has its own test suite and CI workflow
(`.github/workflows/*.yml`); see the sub-project READMEs for exact
commands.