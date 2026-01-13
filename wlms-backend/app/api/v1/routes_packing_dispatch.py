import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_warehouse_staff
from app.core.config import settings
from app.db.session import get_db
from app.models.inventory import InventoryLedger
from app.models.location import Location
from app.models.outbound import OutboundOrder
from app.models.picking import PickingTask
from app.models.user import User
from app.models.file import File
from app.models.outbound import OutboundLine
from app.models.client import Client
from app.services.inventory_service import LedgerCreate, add_ledger_and_apply_on_hand
from app.services.billing_service import create_billing_event
from app.services.document_service import render_dispatch_pdf, render_packing_slip_pdf
from app.services.storage_service import save_bytes, load_bytes
from app.services.audit_service import audit_log
from app.services.notification_service import queue_outbound_dispatched_email

router = APIRouter(tags=["packing", "dispatch"])


class PackingConfirmBody(BaseModel):
    # placeholder for future carton count/weight/carrier
    carton_count: int | None = None
    weight_kg: float | None = None
    carrier: str | None = None


@router.post("/packing/{outbound_id}/confirm")
def packing_confirm(
    outbound_id: str,
    payload: PackingConfirmBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    # Must have completed picking
    task = db.scalar(select(PickingTask).where(PickingTask.outbound_id == o.id))
    if task is None or task.status != "DONE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Picking not completed")

    before_status = o.status
    o.status = "PACKED"

    o.packing_json = {
        **(o.packing_json or {}),
        "carton_count": payload.carton_count,
        "weight_kg": payload.weight_kg,
        "carrier": payload.carrier,
    }

    # Generate and store Packing Slip PDF (idempotent)
    if o.packing_slip_file_id is None:
        client = db.scalar(select(Client).where(Client.id == o.client_id, Client.tenant_id == user.tenant_id))
        lang = (client.preferred_language if client else None) or user.language_pref or "en"
        lines = db.scalars(select(OutboundLine).where(OutboundLine.outbound_id == o.id)).all()
        pdf = render_packing_slip_pdf(
            outbound_id=str(o.id),
            order_number=o.order_number,
            lines=[{"product_id": str(l.product_id), "qty": l.requested_qty} for l in lines],
            packing=o.packing_json,
            language=lang,
        )
        key, size = save_bytes(data=pdf, filename=f"packing_{o.id}.pdf")
        f = File(
            tenant_id=user.tenant_id,
            client_id=o.client_id,
            file_type="PACKING_SLIP_PDF",
            storage_provider=settings.file_storage_provider,
            storage_key=key,
            original_name=f"packing_{o.order_number}.pdf",
            mime_type="application/pdf",
            size_bytes=size,
            created_by_user_id=user.id,
        )
        db.add(f)
        db.flush()
        o.packing_slip_file_id = f.id

        # Optional billing event for printing labels/slips (priced via price list printing.per_label)
        create_billing_event(
            db,
            client_id=o.client_id,
            warehouse_id=o.warehouse_id,
            event_type="PRINT_LABEL",
            quantity=1,
            reference_type="OUTBOUND",
            reference_id=str(o.id),
            event_date=datetime.now(timezone.utc).date(),
        )

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="packing.confirm",
        entity_type="OutboundOrder",
        entity_id=str(o.id),
        before={"status": before_status},
        after={"status": o.status, "packing_slip_file_id": str(o.packing_slip_file_id) if o.packing_slip_file_id else None},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.get("/packing/{outbound_id}/slip")
