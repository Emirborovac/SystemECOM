import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin_or_supervisor
from app.db.session import get_db
from app.models.inventory_reservation import InventoryReservation
from app.models.location import Location
from app.models.outbound import OutboundOrder
from app.models.picking import PickingTask, PickingTaskLine
from app.models.product_batch import ProductBatch
from app.models.warehouse_zone import WarehouseZone
from app.models.user import User
from app.services.audit_service import audit_log

router = APIRouter(prefix="/outbound", tags=["outbound"])


@router.post("/{outbound_id}/generate-picks")
def generate_picks(
    outbound_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
    request: Request | None = None,
) -> dict[str, str]:
    try:
        oid = uuid.UUID(outbound_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")

    o = db.scalar(select(OutboundOrder).where(OutboundOrder.id == oid, OutboundOrder.tenant_id == user.tenant_id))
    if o is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound not found")
    if o.status != "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Outbound not approved")

    existing = db.scalar(select(PickingTask).where(PickingTask.outbound_id == o.id))
    if existing is not None:
        return {"status": "ok"}

    # Route/group + FEFO ordering: prefer earlier-expiring batches, then zone/location code
    reservations = db.scalars(
        select(InventoryReservation)
        .join(Location, InventoryReservation.location_id == Location.id)
        .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
        .outerjoin(ProductBatch, InventoryReservation.batch_id == ProductBatch.id)
        .where(InventoryReservation.outbound_id == o.id)
        .order_by(
            ProductBatch.expiry_date.asc().nulls_last(),
            WarehouseZone.zone_type.asc(),
            Location.code.asc(),
        )
    ).all()
    if not reservations:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No reservations to pick")

    task = PickingTask(outbound_id=o.id, assigned_to_user_id=None, status="OPEN")
    db.add(task)
    db.flush()

    for r in reservations:
        db.add(
            PickingTaskLine(
                picking_task_id=task.id,
                product_id=r.product_id,
                batch_id=r.batch_id,
                from_location_id=r.location_id,
                qty_to_pick=r.qty_reserved,
                qty_picked=0,
            )
        )

    o.status = "PICKING"
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="outbound.generate_picks",
        entity_type="OutboundOrder",
        entity_id=str(o.id),
        after={"status": o.status, "picking_task_id": str(task.id)},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


