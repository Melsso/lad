import asyncio
from contextlib import asynccontextmanager

from lad.core.db import init_db


@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(asyncio.to_thread(init_db))
    yield
