import logging

from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("Lad")


def db_http_error(
    request: Request, location: str, exc: SQLAlchemyError, detail: str
) -> HTTPException:
    logger.exception(
        "lad_event",
        extra={
            "event": "http_request",
            "status": "internal_error",
            "status_code": 500,
            "path": request.url.path,
            "method": request.method,
            "context": {
                "location": location,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        },
    )

    return HTTPException(status_code=500, detail=detail)
