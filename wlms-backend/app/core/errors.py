from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    error: ApiError


