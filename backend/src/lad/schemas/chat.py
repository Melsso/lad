from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
