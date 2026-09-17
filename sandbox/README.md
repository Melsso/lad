# LAD sandbox

A small FastAPI service that executes shell commands on behalf of the
agent's `run_command` tool, isolated from the rest of the stack.

## What it does

One endpoint, `POST /execute`, backing the backend's `run_command` MCP
tool (`backend/src/lad/tools/sandbox_server.py`):

```json
{ "chat_id": "42", "command": "ls -la", "timeout": 60 }
```

```json
{ "exit_code": 0, "stdout": "...", "stderr": "", "timed_out": false }
```

Each request runs as its own `sh -c <command>` subprocess
(`subprocess.run`, `capture_output=True`), with `cwd` set to
`/data/chat_sandboxes/{chat_id}` — created on first use if it doesn't
exist. `timeout` defaults to 60 seconds and is capped at 300
(`MAX_TIMEOUT_SECONDS`); a timeout is reported back as
`{"exit_code": -1, "timed_out": true}` rather than raising.

## Isolation model

- **Network**: its own Docker network (`sandbox_network` in the root
  `docker-compose.yml`), reachable only from the `api` container — no
  general internet egress, no credentials.
- **Filesystem**: `/data/chat_sandboxes` is the same bind mount the `api`
  container writes uploaded files into
  (`chat_sandboxes/{chat_id}/` on the host) — one shared location, no sync
  step between the two containers. Isolation *between chats* is purely
  directory-based (each chat gets its own subdirectory); there is no
  per-chat container or process isolation.
- **Resources**: the whole container is capped at `mem_limit: 512m`,
  `cpus: 0.5` — shared across every chat currently using `run_command`,
  not per-chat. A second concurrent agent-mode chat will visibly slow the
  first one down; this has been verified not to cause cross-chat file
  contamination (see `backend/scripts/profile_llm.py`), just contention.
- **User**: the container runs commands as `sandboxuser`, a non-root user
  created in the image — not root, but not further locked down
  per-command beyond that.

## Running it

Not run standalone — it's built and started as part of the root
`docker-compose.yml` stack via `./start.sh`. See the
[root README](../README.md).

## Testing

```bash
poetry install
poetry run pytest tests/
poetry run ruff check .
poetry run mypy .
```