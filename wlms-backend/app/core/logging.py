import logging
from typing import Any

from app.core.request_context import request_id_var


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        return True


def configure_logging() -> None:
    """
    Minimal structured-ish logging:
    - adds request_id to records
    - uses a compact formatter
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid adding multiple handlers in reload
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        for h in root.handlers:
            h.addFilter(RequestIdFilter())
        return

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
        )
    )
    root.addHandler(handler)


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    if fields:
        logger.info("%s %s", message, " ".join(f"{k}={v}" for k, v in fields.items()))
    else:
        logger.info("%s", message)


