import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user, require_warehouse_staff
from app.core.config import settings
from app.core.rbac import ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR
from app.db.session import get_db
from app.models.client import Client
from app.models.inbound import InboundLine, InboundShipment
from app.models.location import Location
from app.models.product import Product
from app.models.product_batch import ProductBatch
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone
from app.schemas.inbound import InboundCreate, InboundLineOut, InboundOut, InboundScanLine
from app.services.billing_service import create_billing_event
from app.models.file import File
from app.services.document_service import render_inbound_pdf
from app.services.inventory_service import LedgerCreate, add_ledger_and_apply_on_hand
from app.services.storage_service import save_bytes, load_bytes
from app.services.audit_service import audit_log
from app.services.notification_service import queue_inbound_received_email
from app.services.uom_service import qty_to_pieces

router = APIRouter(prefix="/inbound", tags=["inbound"])


def _ref_number() -> str:
    return f"INB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _to_out(i: InboundShipment) -> InboundOut:
    return InboundOut(
        id=i.id,
        tenant_id=i.tenant_id,
        client_id=i.client_id,
        warehouse_id=i.warehouse_id,
        reference_number=i.reference_number,
        status=i.status,
        supplier=i.supplier,
        notes=i.notes,
    )


def _line_out(l: InboundLine) -> InboundLineOut:
    return InboundLineOut(
        id=l.id,
        inbound_id=l.inbound_id,
        product_id=l.product_id,
        expected_qty=l.expected_qty,
        received_qty=l.received_qty,
        batch_id=l.batch_id,
        notes=l.notes,
    )


