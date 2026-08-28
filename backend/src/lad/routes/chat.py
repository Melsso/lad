import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lad.core.db import get_db
from lad.helpers.chat import get_chat_messages, process_chat_msg
from lad.schemas.chat import ChatMessageResponse, SendMessageRequest

chat_router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("Lad")


@chat_router.get("/", response_model=list[ChatMessageResponse])
async def chat_messages(
    request: Request, db: Annotated[Session, Depends(get_db)], chat_id: int
):
    try:
        return get_chat_messages(db=db, chat_id=chat_id)
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
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc


@chat_router.post("/msg-resp", response_model=ChatMessageResponse)
async def process_msg(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    send_msg: SendMessageRequest,
):
    try:
        return process_chat_msg(db=db, chat_id=send_msg.chat_id, msg=send_msg.msg)

    except ValueError as exc:
        logger.exception(
            "lad_event",
            extra={
                "event": "http_request",
                "status": "client_error",
                "status_code": 404,
                "path": request.url.path,
                "method": request.method,
                "context": {
                    "location": "general_exception_handler",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

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
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc
