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

    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: str | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    chat_id: int
    msg: str


class CreateChatRequest(BaseModel):
    title: str | None = None


class UpdateChatTitleRequest(BaseModel):
    chat_id: int
    title: str


class RetryMessageRequest(BaseModel):
    chat_id: int
