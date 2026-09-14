import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class ChatResponse(BaseModel):
    id: int
    title: str
    mode: str
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
    attached_files: list[str] | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("attached_files", mode="before")
    @classmethod
    def parse_attached_files(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value)
        return value


class CreateChatRequest(BaseModel):
    title: str | None = None
    mode: Literal["chat", "agent"] = "chat"


class UpdateChatTitleRequest(BaseModel):
    chat_id: int
    title: str


class RetryMessageRequest(BaseModel):
    chat_id: int
