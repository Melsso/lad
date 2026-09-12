import os

import httpx
from mcp.server.mcpserver import MCPServer

from lad.schemas.config import conf

server = MCPServer("lad-sandbox")

DEFAULT_TIMEOUT_SECONDS = 60


@server.tool()
def run_command(command: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Runs a shell command inside an isolated sandbox scoped to this chat.
    Use this to write files, install packages, run builds, or execute code
    while working on a task. Files persist across calls within the same
    chat. The sandbox has no credentials and cannot reach anything but the
    public internet — do not expect access to any real services."""
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
