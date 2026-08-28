import asyncio

from lad.core.db import init_db


def register_startup_events(app):

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(asyncio.to_thread(init_db))
