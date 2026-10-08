import os

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from lad.core.db import connect_db, get_db_session
from lad.core.embeddings import embed_query
from lad.models.db import Chat, ConversationSummary

server = MCPServer("lad-memory")
MIN_TOP_K = 3
MAX_TOP_K = 10


@server.tool()
async def recall_memory(query: str, top_k: int = 5) -> str:
    top_k = min(max(top_k, MIN_TOP_K), MAX_TOP_K)
    current_chat_id = os.environ.get("LAD_CHAT_ID")
    query_embedding = await embed_query(query)

    statement = (
        select(ConversationSummary, Chat)
        .join(Chat, Chat.id == ConversationSummary.chat_id)
        .where(ConversationSummary.embedding.isnot(None))
    )

    if current_chat_id is not None:
        statement = statement.where(ConversationSummary.chat_id != int(current_chat_id))

    statement = statement.order_by(
        ConversationSummary.embedding.cosine_distance(query_embedding)
    ).limit(top_k)

    async with get_db_session() as db:
        rows = (await db.execute(statement)).all()

    if not rows:
        return "No relevant past conversations found."

    return "\n\n".join(
        f"# {chat.title} (chat {chat.id}, {chat.created_at:%Y-%m-%d})\n"
        f"{summary.content}"
        for summary, chat in rows
    )


if __name__ == "__main__":
    connect_db()
    server.run(transport="stdio")
