from sqlalchemy.orm import Session

from lad.models.db import Chat
from lad.schemas.chat import ChatResponse


def get_chats(db: Session) -> list[ChatResponse]:
    chats = db.query(Chat).order_by(Chat.created_at).all()

    return [
        ChatResponse.model_validate(chat)
        for chat in chats
    ]