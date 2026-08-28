import logging
import sys
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }

        for field in (
            "request_id",
            "user_id",
            "path",
            "method",
            "status_code",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        if hasattr(record, "event"):
            log_record["event"] = record.event

        if hasattr(record, "status"):
            log_record["status"] = record.status

        if hasattr(record, "context"):
            log_record["context"] = record.context

        if hasattr(record, "error_type"):
            log_record["error_type"] = record.error_type

        if hasattr(record, "error_message"):
            log_record["error_message"] = record.error_message

        return json.dumps(log_record)


def setup_logging():

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("Lad")
    logger.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.propagate = False

    return logger
