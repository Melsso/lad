import sys
from pathlib import Path

from lad.core.mcp import MCPClient, MCPServerConfig

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mcp_echo_server.py"


def _echo_client() -> MCPClient:
    return MCPClient(
        servers=[
            MCPServerConfig(
                name="echo", command=sys.executable, args=[str(FIXTURE_PATH)]
            )
        ]
    )


def test_list_tools_discovers_the_real_echo_server():
    client = _echo_client()

    tools = client.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "echo"
    assert "message" in tools[0].parameters["properties"]


def test_call_tool_round_trips_through_a_real_subprocess():
    client = _echo_client()
    client.list_tools()

    result = client.call_tool("echo", {"message": "hello world"})

    assert result == "echo: hello world"
