import os

from mcp.server.mcpserver import MCPServer

from lad.core.db import connect_db, get_db_session
from lad.core.embeddings import embed_query
from lad.models.db import Chat, ConversationSummary

server = MCPServer("lad-memory")


@server.tool()
def recall_memory(query: str, top_k: int = 5) -> str:
    """Searches past conversations (not this one) for content relevant to
    the query. Use this to recall facts, decisions, or context from earlier
    chats that the user refers back to but hasn't restated here."""
    top_k = max(top_k, 3)
    current_chat_id = os.environ.get("LAD_CHAT_ID")
    query_embedding = embed_query(query)

    with get_db_session() as db:
        query_builder = (
            db.query(ConversationSummary, Chat)
            .join(Chat, Chat.id == ConversationSummary.chat_id)
            .filter(ConversationSummary.embedding.isnot(None))
        )

        if current_chat_id is not None:
            query_builder = query_builder.filter(
                ConversationSummary.chat_id != int(current_chat_id)
            )

        results = (
            query_builder.order_by(
                ConversationSummary.embedding.cosine_distance(query_embedding)
            )
            .limit(top_k)
            .all()
        )

        if not results:
            return "No relevant past conversations found."

        return "\n\n".join(
            f"# {chat.title} (chat {chat.id}, {chat.created_at:%Y-%m-%d})\n"
            f"{summary.content}"
            for summary, chat in results
        )


if __name__ == "__main__":
    connect_db()
    server.run(transport="stdio")
