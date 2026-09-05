from mcp.server.mcpserver import MCPServer

server = MCPServer("lad-echo")


@server.tool()
def echo(message: str) -> str:
    """Echoes back the provided message, prefixed with 'echo: '"""
    return f"echo: {message}"


if __name__ == "__main__":
    server.run(transport="stdio")
