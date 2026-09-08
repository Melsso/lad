from mcp.server.mcpserver import MCPServer

from lad.core.db import connect_db, get_db_session
from lad.core.embeddings import embed_query
from lad.models.db import DocumentChunk

server = MCPServer("lad-rag")


@server.tool()
def search_docs(query: str, top_k: int = 8) -> str:
    """Searches the LAD codebase and architecture docs for content relevant
    to the query. Always returns several results to give enough context —
    do not lower top_k below the default."""
    top_k = max(top_k, 5)
    query_embedding = embed_query(query)

    with get_db_session() as db:
        results = (
            db.query(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
            .all()
        )

        if not results:
            return "No relevant documents found."

        return "\n\n".join(
            f"# {chunk.source_path} (chunk {chunk.chunk_index})\n{chunk.content}"
            for chunk in results
        )


if __name__ == "__main__":
    connect_db()
    server.run(transport="stdio")
