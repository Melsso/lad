from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class LLMTurn(BaseModel):
    content: str
    tool_calls: list[ToolCall] = []
