import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.auth_tokens import PasswordResetToken
from app.models.user import User
from app.core.rbac import ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    VerifySupervisorRequest,
)
from app.services.notification_service import queue_password_reset_email
from app.services.audit_service import audit_log
from app.core.rate_limit import rate_limit
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        tenant_id=user.tenant_id,
        client_id=str(user.client_id) if user.client_id else None,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        language_pref=user.language_pref,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), request: Request | None = None) -> TokenResponse:
    if request and request.client:
        rate_limit(key=f"auth:login:{request.client.host}", limit=20, window_seconds=60)
    ident = payload.username.strip()
    # Accept either username or email as "username"
    user = db.scalar(select(User).where((User.username == ident) | (User.email == ident)))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
        client_id=str(user.client_id) if user.client_id else None,
        token_version=int(user.token_version),
    )
    refresh = create_refresh_token(user_id=str(user.id), tenant_id=user.tenant_id, token_version=int(user.token_version))

    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db), request: Request | None = None) -> TokenResponse:
    if request and request.client:
        rate_limit(key=f"auth:refresh:{request.client.host}", limit=60, window_seconds=60)
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if decoded.get("typ") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    sub = decoded.get("sub")
    tenant_id = decoded.get("tenant_id")
    if not sub or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user_uuid = uuid.UUID(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.scalar(select(User).where(User.id == user_uuid, User.tenant_id == tenant_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User disabled or not found")

    token_version = decoded.get("token_version")
    if token_version is None or int(token_version) != int(user.token_version):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
        client_id=str(user.client_id) if user.client_id else None,
        token_version=int(user.token_version),
    )
    new_refresh = create_refresh_token(user_id=str(user.id), tenant_id=user.tenant_id, token_version=int(user.token_version))
    return TokenResponse(access_token=access, refresh_token=new_refresh, user=_user_out(user))


@router.post("/logout")
def logout(db: Session = Depends(get_db), user: User = Depends(get_current_user), request: Request | None = None) -> dict[str, str]:
    # Increment token_version to invalidate existing access+refresh tokens.
    user.token_version = int(user.token_version) + 1
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="auth.logout",
        entity_type="User",
        entity_id=str(user.id),
        after={"token_version": int(user.token_version)},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db), request: Request | None = None) -> dict[str, str]:
    if request and request.client:
        rate_limit(key=f"auth:forgot:{request.client.host}", limit=10, window_seconds=60)
    # Always return OK to prevent account enumeration
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        return {"status": "ok"}

    token = uuid.uuid4().hex
    from datetime import datetime, timedelta, timezone

    pr = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        used_at=None,
    )
    db.add(pr)
    queue_password_reset_email(db, tenant_id=user.tenant_id, to_email=user.email, token=token, language=user.language_pref)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="auth.forgot_password",
        entity_type="User",
        entity_id=str(user.id),
        after={"email": user.email},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db), request: Request | None = None) -> dict[str, str]:
    if request and request.client:
        rate_limit(key=f"auth:reset:{request.client.host}", limit=10, window_seconds=60)
    from datetime import datetime, timezone

    pr = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token == payload.token))
    if pr is None or pr.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if pr.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    user = db.scalar(select(User).where(User.id == pr.user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user.password_hash = hash_password(payload.new_password)
    pr.used_at = datetime.now(timezone.utc)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="auth.reset_password",
        entity_type="User",
        entity_id=str(user.id),
        after={"status": "password_reset"},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/verify-supervisor")
def verify_supervisor(
    payload: VerifySupervisorRequest,
    db: Session = Depends(get_db),
    request: Request | None = None,
) -> dict[str, str]:
    if request and request.client:
        rate_limit(key=f"auth:verify_supervisor:{request.client.host}", limit=10, window_seconds=60)

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.role not in {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="auth.verify_supervisor",
        entity_type="User",
        entity_id=str(user.id),
        after={"status": "ok"},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


