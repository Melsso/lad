from pathlib import Path

from pydantic import BaseModel, Field

MAX_TIMEOUT_SECONDS = 300
CHAT_SANDBOXES_ROOT = Path("/data/chat_sandboxes")


class ExecuteRequest(BaseModel):
    chat_id: str
    command: str
    timeout: int = Field(default=60, gt=0, le=MAX_TIMEOUT_SECONDS)


class ExecuteResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
