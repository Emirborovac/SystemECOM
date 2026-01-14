import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user, require_admin_or_supervisor
from app.db.session import get_db
from app.models.client import Client
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.outbound import OutboundLine, OutboundOrder
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone
from app.schemas.outbound import OutboundCreate, OutboundLineOut, OutboundOut
from app.services.reservation_service import reserve_for_outbound_line
from app.services.audit_service import audit_log
from app.services.uom_service import qty_to_pieces

router = APIRouter(prefix="/outbound", tags=["outbound"])


def _order_number() -> str:
    return f"OUT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _to_out(o: OutboundOrder) -> OutboundOut:
    return OutboundOut(
        id=o.id,
        tenant_id=o.tenant_id,
        client_id=o.client_id,
        warehouse_id=o.warehouse_id,
        order_number=o.order_number,
        status=o.status,
        destination_json=o.destination_json,
        requested_ship_date=o.requested_ship_date,
    )


def _line_out(l: OutboundLine) -> OutboundLineOut:
    return OutboundLineOut(
        id=l.id,
        outbound_id=l.outbound_id,
        product_id=l.product_id,
        requested_qty=l.requested_qty,
        reserved_qty=l.reserved_qty,
        picked_qty=l.picked_qty,
    )


@router.get("", response_model=list[OutboundOut])
def list_outbound(
    client_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OutboundOut]:
    stmt = select(OutboundOrder).where(OutboundOrder.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(OutboundOrder.client_id == user.client_id)
    elif client_id:
        try:
            cid = uuid.UUID(client_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
        stmt = stmt.where(OutboundOrder.client_id == cid)
    items = db.scalars(stmt).all()
    return [_to_out(o) for o in items]


@router.post("", response_model=OutboundOut, status_code=status.HTTP_201_CREATED)
def create_outbound(
    payload: OutboundCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OutboundOut:
    if not payload.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 1 line is required")

    # Client users can only create for their own client
    if is_client_user(user):
        if user.client_id is None or user.client_id != payload.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    wh = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid warehouse_id")

    o = OutboundOrder(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        warehouse_id=payload.warehouse_id,
        order_number=_order_number(),
        status="SUBMITTED" if is_client_user(user) else "DRAFT",
        destination_json=payload.destination.model_dump(),
        requested_ship_date=payload.requested_ship_date,
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    db.add(o)
    db.flush()

    for ln in payload.lines:
        p = db.scalar(
            select(Product).where(Product.id == ln.product_id, Product.tenant_id == user.tenant_id, Product.client_id == payload.client_id)
        )
        if p is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id for this client")
        qty_pieces = qty_to_pieces(product=p, qty=ln.qty, uom=ln.uom or "piece")

        # Enforce "cannot request more than available" (v1 no backorders):
        # Sum available across non-STAGING locations in this warehouse.
        available_sum = db.scalar(
            select(func.coalesce(func.sum(InventoryBalance.available_qty), 0))
            .select_from(InventoryBalance)
            .join(Location, InventoryBalance.location_id == Location.id)
            .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
            .where(InventoryBalance.tenant_id == user.tenant_id)
            .where(InventoryBalance.client_id == payload.client_id)
            .where(InventoryBalance.warehouse_id == payload.warehouse_id)
            .where(InventoryBalance.product_id == ln.product_id)
            .where(WarehouseZone.zone_type != "STAGING")
        )
        if (available_sum or 0) < qty_pieces:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient available stock")

        db.add(
            OutboundLine(
                outbound_id=o.id,
                product_id=ln.product_id,
                requested_qty=qty_pieces,
                reserved_qty=0,
                picked_qty=0,
                batch_policy=None,
            )
        )

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="outbound.create",
        entity_type="OutboundOrder",
        entity_id=str(o.id),
        after=_to_out(o).model_dump(),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(o)
    return _to_out(o)


@router.get("/{outbound_id}", response_model=OutboundOut)
def get_outbound(outbound_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> OutboundOut:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    stmt = select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")
        stmt = stmt.where(OutboundOrder.client_id == user.client_id)
    o = db.scalar(stmt)
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")
    return _to_out(o)


@router.get("/{outbound_id}/lines", response_model=list[OutboundLineOut])
def get_outbound_lines(
    outbound_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[OutboundLineOut]:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")
    if is_client_user(user) and (user.client_id is None or user.client_id != o.client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    lines = db.scalars(select(OutboundLine).where(OutboundLine.outbound_id == oid)).all()
    return [_line_out(l) for l in lines]


@router.post("/{outbound_id}/approve")
def approve_outbound(
    outbound_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
) -> dict[str, str]:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")
    if o.status not in {"SUBMITTED", "DRAFT"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Outbound not approvable")

    lines = db.scalars(select(OutboundLine).where(OutboundLine.outbound_id == o.id)).all()
    for l in lines:
        remaining = l.requested_qty - l.reserved_qty
        if remaining <= 0:
            continue
        reserve_for_outbound_line(
            db,
            tenant_id=o.tenant_id,
            outbound_id=o.id,
            client_id=o.client_id,
            warehouse_id=o.warehouse_id,
            product_id=l.product_id,
            qty=remaining,
        )
        l.reserved_qty += remaining

    before_status = o.status
    o.status = "APPROVED"
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="outbound.approve",
        entity_type="OutboundOrder",
        entity_id=str(o.id),
        before={"status": before_status},
        after={"status": o.status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


