from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_admin_or_supervisor
from app.core.rbac import ROLE_CLIENT_USER
from app.core.security import hash_password
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.user import UserCreate, UserMeUpdate, UserOut
from app.services.audit_service import audit_log

router = APIRouter(prefix="/users", tags=["users"])


def _to_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        tenant_id=u.tenant_id,
        client_id=u.client_id,
        email=u.email,
        username=u.username,
        full_name=u.full_name,
        role=u.role,
        language_pref=u.language_pref,
        is_active=u.is_active,
    )


def _suggest_username(email: str) -> str:
    base = (email.split("@", 1)[0] if "@" in email else email).strip().lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch in {"_", ".", "-"})
    return (base[:64] or "user")


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_admin_or_supervisor)) -> list[UserOut]:
    users = db.scalars(select(User).where(User.tenant_id == user.tenant_id)).all()
    return [_to_out(u) for u in users]


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> UserOut:
    return _to_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserMeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    before = _to_out(user).model_dump()
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.language_pref is not None:
        if payload.language_pref not in ("en", "bs", "de"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid language")
        user.language_pref = payload.language_pref

    db.add(user)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="users.me.update",
        entity_type="User",
        entity_id=str(user.id),
        before=before,
        after=_to_out(user).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
) -> UserOut:
    # If creating a client user, must specify client_id and it must belong to the same tenant.
    if payload.role == ROLE_CLIENT_USER:
        if payload.client_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="client_id required for CLIENT_USER")
        client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
        if client is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
    else:
        # Non-client users must not be bound to a client_id
        if payload.client_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="client_id not allowed for this role")

    new_user = User(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        email=payload.email,
        username=(payload.username.strip()[:64] if payload.username and payload.username.strip() else _suggest_username(payload.email)),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        language_pref=payload.language_pref,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.flush()
        audit_log(
            db,
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            action="users.create",
            entity_type="User",
            entity_id=str(new_user.id),
            after=_to_out(new_user).model_dump(),
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists")
    db.refresh(new_user)
    return _to_out(new_user)


