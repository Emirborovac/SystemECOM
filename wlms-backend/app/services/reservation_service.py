import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryBalance
from app.models.inventory_reservation import InventoryReservation
from app.models.location import Location
from app.models.product_batch import ProductBatch
from app.models.warehouse_zone import WarehouseZone
from app.services.inventory_service import adjust_reserved


def _candidate_balances_stmt(
    *,
    tenant_id: int,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
) :
    # Reserve from non-STAGING locations in this warehouse.
    # (We allow STORAGE/PACKING/etc; caller can tighten later.)
    return (
        select(InventoryBalance, WarehouseZone, ProductBatch)
        .join(Location, InventoryBalance.location_id == Location.id)
        .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
        .outerjoin(ProductBatch, InventoryBalance.batch_id == ProductBatch.id)
        .where(InventoryBalance.tenant_id == tenant_id)
        .where(InventoryBalance.client_id == client_id)
        .where(InventoryBalance.warehouse_id == warehouse_id)
        .where(InventoryBalance.product_id == product_id)
        .where(InventoryBalance.available_qty > 0)
        .where(WarehouseZone.zone_type != "STAGING")
        .order_by(ProductBatch.expiry_date.asc().nulls_last(), InventoryBalance.updated_at.asc())
    )


def reserve_for_outbound_line(
    db: Session,
    *,
    tenant_id: int,
    outbound_id: uuid.UUID,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    qty: int,
) -> list[InventoryReservation]:
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    remaining = qty
    created: list[InventoryReservation] = []

    rows = db.execute(
        _candidate_balances_stmt(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
        )
    ).all()

    for bal, _zone, _batch in rows:
        if remaining <= 0:
            break
        take = min(remaining, bal.available_qty)
        if take <= 0:
            continue

        # Update aggregate reserved in balances
        adjust_reserved(
            db,
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=bal.batch_id,
            location_id=bal.location_id,
            delta_reserved=take,
        )

        # Upsert reservation row for this outbound/product/batch/location
        r = db.scalar(
            select(InventoryReservation).where(
                InventoryReservation.outbound_id == outbound_id,
                InventoryReservation.product_id == product_id,
                InventoryReservation.batch_id == bal.batch_id,
                InventoryReservation.location_id == bal.location_id,
            )
        )
        if r is None:
            r = InventoryReservation(
                tenant_id=tenant_id,
                outbound_id=outbound_id,
                client_id=client_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                batch_id=bal.batch_id,
                location_id=bal.location_id,
                qty_reserved=0,
            )
            db.add(r)
            db.flush()
        r.qty_reserved += take
        created.append(r)
        remaining -= take

    if remaining > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient available inventory to reserve")

    db.flush()
    return created


def consume_reservation(
    db: Session,
    *,
    reservation: InventoryReservation,
    qty: int,
) -> None:
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")
    if reservation.qty_reserved < qty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation qty insufficient")

    # Reduce aggregate reserved on balances
    adjust_reserved(
        db,
        tenant_id=reservation.tenant_id,
        client_id=reservation.client_id,
        warehouse_id=reservation.warehouse_id,
        product_id=reservation.product_id,
        batch_id=reservation.batch_id,
        location_id=reservation.location_id,
        delta_reserved=-qty,
    )

    reservation.qty_reserved -= qty
    if reservation.qty_reserved == 0:
        db.delete(reservation)
    db.flush()


