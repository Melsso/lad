import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lad.core.db import get_db
from lad.helpers.chat import (
    create_chat,
    delete_chat,
    get_chat,
    get_chat_messages,
    stream_chat_msg,
    stream_chat_retry,
    update_chat_title,
)
from lad.schemas.chat import (
    ChatMessageResponse,
    ChatResponse,
    CreateChatRequest,
    RetryMessageRequest,
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


@chat_router.delete("/{chat_id}")
async def delete_chat_endpoint(
    request: Request,
    chat_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        deleted = delete_chat(db=db, chat_id=chat_id)
        db.commit()
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
                    "location": "delete_chat_endpoint",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete chat",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_id} does not exist",
        )

    return {"status": "deleted"}


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


@chat_router.post("/msg/stream")
async def stream_msg(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    chat_request: SendMessageRequest,
):
    try:
        chat = get_chat(db=db, chat_id=chat_request.chat_id)
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
                    "location": "stream_msg",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {chat_request.chat_id} does not exist",
        )

    return StreamingResponse(
        stream_chat_msg(chat_id=chat_request.chat_id, msg=chat_request.msg),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post("/msg/retry")
async def retry_msg(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    retry_request: RetryMessageRequest,
):
    try:
        chat = get_chat(db=db, chat_id=retry_request.chat_id)
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
                    "location": "retry_msg",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while processing message",
        ) from exc

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat {retry_request.chat_id} does not exist",
        )

    return StreamingResponse(
        stream_chat_retry(chat_id=retry_request.chat_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