def get_packing_slip(outbound_id: str, db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)) -> Response:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None or o.packing_slip_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    f = db.scalar(select(File).where(File.id == o.packing_slip_file_id, File.tenant_id == user.tenant_id))
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = load_bytes(storage_provider=f.storage_provider, storage_key=f.storage_key)
    return Response(content=data, media_type=f.mime_type, headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'})


class DispatchConfirmBody(BaseModel):
    packing_location_id: uuid.UUID


@router.post("/dispatch/{outbound_id}/confirm")
def dispatch_confirm(
    outbound_id: str,
    payload: DispatchConfirmBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    loc = db.scalar(select(Location).where(Location.id == payload.packing_location_id, Location.warehouse_id == o.warehouse_id))
    if loc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid packing_location_id")

    # For v1: dispatch decrements all picked quantities from packing location via ledger entries.
    # We infer items by ledger movements into this packing location for this outbound reference.
    inbound_moves = db.scalars(
        select(InventoryLedger).where(
            InventoryLedger.reference_type == "OUTBOUND",
            InventoryLedger.reference_id == str(o.id),
            InventoryLedger.to_location_id == payload.packing_location_id,
            InventoryLedger.qty_delta > 0,
        )
    ).all()
    if not inbound_moves:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nothing to dispatch from packing location")

    for m in inbound_moves:
        add_ledger_and_apply_on_hand(
            db,
            entry=LedgerCreate(
                tenant_id=o.tenant_id,
                client_id=o.client_id,
                warehouse_id=o.warehouse_id,
                product_id=m.product_id,
                batch_id=m.batch_id,
                from_location_id=payload.packing_location_id,
                to_location_id=None,
                qty_delta=-m.qty_delta,
                event_type="DISPATCH",
                reference_type="OUTBOUND",
                reference_id=str(o.id),
                performed_by_user_id=user.id,
            ),
        )

    before_status = o.status
    o.status = "DISPATCHED"
    o.dispatched_at = datetime.now(timezone.utc)

    # Billing event: dispatch order (1)
    create_billing_event(
        db,
        client_id=o.client_id,
        warehouse_id=o.warehouse_id,
        event_type="DISPATCH_ORDER",
        quantity=1,
        reference_type="OUTBOUND",
        reference_id=str(o.id),
        event_date=o.dispatched_at.date(),
    )

    # Generate and store Dispatch PDF (idempotent)
    if o.dispatch_pdf_file_id is None:
        client = db.scalar(select(Client).where(Client.id == o.client_id, Client.tenant_id == user.tenant_id))
        lang = (client.preferred_language if client else None) or user.language_pref or "en"
        lines = db.scalars(select(OutboundLine).where(OutboundLine.outbound_id == o.id)).all()
        pdf = render_dispatch_pdf(
            outbound_id=str(o.id),
            order_number=o.order_number,
            lines=[{"product_id": str(l.product_id), "picked_qty": l.picked_qty} for l in lines],
            language=lang,
        )
        key, size = save_bytes(data=pdf, filename=f"dispatch_{o.id}.pdf")
        f = File(
            tenant_id=user.tenant_id,
            client_id=o.client_id,
            file_type="DISPATCH_PDF",
            storage_provider=settings.file_storage_provider,
            storage_key=key,
            original_name=f"dispatch_{o.order_number}.pdf",
            mime_type="application/pdf",
            size_bytes=size,
            created_by_user_id=user.id,
        )
        db.add(f)
        db.flush()
        o.dispatch_pdf_file_id = f.id
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="dispatch.confirm",
        entity_type="OutboundOrder",
        entity_id=str(o.id),
        before={"status": before_status},
        after={
            "status": o.status,
            "dispatch_pdf_file_id": str(o.dispatch_pdf_file_id) if o.dispatch_pdf_file_id else None,
            "packing_location_id": str(payload.packing_location_id),
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    if settings.notify_outbound_dispatched_email:
        recipients = db.scalars(select(User).where(User.client_id == o.client_id, User.is_active.is_(True))).all()
        for r in recipients:
            if r.email:
                queue_outbound_dispatched_email(
                    db,
                    tenant_id=user.tenant_id,
                    to_email=r.email,
                    outbound_id=str(o.id),
                    language=r.language_pref or "en",
                )
    db.commit()
    return {"status": "ok"}


@router.get("/outbound/{outbound_id}/document")
def get_dispatch_document(outbound_id: str, db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)):
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None or o.dispatch_pdf_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    f = db.scalar(select(File).where(File.id == o.dispatch_pdf_file_id, File.tenant_id == user.tenant_id))
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = load_bytes(storage_provider=f.storage_provider, storage_key=f.storage_key)
    return Response(content=data, media_type=f.mime_type, headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'})


