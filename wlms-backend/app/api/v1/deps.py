import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import ROLE_CLIENT_USER, require_roles
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token tenant")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    try:
        user_uuid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.scalar(select(User).where(User.id == user_uuid, User.tenant_id == tenant_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User disabled or not found")

    token_version = payload.get("token_version")
    if token_version is None or int(token_version) != int(user.token_version):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Optional defensive check: if token includes client_id, it must match DB.
    token_client_id = payload.get("client_id")
    if token_client_id is not None and user.client_id is not None and str(user.client_id) != str(token_client_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token client")

    return user


def require_admin_or_supervisor(user: User = Depends(get_current_user)) -> User:
    try:
        require_roles(user.role, ["WAREHOUSE_ADMIN", "WAREHOUSE_SUPERVISOR"])
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return user


def require_warehouse_staff(user: User = Depends(get_current_user)) -> User:
    try:
        require_roles(user.role, ["WAREHOUSE_ADMIN", "WAREHOUSE_SUPERVISOR", "WAREHOUSE_WORKER", "DRIVER"])
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return user


def require_any_authenticated(user: User = Depends(get_current_user)) -> User:
    return user


def is_client_user(user: User) -> bool:
    return user.role == ROLE_CLIENT_USER or user.client_id is not None


