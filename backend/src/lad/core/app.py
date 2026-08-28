from fastapi import FastAPI

from lad.core.logging import setup_logging
from lad.core.startup import register_startup_events
from lad.routes.app import app_router
from lad.routes.chat import chat_router


def create_app() -> FastAPI:

    setup_logging()

    app = FastAPI(
        title="lad",
        description="Daily Assistant",
        version="1.0.0",
    )

    app.include_router(app_router)
    app.include_router(chat_router)

    register_startup_events(app)

    return app
