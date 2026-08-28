import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lad.core.db import get_db
from lad.helpers.chat import get_chats
from lad.schemas.chat import ChatResponse

app_router = APIRouter(prefix="/app", tags=["app"])
logger = logging.getLogger("Lad")


@app_router.get("/", response_model=list[ChatResponse])
async def session_status(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return get_chats(db=db)
    except SQLAlchemyError as exc:
        logger.exception(
            "lad_event",
            extra={
                "event": "http_request",
                "status": "internal_error",
                "status_code": 500,
                "path": request.url.path,
                "method": request.method,
                "context": {
                    "location": "general_exception_handler",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        return []
