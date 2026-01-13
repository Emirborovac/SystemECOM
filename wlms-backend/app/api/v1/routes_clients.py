import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user, require_admin_or_supervisor
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.services.audit_service import audit_log

router = APIRouter(prefix="/clients", tags=["clients"])


def _to_out(c: Client) -> ClientOut:
    return ClientOut(
        id=str(c.id),
        tenant_id=c.tenant_id,
        name=c.name,
        address=c.address,
        tax_id=c.tax_id,
        billing_currency=c.billing_currency,
        vat_rate=float(c.vat_rate),
        preferred_language=c.preferred_language,
    )


@router.get("", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ClientOut]:
    stmt = select(Client).where(Client.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(Client.id == user.client_id)

    clients = db.scalars(stmt).all()
    return [_to_out(c) for c in clients]


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> ClientOut:
    c = Client(
        tenant_id=user.tenant_id,
        name=payload.name,
        address=payload.address,
        tax_id=payload.tax_id,
        billing_currency=payload.billing_currency,
        vat_rate=payload.vat_rate,
        preferred_language=payload.preferred_language,
    )
    db.add(c)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="clients.create",
        entity_type="Client",
        entity_id=str(c.id),
        after=_to_out(c).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientOut:
    try:
        cid = uuid.UUID(client_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    stmt = select(Client).where(Client.tenant_id == user.tenant_id, Client.id == cid)
    if is_client_user(user):
        if user.client_id is None or user.client_id != cid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    c = db.scalar(stmt)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return _to_out(c)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> ClientOut:
    try:
        cid = uuid.UUID(client_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    c = db.scalar(select(Client).where(Client.tenant_id == user.tenant_id, Client.id == cid))
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    before = _to_out(c).model_dump()
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="clients.update",
        entity_type="Client",
        entity_id=str(c.id),
        before=before,
        after=_to_out(c).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(c)
    return _to_out(c)


