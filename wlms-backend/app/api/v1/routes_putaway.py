import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_warehouse_staff
from app.db.session import get_db
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone
from app.schemas.putaway import PutawayConfirm, PutawayTask
from app.services.inventory_service import move_on_hand
from app.services.audit_service import audit_log

router = APIRouter(prefix="/putaway", tags=["putaway"])


@router.get("/tasks", response_model=list[PutawayTask])
def list_putaway_tasks(db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)) -> list[PutawayTask]:
    # All balances in STAGING zones with on_hand > 0 are put-away tasks.
    # Join via Location -> Zone and filter by tenant via warehouse tenant_id.
    # (Location doesn't have tenant_id, so we gate by user.tenant_id through Warehouse.)
    stmt = (
        select(InventoryBalance, Location)
        .join(Location, InventoryBalance.location_id == Location.id)
        .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
        .join(Warehouse, Location.warehouse_id == Warehouse.id)
        .where(Warehouse.tenant_id == user.tenant_id)
        .where(WarehouseZone.zone_type == "STAGING")
        .where(InventoryBalance.on_hand_qty > 0)
    )

    rows = db.execute(stmt).all()
    # Suggest a storage destination per warehouse (simple v1 heuristic: first STORAGE location by code).
    wh_ids = sorted({str(loc.warehouse_id) for _bal, loc in rows})
    suggested: dict[str, tuple[uuid.UUID, str]] = {}
    if wh_ids:
        for wh_id in wh_ids:
            try:
                wid = uuid.UUID(wh_id)
            except Exception:
                continue
            sug = db.execute(
                select(Location.id, Location.code)
                .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
                .where(Location.warehouse_id == wid, WarehouseZone.zone_type == "STORAGE")
                .order_by(Location.code.asc())
                .limit(1)
            ).first()
            if sug is not None:
                suggested[wh_id] = (sug[0], sug[1])

    tasks: list[PutawayTask] = []
    for bal, loc in rows:
        sug = suggested.get(str(loc.warehouse_id))
        tasks.append(
            PutawayTask(
                client_id=bal.client_id,
                warehouse_id=bal.warehouse_id,
                product_id=bal.product_id,
                batch_id=bal.batch_id,
                from_location_id=loc.id,
                on_hand_qty=bal.on_hand_qty,
                suggested_to_location_id=sug[0] if sug else None,
                suggested_to_location_code=sug[1] if sug else None,
            )
        )
    return tasks


@router.post("/confirm")
def confirm_putaway(
    payload: PutawayConfirm,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> dict[str, str]:
    if payload.qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    # Validate from/to locations and tenant via warehouse
    from_loc = db.scalar(select(Location).where(Location.id == payload.from_location_id))
    to_loc = db.scalar(select(Location).where(Location.id == payload.to_location_id))
    if from_loc is None or to_loc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location")

    wh = db.scalar(select(Warehouse).where(Warehouse.id == from_loc.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if to_loc.warehouse_id != from_loc.warehouse_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Locations must be in same warehouse")

    from_zone = db.scalar(select(WarehouseZone).where(WarehouseZone.id == from_loc.zone_id))
    to_zone = db.scalar(select(WarehouseZone).where(WarehouseZone.id == to_loc.zone_id))
    if from_zone is None or to_zone is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zone")
    if from_zone.zone_type != "STAGING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from_location must be STAGING")
    if to_zone.zone_type != "STORAGE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_location must be STORAGE")

    # Validate product exists under this tenant (client scoping comes from balance)
    product = db.scalar(select(Product).where(Product.id == payload.product_id))
    if product is None or product.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product")

    # Determine client_id from the source balance row (authoritative)
    bal = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.tenant_id == user.tenant_id,
            InventoryBalance.location_id == from_loc.id,
            InventoryBalance.product_id == payload.product_id,
            InventoryBalance.batch_id == payload.batch_id,
        )
    )
    if bal is None or bal.on_hand_qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No stock in staging for this item")

    move_on_hand(
        db,
        tenant_id=user.tenant_id,
        client_id=bal.client_id,
        warehouse_id=bal.warehouse_id,
        product_id=bal.product_id,
        batch_id=bal.batch_id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        qty=payload.qty,
        reference_type="PUTAWAY",
        reference_id=f"{from_loc.id}->{to_loc.id}",
        performed_by_user_id=user.id,
        event_type="PUTAWAY_MOVE",
    )

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="putaway.confirm",
        entity_type="InventoryMove",
        entity_id=f"{payload.from_location_id}->{payload.to_location_id}",
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


