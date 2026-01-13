import uuid
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import request_id_var

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.time()
        try:
            response: Response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["x-request-id"] = rid
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "%s %s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            getattr(response, "status_code", "?"),
            duration_ms,
        )
        return response


