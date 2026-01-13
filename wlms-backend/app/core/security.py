from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def create_access_token(*, user_id: str, tenant_id: int, role: str, client_id: str | None, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expires_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "typ": "access",
        "tenant_id": tenant_id,
        "role": role,
        "client_id": client_id,
        "token_version": int(token_version),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return _encode(payload)


def create_refresh_token(*, user_id: str, tenant_id: int, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.refresh_token_expires_days)
    payload: dict[str, Any] = {
        "sub": user_id,
        "typ": "refresh",
        "tenant_id": tenant_id,
        "token_version": int(token_version),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return _encode(payload)


def decode_token(token: str) -> dict[str, Any]:
    return _decode(token)


