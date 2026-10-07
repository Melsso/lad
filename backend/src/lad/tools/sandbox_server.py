import os

import httpx
from mcp.server.mcpserver import MCPServer

from lad.schemas.config import conf

server = MCPServer("lad-sandbox")

DEFAULT_TIMEOUT_SECONDS = 60


@server.tool()
def run_command(command: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Runs a shell command inside an isolated sandbox scoped to this chat.
    Use this to write files, run builds, tests, or code. Files persist across
    calls within the same chat. The sandbox is offline with no credentials:
    nothing can be downloaded or installed (pip/npm/cargo installs fail).
    Available: python3 (pytest, mypy, ruff, numpy, pandas, requests, fastapi,
    flask, pypdf and more), node (typescript, tsx, prettier, eslint, vitest),
    go, rust/cargo, java, ruby, php, gcc/g++/make/cmake, git, jq, ripgrep,
    sqlite3, shellcheck, pdftotext, zip/unzip/7z."""
    chat_id = os.environ.get("LAD_CHAT_ID")

    if not chat_id:
        raise RuntimeError("No chat context available for sandbox execution")

    response = httpx.post(
        f"{conf.SANDBOX_URL}/execute",
        json={"chat_id": chat_id, "command": command, "timeout": timeout},
        timeout=timeout + 10,
    )
    response.raise_for_status()
    result = response.json()

    return (
        f"exit_code: {result['exit_code']}\n"
        f"stdout:\n{result['stdout']}\n"
        f"stderr:\n{result['stderr']}"
    )


if __name__ == "__main__":
    server.run(transport="stdio")
