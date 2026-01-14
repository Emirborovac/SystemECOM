import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_warehouse_staff
from app.db.session import get_db
from app.models.inventory_reservation import InventoryReservation
from app.models.location import Location
from app.models.outbound import OutboundLine, OutboundOrder
from app.models.picking import PickingTask, PickingTaskLine
from app.models.product import Product
from app.models.product_batch import ProductBatch
from app.models.user import User
from app.models.warehouse_zone import WarehouseZone
from app.schemas.putaway import PutawayConfirm
from app.services.inventory_service import move_on_hand
from app.services.reservation_service import consume_reservation
from app.services.audit_service import audit_log

router = APIRouter(prefix="/picking", tags=["picking"])


@router.get("/tasks", response_model=list[dict])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)) -> list[dict]:
    tasks = db.scalars(select(PickingTask).join(OutboundOrder).where(OutboundOrder.tenant_id == user.tenant_id)).all()
    return [{"id": str(t.id), "outbound_id": str(t.outbound_id), "status": t.status} for t in tasks]


@router.get("/tasks/{task_id}/lines", response_model=list[dict])
def list_task_lines(task_id: str, db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)) -> list[dict]:
    try:
        tid = uuid.UUID(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task = db.scalar(select(PickingTask).where(PickingTask.id == tid))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.id == task.outbound_id, OutboundOrder.tenant_id == user.tenant_id))
    if outbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    rows = db.execute(
        select(PickingTaskLine, Location, WarehouseZone, ProductBatch)
        .join(Location, PickingTaskLine.from_location_id == Location.id)
        .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
        .outerjoin(ProductBatch, PickingTaskLine.batch_id == ProductBatch.id)
        .where(PickingTaskLine.picking_task_id == task.id)
        .order_by(
            ProductBatch.expiry_date.asc().nulls_last(),
            WarehouseZone.zone_type.asc(),
            Location.code.asc(),
        )
    ).all()
    return [
        {
            "id": l.id,
            "product_id": str(l.product_id),
            "batch_id": str(l.batch_id) if l.batch_id else None,
            "from_location_id": str(l.from_location_id),
            "from_location_code": loc.code,
            "zone_type": zone.zone_type,
            "expiry_date": batch.expiry_date.isoformat() if batch and batch.expiry_date else None,
            "qty_to_pick": l.qty_to_pick,
            "qty_picked": l.qty_picked,
        }
        for l, loc, zone, batch in rows
    ]


@router.post("/tasks/{task_id}/start")
def start_task(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> dict[str, str]:
    try:
        tid = uuid.UUID(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task = db.scalar(select(PickingTask).where(PickingTask.id == tid))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.id == task.outbound_id, OutboundOrder.tenant_id == user.tenant_id))
    if outbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.status = "IN_PROGRESS"
    task.assigned_to_user_id = user.id
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="picking.start",
        entity_type="PickingTask",
        entity_id=str(task.id),
        after={"status": task.status, "assigned_to_user_id": str(user.id)},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


class PickingScanBody(PutawayConfirm):
    """
    Reuse fields for: product_id, batch_id?, qty, from_location_id, to_location_id.
    Here: from_location_id = pick location, to_location_id = packing staging location.
    """


@router.post("/tasks/{task_id}/scan")
def scan_pick(
    task_id: str,
    payload: PickingScanBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> dict[str, str]:
    try:
        tid = uuid.UUID(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task = db.scalar(select(PickingTask).where(PickingTask.id == tid))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.id == task.outbound_id, OutboundOrder.tenant_id == user.tenant_id))
    if outbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if payload.qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    line = db.scalar(
        select(PickingTaskLine).where(
            PickingTaskLine.picking_task_id == task.id,
            PickingTaskLine.product_id == payload.product_id,
            PickingTaskLine.batch_id == payload.batch_id,
            PickingTaskLine.from_location_id == payload.from_location_id,
        )
    )
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pick line not found")
    if line.qty_picked + payload.qty > line.qty_to_pick:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Over-pick not allowed")

    # Consume matching reservation for this outbound/product/batch/location
    res = db.scalar(
        select(InventoryReservation).where(
            InventoryReservation.outbound_id == outbound.id,
            InventoryReservation.product_id == payload.product_id,
            InventoryReservation.batch_id == payload.batch_id,
            InventoryReservation.location_id == payload.from_location_id,
        )
    )
    if res is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No reservation found for this pick")
    consume_reservation(db, reservation=res, qty=payload.qty)

    # Move on-hand from pick location -> packing staging
    move_on_hand(
        db,
        tenant_id=outbound.tenant_id,
        client_id=outbound.client_id,
        warehouse_id=outbound.warehouse_id,
        product_id=payload.product_id,
        batch_id=payload.batch_id,
        from_location_id=payload.from_location_id,
        to_location_id=payload.to_location_id,
        qty=payload.qty,
        reference_type="OUTBOUND",
        reference_id=str(outbound.id),
        performed_by_user_id=user.id,
        event_type="PICK",
    )

    line.qty_picked += payload.qty
    db.flush()

    # Update outbound line picked qty
    oline = db.scalar(select(OutboundLine).where(OutboundLine.outbound_id == outbound.id, OutboundLine.product_id == payload.product_id))
    if oline is not None:
        oline.picked_qty += payload.qty

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="picking.scan",
        entity_type="PickingTask",
        entity_id=str(task.id),
        after={
            "product_id": str(payload.product_id),
            "batch_id": str(payload.batch_id) if payload.batch_id else None,
            "qty": payload.qty,
            "from_location_id": str(payload.from_location_id),
            "to_location_id": str(payload.to_location_id),
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> dict[str, str]:
    try:
        tid = uuid.UUID(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task = db.scalar(select(PickingTask).where(PickingTask.id == tid))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.id == task.outbound_id, OutboundOrder.tenant_id == user.tenant_id))
    if outbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # ensure all lines picked
    lines = db.scalars(select(PickingTaskLine).where(PickingTaskLine.picking_task_id == task.id)).all()
    if any(l.qty_picked < l.qty_to_pick for l in lines):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not all lines picked")

    task.status = "DONE"
    task.completed_at = datetime.now(timezone.utc)
    outbound.status = "PACKING"
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="picking.complete",
        entity_type="PickingTask",
        entity_id=str(task.id),
        after={"status": task.status, "outbound_status": outbound.status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


