import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import ApiErrorResponse
from app.core.request_context import request_id_var

logger = logging.getLogger("app.errors")


def _request_id() -> str | None:
    return request_id_var.get()


def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    rid = _request_id()
    payload = ApiErrorResponse(
        error={
            "code": "http_error",
            "message": str(exc.detail),
            "request_id": rid,
            "details": None,
        }
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = _request_id()
    payload = ApiErrorResponse(
        error={
            "code": "validation_error",
            "message": "Invalid request",
            "request_id": rid,
            "details": exc.errors(),
        }
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    logger.exception("Unhandled error request_id=%s", rid)
    payload = ApiErrorResponse(
        error={
            "code": "internal_error",
            "message": "Internal server error",
            "request_id": rid,
            "details": None,
        }
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


