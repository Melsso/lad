from mcp.server.mcpserver import MCPServer

from lad.core.web_search import search_web

server = MCPServer("lad-web-search")

MIN_RESULTS = 3


@server.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Searches the live web for current information not available in the
    local codebase or docs. Use this for anything time-sensitive, external,
    or outside this project's own files."""
    max_results = max(max_results, MIN_RESULTS)
    results = search_web(query, max_results=max_results)

    if not results:
        return "No results found."

    return "\n\n".join(
        f"# {result.get('title', 'Untitled')}\n"
        f"{result.get('url', '')}\n"
        f"{result.get('content', '')}"
        for result in results
    )


if __name__ == "__main__":
    server.run(transport="stdio")
