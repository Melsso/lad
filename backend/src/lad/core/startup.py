import asyncio
import contextlib
from contextlib import asynccontextmanager

from lad.core.db import dispose_db, init_db


@asynccontextmanager
async def lifespan(app):
    init_task = asyncio.create_task(init_db())

    try:
        yield
    finally:
        init_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await init_task

        await dispose_db()
