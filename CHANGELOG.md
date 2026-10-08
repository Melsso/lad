# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

First version.

### Added

- Chat UI (React, TypeScript, Vite, Tailwind) with SSE replies, markdown, GFM
  and KaTeX rendering, chat rename and delete, retry of unanswered turns, and
  favicon states for processing and ready.
- Async FastAPI backend with SQLAlchemy and Postgres (pgvector) persistence.
- Two chat modes, fixed per chat: `chat` (lighter model; `web_search`,
  `recall_memory`) and `agent` (larger model; adds the sandboxed `run_command`
  tool and file uploads).
- MCP-based tool layer: each tool is its own stdio MCP server, with tool
  discovery cached per process and tool output truncated before it reaches the
  model.
- Rolling conversation summaries, embedded with pgvector for cross-chat
  `recall_memory`, that never split a tool call from its result.
- File uploads for agent chats, saved into the chat's sandbox directory and
  removed when the chat is deleted.
- Sandbox service with per-chat working directories, an offline coding
  toolchain (Python, Node, Ruby, PHP, gcc/cmake and common CLI tools), and
  process-group kill on timeout.
- Local inference through Ollama, with configurable chat, agent and embedding
  models.
- Unit and integration test suites for the backend, frontend and sandbox, with
  a CI workflow for each.
- `load_test_crud.py` and `profile_llm.py` scripts, and `start.sh` / `stop.sh`
  to run the whole stack.

### Security

- The API only accepts requests from nginx, so the sandbox can't call back into
  it.
- nginx and Postgres are published on loopback only.
- The sandbox runs on an internal network with no internet access, as a
  non-root user with all capabilities dropped, and with memory, CPU and process
  limits.