@router.get("", response_model=list[InboundOut])
def list_inbound(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[InboundOut]:
    stmt = select(InboundShipment).where(InboundShipment.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(InboundShipment.client_id == user.client_id)
    items = db.scalars(stmt).all()
    return [_to_out(i) for i in items]


@router.post("", response_model=InboundOut, status_code=status.HTTP_201_CREATED)
def create_inbound(
    payload: InboundCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> InboundOut:
    # Client users can only create inbound for their client.
    if is_client_user(user):
        if user.client_id is None or user.client_id != payload.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    else:
        if user.role not in {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    wh = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid warehouse_id")

    inbound = InboundShipment(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        warehouse_id=payload.warehouse_id,
        reference_number=_ref_number(),
        status="DRAFT",
        supplier=payload.supplier,
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    db.add(inbound)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="inbound.create",
        entity_type="InboundShipment",
        entity_id=str(inbound.id),
        after=_to_out(inbound).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(inbound)
    return _to_out(inbound)


@router.get("/{inbound_id}", response_model=InboundOut)
def get_inbound(inbound_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> InboundOut:
    try:
        iid = uuid.UUID(inbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    stmt = select(InboundShipment).where(InboundShipment.id == iid, InboundShipment.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")
        stmt = stmt.where(InboundShipment.client_id == user.client_id)
    inbound = db.scalar(stmt)
    if inbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")
    return _to_out(inbound)


@router.post("/{inbound_id}/start-receiving")
def start_receiving(
    inbound_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        iid = uuid.UUID(inbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    inbound = db.scalar(select(InboundShipment).where(InboundShipment.id == iid, InboundShipment.tenant_id == user.tenant_id))
    if inbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    before_status = inbound.status
    inbound.status = "RECEIVING"
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="inbound.start_receiving",
        entity_type="InboundShipment",
        entity_id=str(inbound.id),
        before={"status": before_status},
        after={"status": inbound.status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/{inbound_id}/scan-line", response_model=InboundLineOut)
def scan_line(
    inbound_id: str,
    payload: InboundScanLine,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> InboundLineOut:
    try:
        iid = uuid.UUID(inbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    inbound = db.scalar(select(InboundShipment).where(InboundShipment.id == iid, InboundShipment.tenant_id == user.tenant_id))
    if inbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")
    if inbound.status not in {"RECEIVING", "DRAFT"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inbound not in receiving state")

    # staging location must be in this warehouse AND a STAGING zone
    staging = db.scalar(select(Location).where(Location.id == payload.location_staging_id, Location.warehouse_id == inbound.warehouse_id))
    if staging is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid staging location")
    zone = db.scalar(select(WarehouseZone).where(WarehouseZone.id == staging.zone_id, WarehouseZone.warehouse_id == inbound.warehouse_id))
    if zone is None or zone.zone_type != "STAGING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location is not a staging zone")

    # find product by barcode, scoped by tenant+client
    product = db.scalar(
        select(Product).where(
            Product.tenant_id == user.tenant_id,
            Product.client_id == inbound.client_id,
            Product.barcode == payload.barcode,
        )
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown product barcode")

    # batch requirements
    batch_id: uuid.UUID | None = None
    if product.lot_tracking_enabled or product.expiry_tracking_enabled:
        if not payload.batch_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="batch_number required")
        if product.expiry_tracking_enabled and payload.expiry_date is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expiry_date required")

        batch = db.scalar(
            select(ProductBatch).where(
                ProductBatch.product_id == product.id,
                ProductBatch.batch_number == payload.batch_number,
                ProductBatch.expiry_date == payload.expiry_date,
            )
        )
        if batch is None:
            batch = ProductBatch(product_id=product.id, batch_number=payload.batch_number, expiry_date=payload.expiry_date)
            db.add(batch)
            db.flush()
        batch_id = batch.id

    qty_pieces = qty_to_pieces(product=product, qty=payload.qty, uom=payload.uom or "piece")

    # Upsert-ish inbound line by (inbound_id, product_id, batch_id)
    line = db.scalar(
        select(InboundLine).where(
            InboundLine.inbound_id == inbound.id,
            InboundLine.product_id == product.id,
            InboundLine.batch_id == batch_id,
        )
    )
    if line is None:
        line = InboundLine(inbound_id=inbound.id, product_id=product.id, expected_qty=None, received_qty=0, batch_id=batch_id)
        db.add(line)
        db.flush()
    line.received_qty += qty_pieces

    # Ledger + balances
    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=user.tenant_id,
            client_id=inbound.client_id,
            warehouse_id=inbound.warehouse_id,
            product_id=product.id,
            batch_id=batch_id,
            from_location_id=None,
            to_location_id=staging.id,
            qty_delta=qty_pieces,
            event_type="INBOUND_RECEIVE",
            reference_type="INBOUND",
            reference_id=str(inbound.id),
            performed_by_user_id=user.id,
        ),
    )

    inbound.status = "RECEIVING"
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="inbound.scan_line",
        entity_type="InboundShipment",
        entity_id=str(inbound.id),
        after={
            "barcode": payload.barcode,
            "qty": payload.qty,
            "uom": payload.uom or "piece",
            "qty_pieces": qty_pieces,
            "product_id": str(product.id),
            "batch_id": str(batch_id) if batch_id else None,
            "staging_location_id": str(staging.id),
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(line)
    return _line_out(line)


@router.post("/{inbound_id}/complete")
def complete_inbound(
    inbound_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        iid = uuid.UUID(inbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    inbound = db.scalar(select(InboundShipment).where(InboundShipment.id == iid, InboundShipment.tenant_id == user.tenant_id))
    if inbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    before_status = inbound.status
    inbound.status = "RECEIVED"
    inbound.received_at = datetime.now(timezone.utc)

    # Billing event: inbound lines count (simple v1)
    line_count = db.scalar(select(func.count(InboundLine.id)).where(InboundLine.inbound_id == inbound.id)) or 0
    if line_count > 0:
        create_billing_event(
            db,
            client_id=inbound.client_id,
            warehouse_id=inbound.warehouse_id,
            event_type="INBOUND_LINE",
            quantity=int(line_count),
            reference_type="INBOUND",
            reference_id=str(inbound.id),
            event_date=inbound.received_at.date(),
        )

    # Generate and store Receiving PDF (idempotent)
    if inbound.receiving_pdf_file_id is None:
        client = db.scalar(select(Client).where(Client.id == inbound.client_id, Client.tenant_id == user.tenant_id))
        lang = (client.preferred_language if client else None) or user.language_pref or "en"
        lines = db.scalars(select(InboundLine).where(InboundLine.inbound_id == inbound.id)).all()
        pdf = render_inbound_pdf(
            inbound_id=str(inbound.id),
            reference_number=inbound.reference_number,
            lines=[{"product_id": str(l.product_id), "received_qty": l.received_qty} for l in lines],
            language=lang,
        )
        key, size = save_bytes(data=pdf, filename=f"receiving_{inbound.id}.pdf")
        f = File(
            tenant_id=user.tenant_id,
            client_id=inbound.client_id,
            file_type="RECEIVING_PDF",
            storage_provider=settings.file_storage_provider,
            storage_key=key,
            original_name=f"receiving_{inbound.reference_number}.pdf",
            mime_type="application/pdf",
            size_bytes=size,
            created_by_user_id=user.id,
        )
        db.add(f)
        db.flush()
        inbound.receiving_pdf_file_id = f.id

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="inbound.complete",
        entity_type="InboundShipment",
        entity_id=str(inbound.id),
        before={"status": before_status},
        after={
            "status": inbound.status,
            "receiving_pdf_file_id": str(inbound.receiving_pdf_file_id) if inbound.receiving_pdf_file_id else None,
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    if settings.notify_inbound_received_email:
        recipients = db.scalars(select(User).where(User.client_id == inbound.client_id, User.is_active.is_(True))).all()
        for r in recipients:
            if r.email:
                queue_inbound_received_email(
                    db,
                    tenant_id=user.tenant_id,
                    to_email=r.email,
                    inbound_id=str(inbound.id),
                    language=r.language_pref or "en",
                )
    db.commit()
    return {"status": "ok"}


@router.get("/{inbound_id}/document")
def get_inbound_document(
    inbound_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        iid = uuid.UUID(inbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")

    stmt = select(InboundShipment).where(InboundShipment.id == iid, InboundShipment.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound not found")
        stmt = stmt.where(InboundShipment.client_id == user.client_id)
    inbound = db.scalar(stmt)
    if inbound is None or inbound.receiving_pdf_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    f = db.scalar(select(File).where(File.id == inbound.receiving_pdf_file_id, File.tenant_id == user.tenant_id))
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    data = load_bytes(storage_provider=f.storage_provider, storage_key=f.storage_key)
    from fastapi import Response

    return Response(content=data, media_type=f.mime_type, headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'})


