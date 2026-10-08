import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from lad.core.db import get_db
from lad.helpers.chat import (
    create_chat,
    delete_chat,
    generate_temporary_chat_title,
    get_chat,
    get_chat_messages,
    stream_chat_msg,
    stream_chat_retry,
    update_chat_title,
)
from lad.helpers.uploads import delete_chat_sandbox, save_uploads, validate_uploads
from lad.routes.errors import db_http_error
from lad.schemas.chat import (
    ChatMessageResponse,
    ChatResponse,
    CreateChatRequest,
    RetryMessageRequest,
    UpdateChatTitleRequest,
)

chat_router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@chat_router.post("/create", response_model=ChatResponse)
async def create_chat_endpoint(
    request: Request, db: DbSession, chat_request: CreateChatRequest
):
    try:
        title = (
            generate_temporary_chat_title(chat_request.title)
            if chat_request.title
            else "New Chat"
        )

        chat = await create_chat(db=db, title=title, mode=chat_request.mode)

        await db.commit()
        await db.refresh(chat)

        return chat

    except SQLAlchemyError as exc:
        await db.rollback()
        raise db_http_error(
            request, "create_chat_endpoint", exc, "Failed to create chat"
        ) from exc


@chat_router.patch("/title", response_model=ChatResponse)
async def update_chat(
    request: Request, chat_request: UpdateChatTitleRequest, db: DbSession
):
    try:
        title = chat_request.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Chat title cannot be empty")

        chat = await update_chat_title(db=db, chat_id=chat_request.chat_id, title=title)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        await db.commit()
        await db.refresh(chat)

        return chat

    except HTTPException:
        raise

    except SQLAlchemyError as exc:
        await db.rollback()
        raise db_http_error(
            request, "update_chat", exc, "Failed to update chat"
        ) from exc


@chat_router.delete("/{chat_id}")
async def delete_chat_endpoint(request: Request, chat_id: int, db: DbSession):
    try:
        deleted = await delete_chat(db=db, chat_id=chat_id)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise db_http_error(
            request, "delete_chat_endpoint", exc, "Failed to delete chat"
        ) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} does not exist")

    await asyncio.to_thread(delete_chat_sandbox, chat_id)

    return {"status": "deleted"}


@chat_router.get("/messages", response_model=list[ChatMessageResponse])
async def chat_messages(request: Request, db: DbSession, chat_id: int):
    try:
        return await get_chat_messages(db=db, chat_id=chat_id)
    except SQLAlchemyError as exc:
        raise db_http_error(
            request, "chat_messages", exc, "Failed to load messages"
        ) from exc


@chat_router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat_endpoint(request: Request, db: DbSession, chat_id: int):
    try:
        chat = await get_chat(db=db, chat_id=chat_id)
    except SQLAlchemyError as exc:
        raise db_http_error(
            request, "get_chat_endpoint", exc, "Failed to load chat"
        ) from exc

    if chat is None:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} does not exist")

    return chat


@chat_router.post("/msg/stream")
async def stream_msg(
    request: Request,
    db: DbSession,
    chat_id: Annotated[int, Form()],
    msg: Annotated[str, Form()],
):
    try:
        chat = await get_chat(db=db, chat_id=chat_id)
        await db.rollback()
    except SQLAlchemyError as exc:
        raise db_http_error(
            request, "stream_msg", exc, "Failed to start the reply"
        ) from exc

    if chat is None:
        raise HTTPException(status_code=404, detail=f"Chat {chat_id} does not exist")

    uploaded_files = [
        item
        for item in (await request.form()).getlist("files")
        if isinstance(item, UploadFile) and item.filename
    ]
    if uploaded_files and chat.mode != "agent":
        raise HTTPException(
            status_code=400, detail="File uploads are only available in agent mode"
        )
    try:
        validate_uploads(uploaded_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attached_filenames = (
        await asyncio.to_thread(save_uploads, chat_id=chat_id, files=uploaded_files)
        if uploaded_files
        else []
    )

    return StreamingResponse(
        stream_chat_msg(
            chat_id=chat_id, msg=msg, attached_filenames=attached_filenames
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@chat_router.post("/msg/retry")
async def retry_msg(
    request: Request, db: DbSession, retry_request: RetryMessageRequest
):
    try:
        chat = await get_chat(db=db, chat_id=retry_request.chat_id)
        await db.rollback()
    except SQLAlchemyError as exc:
        raise db_http_error(
            request, "retry_msg", exc, "Failed to start the reply"
        ) from exc

    if chat is None:
        raise HTTPException(
            status_code=404, detail=f"Chat {retry_request.chat_id} does not exist"
        )

    return StreamingResponse(
        stream_chat_retry(chat_id=retry_request.chat_id),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
