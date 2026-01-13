from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin_or_supervisor
from app.db.session import get_db
from app.models.client import Client
from app.models.discrepancy import DiscrepancyReport
from app.models.inbound import InboundShipment
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.outbound import OutboundOrder
from app.models.product_batch import ProductBatch
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(require_admin_or_supervisor)) -> dict:
    today = datetime.now(timezone.utc).date()
    start_14 = today - timedelta(days=13)

    inbound_today = db.scalar(
        select(func.count(InboundShipment.id)).where(
            InboundShipment.tenant_id == user.tenant_id,
            func.date(InboundShipment.created_at) == today,
        )
    )
    outbound_today = db.scalar(
        select(func.count(OutboundOrder.id)).where(
            OutboundOrder.tenant_id == user.tenant_id,
            func.date(OutboundOrder.created_at) == today,
        )
    )
    pending_discrepancies = db.scalar(
        select(func.count(DiscrepancyReport.id)).where(
            DiscrepancyReport.tenant_id == user.tenant_id,
            DiscrepancyReport.status == "PENDING",
        )
    )

    # Occupied pallet positions (v1 approximation): distinct STORAGE locations with on_hand > 0
    occupied_positions = db.scalar(
        select(func.count(func.distinct(InventoryBalance.location_id)))
        .join(Location, InventoryBalance.location_id == Location.id)
        .join(WarehouseZone, Location.zone_id == WarehouseZone.id)
        .join(Warehouse, Location.warehouse_id == Warehouse.id)
        .where(InventoryBalance.tenant_id == user.tenant_id)
        .where(Warehouse.tenant_id == user.tenant_id)
        .where(WarehouseZone.zone_type == "STORAGE")
        .where(InventoryBalance.on_hand_qty > 0)
    )

    # Expiring items (count of balance rows with on_hand > 0 and expiry within X days)
    def _expiring(days: int) -> int:
        limit_date = today + timedelta(days=days)
        v = db.scalar(
            select(func.count(InventoryBalance.id))
            .join(ProductBatch, InventoryBalance.batch_id == ProductBatch.id)
            .where(InventoryBalance.tenant_id == user.tenant_id)
            .where(InventoryBalance.on_hand_qty > 0)
            .where(ProductBatch.expiry_date.is_not(None))
            .where(ProductBatch.expiry_date <= limit_date)
        )
        return int(v or 0)

    expiring_30 = _expiring(30)
    expiring_60 = _expiring(60)
    expiring_90 = _expiring(90)

    # Trend: inbound/outbound per day over last 14 days
    inbound_rows = db.execute(
        select(func.date(InboundShipment.created_at), func.count(InboundShipment.id))
        .where(InboundShipment.tenant_id == user.tenant_id)
        .where(func.date(InboundShipment.created_at) >= start_14)
        .where(func.date(InboundShipment.created_at) <= today)
        .group_by(func.date(InboundShipment.created_at))
    ).all()
    outbound_rows = db.execute(
        select(func.date(OutboundOrder.created_at), func.count(OutboundOrder.id))
        .where(OutboundOrder.tenant_id == user.tenant_id)
        .where(func.date(OutboundOrder.created_at) >= start_14)
        .where(func.date(OutboundOrder.created_at) <= today)
        .group_by(func.date(OutboundOrder.created_at))
    ).all()
    inbound_map = {d.isoformat(): int(c) for d, c in inbound_rows}
    outbound_map = {d.isoformat(): int(c) for d, c in outbound_rows}
    days = [(start_14 + timedelta(days=i)).isoformat() for i in range(14)]
    trend = [{"date": d, "inbound": inbound_map.get(d, 0), "outbound": outbound_map.get(d, 0)} for d in days]

    # Top clients by activity (v1: outbound count)
    top = db.execute(
        select(OutboundOrder.client_id, func.count(OutboundOrder.id))
        .where(OutboundOrder.tenant_id == user.tenant_id)
        .group_by(OutboundOrder.client_id)
        .order_by(func.count(OutboundOrder.id).desc())
        .limit(5)
    ).all()
    client_ids = [cid for cid, _cnt in top]
    names = {}
    if client_ids:
        rows = db.execute(select(Client.id, Client.name).where(Client.tenant_id == user.tenant_id, Client.id.in_(client_ids))).all()
        names = {str(i): n for i, n in rows}
    top_clients = [{"client_id": str(cid), "name": names.get(str(cid), ""), "outbound_count": int(cnt)} for cid, cnt in top]

    return {
        "date": today.isoformat(),
        "inbound_today": int(inbound_today or 0),
        "outbound_today": int(outbound_today or 0),
        "discrepancies_pending": int(pending_discrepancies or 0),
        "occupied_positions": int(occupied_positions or 0),
        "expiring_30": expiring_30,
        "expiring_60": expiring_60,
        "expiring_90": expiring_90,
        "trend_14d": trend,
        "top_clients": top_clients,
    }


