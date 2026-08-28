from fastapi import FastAPI

from lad.core.logging import setup_logging
from lad.core.startup import register_startup_events

# TODO ADD ROUTES HERE IMPORT

def create_app() -> FastAPI:

    setup_logging()

    app = FastAPI(
        title="lad",
        description="Daily Assistant",
        version="1.0.0",
    )

    # TODO INCLUDE ROUTES HERE
    # app.include_router(ws_router, prefix="/api")

    register_startup_events(app)

    return app
