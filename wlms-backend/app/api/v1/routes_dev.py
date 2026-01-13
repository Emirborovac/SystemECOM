from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import ROLE_WAREHOUSE_ADMIN
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.dev import DevInitRequest

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/init")
def dev_init(payload: DevInitRequest, db: Session = Depends(get_db)) -> dict:
    if settings.env != "dev":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    existing_user = db.scalar(select(User.id).limit(1))
    existing_tenant = db.scalar(select(Tenant.id).limit(1))
    if existing_user is not None or existing_tenant is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already initialized")

    tenant = Tenant(name=payload.tenant_name)
    db.add(tenant)
    db.flush()  # to get tenant.id

    admin = User(
        tenant_id=tenant.id,
        client_id=None,
        email=payload.admin_email,
        password_hash=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        role=ROLE_WAREHOUSE_ADMIN,
        language_pref=payload.admin_language_pref,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    access = create_access_token(
        user_id=str(admin.id),
        tenant_id=admin.tenant_id,
        role=admin.role,
        client_id=None,
        token_version=int(admin.token_version),
    )
    refresh = create_refresh_token(user_id=str(admin.id), tenant_id=admin.tenant_id, token_version=int(admin.token_version))

    return {
        "tenant": {"id": tenant.id, "name": tenant.name},
        "admin_user": {"id": str(admin.id), "email": admin.email, "role": admin.role},
        "access_token": access,
        "refresh_token": refresh,
    }


