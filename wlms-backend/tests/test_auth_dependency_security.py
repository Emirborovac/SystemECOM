import uuid

import jwt
import pytest
from fastapi import HTTPException

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.models.user import User


class _Creds:
    def __init__(self, token: str):
        self.credentials = token


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeSession:
    """
    Minimal SQLAlchemy Session stub.
    - scalar(select(User)...): returns user if query contains matching id+tenant_id
    """

    def __init__(self, *, user: User):
        self.user = user
        self.last_stmt = None

    def scalar(self, stmt):
        self.last_stmt = stmt
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Require tenant scoping and user id scoping in the WHERE clause.
        if "users.tenant_id" not in compiled:
            return None
        if str(self.user.tenant_id) not in compiled:
            return None
        if str(self.user.id) not in compiled:
            return None
        return self.user


def _make_user(*, tenant_id: int, client_id: uuid.UUID | None) -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        email="u@example.com",
        password_hash="x",
        full_name="U",
        role="WAREHOUSE_ADMIN",
        language_pref="en",
        token_version=0,
        is_active=True,
    )


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def test_get_current_user_rejects_missing_tenant_id():
    user = _make_user(tenant_id=1, client_id=None)
    db = FakeSession(user=user)
    token = _encode({"sub": str(user.id), "typ": "access", "token_version": 0})
    with pytest.raises(HTTPException) as e:
        get_current_user(db=db, creds=_Creds(token))
    assert e.value.status_code == 401


def test_get_current_user_rejects_tenant_mismatch():
    user = _make_user(tenant_id=1, client_id=None)
    db = FakeSession(user=user)
    token = _encode(
        {"sub": str(user.id), "typ": "access", "tenant_id": 999, "role": "WAREHOUSE_ADMIN", "client_id": None, "token_version": 0}
    )
    with pytest.raises(HTTPException) as e:
        get_current_user(db=db, creds=_Creds(token))
    assert e.value.status_code == 401


def test_get_current_user_rejects_client_mismatch_when_present():
    client_id = uuid.uuid4()
    user = _make_user(tenant_id=1, client_id=client_id)
    db = FakeSession(user=user)
    token = _encode(
        {
            "sub": str(user.id),
            "typ": "access",
            "tenant_id": 1,
            "role": "CLIENT_USER",
            "client_id": str(uuid.uuid4()),
            "token_version": 0,
        }
    )
    with pytest.raises(HTTPException) as e:
        get_current_user(db=db, creds=_Creds(token))
    assert e.value.status_code == 401


