import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lad.core.db import get_db
from lad.helpers.chat import (
    create_chat,
    get_chat_messages,
    process_chat_msg,
    update_chat_title,
)
from lad.schemas.chat import (
    ChatMessageResponse,
    ChatResponse,
    CreateChatRequest,
    SendMessageRequest,
    UpdateChatTitleRequest,
)

chat_router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("Lad")


@chat_router.post("/create", response_model=ChatResponse)
async def create_chat_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    chat_request: CreateChatRequest,
):
    try:
        title = chat_request.title.strip() if chat_request.title else "New Chat"
        if not title:
            title = "New Chat"

        chat = create_chat(db=db, title=title)

        db.commit()
        db.refresh(chat)

        return chat

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "lad_event",
            extra={
                "event": "http_request",
                "status": "internal_error",
                "status_code": 500,
                "path": request.url.path,
                "method": request.method,
                "context": {
                    "location": "create_chat_endpoint",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create chat",
        ) from exc


@chat_router.patch("/title", response_model=ChatResponse)
async def update_chat(
    request: Request,
    chat_request: UpdateChatTitleRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        title = chat_request.title.strip()
        if not title:
            raise HTTPException(
                status_code=400,
                detail="Chat title cannot be empty",
            )

        chat = update_chat_title(db=db, chat_id=chat_request.chat_id, title=title)
        if chat is None:
            raise HTTPException(
                status_code=404,
                detail="Chat not found",
            )

        db.commit()
        db.refresh(chat)

        return chat

    except HTTPException:
        raise

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "lad_event",
            extra={
                "event": "http_request",
                "status": "internal_error",
                "status_code": 500,
                "path": request.url.path,
                "method": request.method,
                "context": {
                    "location": "update_chat",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to update chat",
        ) from exc


@chat_router.get("/messages", response_model=list[ChatMessageResponse])
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
                    "location": "chat_messages",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc


@chat_router.post("/msg", response_model=ChatMessageResponse)
async def process_msg(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    chat_request: SendMessageRequest,
):
    try:
        return process_chat_msg(
            db=db, chat_id=chat_request.chat_id, msg=chat_request.msg
        )

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
                    "location": "process_msg",
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
                    "location": "process_msg",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "lad_event",
            extra={
                "event": "http_request",
                "status": "internal_error",
                "status_code": 500,
                "path": request.url.path,
                "method": request.method,
                "context": {
                    "location": "process_msg",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing message",
        ) from exc
