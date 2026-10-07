import asyncio
import socket

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lad.core.logging import setup_logging
from lad.core.startup import lifespan
from lad.routes.app import app_router
from lad.routes.chat import chat_router
from lad.schemas.config import conf


async def _resolve(host: str) -> set[str]:
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        return set()

    return {str(info[4][0]) for info in infos}


def _restrict_clients(app: FastAPI) -> None:
    allowed_hosts = [
        host.strip() for host in conf.ALLOWED_CLIENT_HOSTS.split(",") if host.strip()
    ]

    if not allowed_hosts:
        return

    @app.middleware("http")
    async def only_allowed_clients(request: Request, call_next):
        client_ip = request.client.host if request.client else None
        allowed: set[str] = set()

        for host in allowed_hosts:
            allowed |= await _resolve(host)

        if client_ip not in allowed:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)

        return await call_next(request)


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="lad",
        description="Local AI Daemon",
        version="0.1.0",
        lifespan=lifespan,
    )

    _restrict_clients(app)

    app.include_router(app_router)
    app.include_router(chat_router)

    return app
