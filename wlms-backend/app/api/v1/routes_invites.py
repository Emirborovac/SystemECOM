import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin_or_supervisor
from app.core.rbac import ROLE_CLIENT_USER
from app.core.security import hash_password
from app.db.session import get_db
from app.models.auth_tokens import UserInvite
from app.models.client import Client
from app.models.user import User
from app.schemas.invite import InviteAccept, InviteCreate
from app.services.notification_service import queue_invite_email
from app.services.audit_service import audit_log

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/invite")
def invite_user(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> dict[str, str]:
    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    token = uuid.uuid4().hex
    inv = UserInvite(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        email=payload.email,
        role=ROLE_CLIENT_USER,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        accepted_at=None,
        created_by_user_id=user.id,
    )
    db.add(inv)
    queue_invite_email(db, tenant_id=user.tenant_id, to_email=payload.email, token=token, language=payload.language)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="users.invite",
        entity_type="UserInvite",
        entity_id=str(inv.id),
        after={"email": payload.email, "client_id": str(payload.client_id), "role": inv.role},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/invite/accept")
def accept_invite(payload: InviteAccept, db: Session = Depends(get_db), request: Request | None = None) -> dict[str, str]:
    inv = db.scalar(select(UserInvite).where(UserInvite.token == payload.token))
    if inv is None or inv.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    # Create user if not exists; otherwise attach to client if safe
    existing = db.scalar(select(User).where(User.email == inv.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    new_user = User(
        tenant_id=inv.tenant_id,
        client_id=inv.client_id,
        email=inv.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=ROLE_CLIENT_USER,
        language_pref=payload.language_pref,
        is_active=True,
    )
    db.add(new_user)
    inv.accepted_at = datetime.now(timezone.utc)
    db.flush()
    audit_log(
        db,
        tenant_id=inv.tenant_id,
        actor_user_id=None,
        action="users.invite.accept",
        entity_type="User",
        entity_id=str(new_user.id),
        after={
            "email": new_user.email,
            "client_id": str(new_user.client_id) if new_user.client_id else None,
            "role": new_user.role,
            "invite_id": str(inv.id),
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


