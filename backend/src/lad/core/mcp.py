import asyncio
import json
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from lad.schemas.config import conf
from lad.schemas.llm import ToolDefinition


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str]


def load_server_configs(raw: str) -> list[MCPServerConfig]:
    entries = json.loads(raw) if raw.strip() else []

    return [
        MCPServerConfig(
            name=entry["name"],
            command=entry["command"],
            args=entry.get("args", []),
        )
        for entry in entries
    ]


class MCPClient:
    def __init__(self, servers: list[MCPServerConfig]):
        self._servers = servers
        self._tool_owners: dict[str, MCPServerConfig] = {}

    def list_tools(self) -> list[ToolDefinition]:
        if not self._servers:
            return []

        return asyncio.run(self._list_tools_async())

    async def _list_tools_async(self) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []

        for server in self._servers:
            params = StdioServerParameters(command=server.command, args=server.args)

            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.list_tools()

                for tool in result.tools:
                    self._tool_owners[tool.name] = server
                    definitions.append(
                        ToolDefinition(
                            name=tool.name,
                            description=tool.description or "",
                            parameters=tool.input_schema,
                        )
                    )

        return definitions

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        server = self._tool_owners.get(name)

        if server is None:
            raise ValueError(f"Unknown MCP tool: {name}")

        return asyncio.run(self._call_tool_async(server, name, arguments))

    async def _call_tool_async(
        self, server: MCPServerConfig, name: str, arguments: dict[str, Any]
    ) -> str:
        params = StdioServerParameters(command=server.command, args=server.args)

        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, arguments)

            text = "\n".join(
                block.text for block in result.content if isinstance(block, TextContent)
            )

            if result.is_error:
                raise RuntimeError(text or f"{name} failed")

            return text


mcp_client = MCPClient(servers=load_server_configs(conf.MCP_SERVERS))
