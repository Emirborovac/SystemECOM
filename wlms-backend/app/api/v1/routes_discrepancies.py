import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user, require_admin_or_supervisor
from app.db.session import get_db
from app.models.client import Client
from app.models.discrepancy import DiscrepancyReport
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.discrepancy import DiscrepancyCreate, DiscrepancyOut
from app.services.inventory_service import LedgerCreate, add_ledger_and_apply_on_hand
from app.services.audit_service import audit_log

router = APIRouter(prefix="/discrepancies", tags=["discrepancies"])


def _to_out(d: DiscrepancyReport) -> DiscrepancyOut:
    return DiscrepancyOut(
        id=d.id,
        tenant_id=d.tenant_id,
        client_id=d.client_id,
        warehouse_id=d.warehouse_id,
        product_id=d.product_id,
        batch_id=d.batch_id,
        location_id=d.location_id,
        system_qty=d.system_qty,
        counted_qty=d.counted_qty,
        delta_qty=d.delta_qty,
        reason=d.reason,
        status=d.status,
    )


@router.get("", response_model=list[DiscrepancyOut])
def list_discrepancies(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[DiscrepancyOut]:
    stmt = select(DiscrepancyReport).where(DiscrepancyReport.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(DiscrepancyReport.client_id == user.client_id)
    items = db.scalars(stmt).all()
    return [_to_out(d) for d in items]


@router.post("", response_model=DiscrepancyOut, status_code=status.HTTP_201_CREATED)
def create_discrepancy(
    payload: DiscrepancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> DiscrepancyOut:
    if payload.counted_qty < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="counted_qty must be >= 0")

    # validate product belongs to tenant
    product = db.scalar(select(Product).where(Product.id == payload.product_id, Product.tenant_id == user.tenant_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id")

    # location -> warehouse -> tenant
    loc = db.scalar(select(Location).where(Location.id == payload.location_id))
    if loc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location_id")
    wh = db.scalar(select(Warehouse).where(Warehouse.id == loc.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    # Determine client_id from inventory balance (authoritative)
    bal = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.tenant_id == user.tenant_id,
            InventoryBalance.location_id == loc.id,
            InventoryBalance.product_id == payload.product_id,
            InventoryBalance.batch_id == payload.batch_id,
        )
    )
    if bal is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No system stock record for this item at location")

    # Client users can only create discrepancy for their own client stock
    if is_client_user(user):
        if user.client_id is None or user.client_id != bal.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    system_qty = bal.on_hand_qty
    delta = payload.counted_qty - system_qty

    d = DiscrepancyReport(
        tenant_id=user.tenant_id,
        client_id=bal.client_id,
        warehouse_id=bal.warehouse_id,
        product_id=bal.product_id,
        batch_id=bal.batch_id,
        location_id=bal.location_id,
        system_qty=system_qty,
        counted_qty=payload.counted_qty,
        delta_qty=delta,
        reason=payload.reason,
        status="PENDING",
        created_by_user_id=user.id,
    )
    db.add(d)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="discrepancies.create",
        entity_type="DiscrepancyReport",
        entity_id=str(d.id),
        after=_to_out(d).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(d)
    return _to_out(d)


@router.post("/{discrepancy_id}/approve")
def approve_discrepancy(
    discrepancy_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        did = uuid.UUID(discrepancy_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    d = db.scalar(select(DiscrepancyReport).where(DiscrepancyReport.id == did, DiscrepancyReport.tenant_id == user.tenant_id))
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if d.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not pending")

    # Apply adjustment if delta != 0
    if d.delta_qty > 0:
        add_ledger_and_apply_on_hand(
            db,
            entry=LedgerCreate(
                tenant_id=d.tenant_id,
                client_id=d.client_id,
                warehouse_id=d.warehouse_id,
                product_id=d.product_id,
                batch_id=d.batch_id,
                from_location_id=None,
                to_location_id=d.location_id,
                qty_delta=d.delta_qty,
                event_type="ADJUSTMENT_PLUS",
                reference_type="DISCREPANCY",
                reference_id=str(d.id),
                performed_by_user_id=user.id,
            ),
        )
    elif d.delta_qty < 0:
        add_ledger_and_apply_on_hand(
            db,
            entry=LedgerCreate(
                tenant_id=d.tenant_id,
                client_id=d.client_id,
                warehouse_id=d.warehouse_id,
                product_id=d.product_id,
                batch_id=d.batch_id,
                from_location_id=d.location_id,
                to_location_id=None,
                qty_delta=d.delta_qty,
                event_type="ADJUSTMENT_MINUS",
                reference_type="DISCREPANCY",
                reference_id=str(d.id),
                performed_by_user_id=user.id,
            ),
        )

    d.status = "APPROVED"
    d.approved_by_user_id = user.id
    d.decided_at = datetime.now(timezone.utc)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="discrepancies.approve",
        entity_type="DiscrepancyReport",
        entity_id=str(d.id),
        before={"status": "PENDING"},
        after={"status": d.status, "delta_qty": d.delta_qty},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/{discrepancy_id}/reject")
def reject_discrepancy(
    discrepancy_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        did = uuid.UUID(discrepancy_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    d = db.scalar(select(DiscrepancyReport).where(DiscrepancyReport.id == did, DiscrepancyReport.tenant_id == user.tenant_id))
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if d.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not pending")

    d.status = "REJECTED"
    d.approved_by_user_id = user.id
    d.decided_at = datetime.now(timezone.utc)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="discrepancies.reject",
        entity_type="DiscrepancyReport",
        entity_id=str(d.id),
        before={"status": "PENDING"},
        after={"status": d.status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


