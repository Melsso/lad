# LAD sandbox

A small FastAPI service that executes shell commands on behalf of the agent's
`run_command` tool, isolated from the rest of the stack. The container is
offline and ships with a coding toolchain.

## What it does

`POST /execute` backs the backend's `run_command` MCP tool
(`backend/src/lad/tools/sandbox_server.py`):

```json
{ "chat_id": "42", "command": "ls -la", "timeout": 60 }
```

```json
{ "exit_code": 0, "stdout": "...", "stderr": "", "timed_out": false }
```

Each request runs as its own `sh -c <command>` process with `cwd` set to
`/data/chat_sandboxes/{chat_id}`, created on first use. `chat_id` must be
digits only. `timeout` defaults to 60 seconds and is capped at 300. On timeout
the whole process group is killed (background children included) and the
response is `{"exit_code": -1, "timed_out": true}` with the output captured so
far. `GET /health` returns `{"status": "ok"}` and is used by the compose
healthcheck.

## Toolchain

The sandbox has no network at runtime, so nothing can be installed (`pip` and
`npm` fail immediately). Everything is baked into the image:

- **Python 3** with pytest, pytest-cov, pytest-asyncio, pytest-mock,
  hypothesis, mypy, ruff, black, requests, httpx, fastapi, uvicorn, flask,
  pydantic, sqlalchemy, numpy, pandas, scipy, matplotlib, openpyxl, pyyaml,
  tomli-w, lxml, beautifulsoup4, jinja2, pypdf, pdfplumber, markdown, click,
  typer, rich, python-dotenv (see `agent-requirements.txt`)
- **Node 22** with typescript, tsx, prettier, eslint and vitest installed
  globally
- **Ruby** and **PHP** (CLI)
- **gcc/g++, make, cmake**
- **git, jq, ripgrep, tree, file, sqlite3, shellcheck, xmllint, pdftotext**
- **zip, unzip, 7z**

The service itself runs from its own virtualenv (`/opt/app-venv`), separate
from the Python the agent uses, so agent packages and service dependencies
can't conflict.

## Isolation model

- **Network**: `sandbox-network` is `internal: true` in the root
  `docker-compose.yml`, so the container has no internet access and no route to
  the host or LAN. Its only other member is `api`, which rejects any request
  that doesn't come from nginx (`ALLOWED_CLIENT_HOSTS`), so commands can't call
  back into the API.
- **Filesystem**: `/data/chat_sandboxes` is the same bind mount the `api`
  container writes uploaded files into (`chat_sandboxes/{chat_id}/` on the
  host), so there is no sync step. Separation between chats is by working
  directory only: it prevents accidental overlap, not a deliberate command
  reading another chat's directory.
- **Resources**: `mem_limit: 1g`, `cpus: 0.5`, `pids_limit: 128`, all Linux
  capabilities dropped, `no-new-privileges`. These are shared across every chat
  using `run_command`, not per chat, so a second concurrent agent chat will
  slow the first.
- **User**: commands run as `sandboxuser` (uid 1001), not root.

## Running it

It isn't run standalone: it is built and started by the root
`docker-compose.yml` through `./start.sh`. See the
[root README](../README.md).

## Testing

```bash
poetry install
poetry run pytest tests/
poetry run ruff check .
poetry run mypy .
```