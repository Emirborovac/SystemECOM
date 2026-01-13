import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user, require_warehouse_staff
from app.core.config import settings
from app.db.session import get_db
from app.models.client import Client
from app.models.location import Location
from app.models.product import Product
from app.models.return_ import Return, ReturnLine
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.file import File
from app.schemas.return_ import ReturnCreate, ReturnOut, ReturnScanLine
from app.services.document_service import render_return_pdf
from app.services.inventory_service import LedgerCreate, add_ledger_and_apply_on_hand
from app.services.storage_service import save_bytes, load_bytes
from app.services.audit_service import audit_log

router = APIRouter(prefix="/returns", tags=["returns"])


def _to_out(r: Return) -> ReturnOut:
    return ReturnOut(
        id=r.id,
        tenant_id=r.tenant_id,
        client_id=r.client_id,
        warehouse_id=r.warehouse_id,
        status=r.status,
        notes=r.notes,
    )


@router.get("", response_model=list[ReturnOut])
def list_returns(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ReturnOut]:
    stmt = select(Return).where(Return.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(Return.client_id == user.client_id)
    items = db.scalars(stmt).all()
    return [_to_out(r) for r in items]


@router.post("", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def create_return(
    payload: ReturnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> ReturnOut:
    if is_client_user(user):
        if user.client_id is None or user.client_id != payload.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    wh = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid warehouse_id")

    r = Return(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        warehouse_id=payload.warehouse_id,
        status="RECEIVED",
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    db.add(r)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="returns.create",
        entity_type="Return",
        entity_id=str(r.id),
        after=_to_out(r).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(r)
    return _to_out(r)


@router.post("/{return_id}/scan-line")
def scan_line(
    return_id: str,
    payload: ReturnScanLine,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        rid = uuid.UUID(return_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    r = db.scalar(select(Return).where(Return.id == rid, Return.tenant_id == user.tenant_id))
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if payload.qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    if payload.disposition not in {"RESTOCK", "QUARANTINE", "SCRAP"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid disposition")

    p = db.scalar(select(Product).where(Product.id == payload.product_id, Product.tenant_id == user.tenant_id, Product.client_id == r.client_id))
    if p is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id")

    to_loc_id = payload.to_location_id
    if payload.disposition in {"RESTOCK", "QUARANTINE"}:
        if to_loc_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_location_id required")
        loc = db.scalar(select(Location).where(Location.id == to_loc_id, Location.warehouse_id == r.warehouse_id))
        if loc is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid to_location_id")

        add_ledger_and_apply_on_hand(
            db,
            entry=LedgerCreate(
                tenant_id=r.tenant_id,
                client_id=r.client_id,
                warehouse_id=r.warehouse_id,
                product_id=p.id,
                batch_id=payload.batch_id,
                from_location_id=None,
                to_location_id=to_loc_id,
                qty_delta=payload.qty,
                event_type="RETURN_RECEIVE",
                reference_type="RETURN",
                reference_id=str(r.id),
                performed_by_user_id=user.id,
            ),
        )

    db.add(
        ReturnLine(
            return_id=r.id,
            product_id=p.id,
            batch_id=payload.batch_id,
            qty=payload.qty,
            disposition=payload.disposition,
            to_location_id=to_loc_id,
        )
    )
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="returns.scan_line",
        entity_type="Return",
        entity_id=str(r.id),
        after={
            "product_id": str(payload.product_id),
            "batch_id": str(payload.batch_id) if payload.batch_id else None,
            "qty": payload.qty,
            "disposition": payload.disposition,
            "to_location_id": str(payload.to_location_id) if payload.to_location_id else None,
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/{return_id}/complete")
def complete_return(
    return_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        rid = uuid.UUID(return_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    r = db.scalar(select(Return).where(Return.id == rid, Return.tenant_id == user.tenant_id))
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    before_status = r.status
    r.status = "CLOSED"

    # Generate and store Return PDF (idempotent)
    if r.return_pdf_file_id is None:
        client = db.scalar(select(Client).where(Client.id == r.client_id, Client.tenant_id == user.tenant_id))
        lang = (client.preferred_language if client else None) or user.language_pref or "en"
        lines = db.scalars(select(ReturnLine).where(ReturnLine.return_id == r.id)).all()
        pdf = render_return_pdf(
            return_id=str(r.id),
            lines=[{"product_id": str(l.product_id), "qty": l.qty, "disposition": l.disposition} for l in lines],
            language=lang,
        )
        key, size = save_bytes(data=pdf, filename=f"return_{r.id}.pdf")
        f = File(
            tenant_id=user.tenant_id,
            client_id=r.client_id,
            file_type="RETURN_PDF",
            storage_provider=settings.file_storage_provider,
            storage_key=key,
            original_name=f"return_{r.id}.pdf",
            mime_type="application/pdf",
            size_bytes=size,
            created_by_user_id=user.id,
        )
        db.add(f)
        db.flush()
        r.return_pdf_file_id = f.id
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="returns.complete",
        entity_type="Return",
        entity_id=str(r.id),
        before={"status": before_status},
        after={"status": r.status, "return_pdf_file_id": str(r.return_pdf_file_id) if r.return_pdf_file_id else None},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.get("/{return_id}/document")
def get_return_document(return_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        rid = uuid.UUID(return_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    r = db.scalar(select(Return).where(Return.id == rid, Return.tenant_id == user.tenant_id))
    if r is None or r.return_pdf_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.client_id is not None and r.client_id != user.client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    f = db.scalar(select(File).where(File.id == r.return_pdf_file_id, File.tenant_id == user.tenant_id))
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = load_bytes(storage_provider=f.storage_provider, storage_key=f.storage_key)
    from fastapi import Response

    return Response(content=data, media_type=f.mime_type, headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'})


