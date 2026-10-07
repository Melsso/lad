from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from lad.core.db import get_db
from lad.helpers.chat import get_chats
from lad.routes.errors import db_http_error
from lad.schemas.chat import ChatResponse

app_router = APIRouter(prefix="/app", tags=["app"])


@app_router.get("/", response_model=list[ChatResponse])
async def chats(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        return await get_chats(db=db)
    except SQLAlchemyError as exc:
        raise db_http_error(request, "chats", exc, "Failed to load chats") from exc
