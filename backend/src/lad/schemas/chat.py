from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int

    content: str
    role: str

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    chat_id: int
    msg: str
