import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user
from app.db.session import get_db
from app.models.billing import BillingEvent
from app.models.client import Client
from app.models.discrepancy import DiscrepancyReport
from app.models.inbound import InboundShipment
from app.models.inventory import InventoryBalance, InventoryLedger
from app.models.outbound import OutboundOrder
from app.models.product_batch import ProductBatch
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


def _csv_response(rows: list[dict], filename: str) -> Response:
    buf = io.StringIO()
    if not rows:
        writer = csv.writer(buf)
        writer.writerow(["empty"])
    else:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory-snapshot")
def inventory_snapshot(
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    stmt = select(InventoryBalance).where(InventoryBalance.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            return [] if format == "json" else _csv_response([], "inventory_snapshot.csv")
        stmt = stmt.where(InventoryBalance.client_id == user.client_id)
    rows = db.scalars(stmt).all()
    data = [
        {
            "client_id": str(r.client_id),
            "warehouse_id": str(r.warehouse_id),
            "location_id": str(r.location_id),
            "product_id": str(r.product_id),
            "batch_id": str(r.batch_id) if r.batch_id else "",
            "on_hand_qty": r.on_hand_qty,
            "reserved_qty": r.reserved_qty,
            "available_qty": r.available_qty,
        }
        for r in rows
    ]
    return _csv_response(data, "inventory_snapshot.csv") if format == "csv" else data


@router.get("/expiry")
def expiry_report(
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    stmt = (
        select(InventoryBalance, ProductBatch)
        .join(ProductBatch, InventoryBalance.batch_id == ProductBatch.id)
        .where(InventoryBalance.tenant_id == user.tenant_id)
    )
    if is_client_user(user):
        if user.client_id is None:
            return [] if format == "json" else _csv_response([], "expiry.csv")
        stmt = stmt.where(InventoryBalance.client_id == user.client_id)
    rows = db.execute(stmt).all()
    data = [
        {
            "client_id": str(b.client_id),
            "warehouse_id": str(b.warehouse_id),
            "location_id": str(b.location_id),
            "product_id": str(b.product_id),
            "batch_id": str(b.batch_id),
            "batch_number": batch.batch_number,
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else "",
            "on_hand_qty": b.on_hand_qty,
        }
        for b, batch in rows
    ]
    return _csv_response(data, "expiry.csv") if format == "csv" else data


@router.get("/movements")
def movement_history(
    format: str = Query(default="json"),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    stmt = select(InventoryLedger).where(InventoryLedger.tenant_id == user.tenant_id).order_by(InventoryLedger.created_at.desc()).limit(limit)
    if is_client_user(user) and user.client_id is not None:
        stmt = stmt.where(InventoryLedger.client_id == user.client_id)
    rows = db.scalars(stmt).all()
    data = [
        {
            "created_at": r.created_at.isoformat(),
            "event_type": r.event_type,
            "client_id": str(r.client_id),
            "warehouse_id": str(r.warehouse_id),
            "product_id": str(r.product_id),
            "batch_id": str(r.batch_id) if r.batch_id else "",
            "from_location_id": str(r.from_location_id) if r.from_location_id else "",
            "to_location_id": str(r.to_location_id) if r.to_location_id else "",
            "qty_delta": r.qty_delta,
            "reference_type": r.reference_type,
            "reference_id": r.reference_id,
        }
        for r in rows
    ]
    return _csv_response(data, "movements.csv") if format == "csv" else data


@router.get("/volumes")
def volumes(
    start: date,
    end: date,
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    # inbound/outbound counts per day
    inbound_stmt = (
        select(func.date(InboundShipment.created_at), func.count(InboundShipment.id))
        .where(InboundShipment.tenant_id == user.tenant_id)
        .where(func.date(InboundShipment.created_at) >= start)
        .where(func.date(InboundShipment.created_at) <= end)
        .group_by(func.date(InboundShipment.created_at))
    )
    outbound_stmt = (
        select(func.date(OutboundOrder.created_at), func.count(OutboundOrder.id))
        .where(OutboundOrder.tenant_id == user.tenant_id)
        .where(func.date(OutboundOrder.created_at) >= start)
        .where(func.date(OutboundOrder.created_at) <= end)
        .group_by(func.date(OutboundOrder.created_at))
    )
    if is_client_user(user) and user.client_id is not None:
        inbound_stmt = inbound_stmt.where(InboundShipment.client_id == user.client_id)
        outbound_stmt = outbound_stmt.where(OutboundOrder.client_id == user.client_id)

    inbound = {d.isoformat(): int(c) for d, c in db.execute(inbound_stmt).all()}
    outbound = {d.isoformat(): int(c) for d, c in db.execute(outbound_stmt).all()}
    days = sorted(set(inbound.keys()) | set(outbound.keys()))
    data = [{"date": day, "inbound": inbound.get(day, 0), "outbound": outbound.get(day, 0)} for day in days]
    return _csv_response(data, "volumes.csv") if format == "csv" else data


@router.get("/discrepancies")
def discrepancy_report(
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    stmt = select(DiscrepancyReport).where(DiscrepancyReport.tenant_id == user.tenant_id).order_by(DiscrepancyReport.created_at.desc())
    if is_client_user(user) and user.client_id is not None:
        stmt = stmt.where(DiscrepancyReport.client_id == user.client_id)
    rows = db.scalars(stmt).all()
    data = [
        {
            "id": str(r.id),
            "status": r.status,
            "client_id": str(r.client_id),
            "warehouse_id": str(r.warehouse_id),
            "location_id": str(r.location_id),
            "product_id": str(r.product_id),
            "delta_qty": r.delta_qty,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return _csv_response(data, "discrepancies.csv") if format == "csv" else data


@router.get("/billing-events")
def billing_events_report(
    start: date,
    end: date,
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    # BillingEvent has no tenant_id; scope via Client
    stmt = (
        select(BillingEvent)
        .join(Client, Client.id == BillingEvent.client_id)
        .where(Client.tenant_id == user.tenant_id)
        .where(BillingEvent.event_date >= start, BillingEvent.event_date <= end)
    )
    if is_client_user(user) and user.client_id is not None:
        stmt = stmt.where(BillingEvent.client_id == user.client_id)
    rows = db.scalars(stmt).all()
    data = [
        {
            "event_date": r.event_date.isoformat(),
            "client_id": str(r.client_id),
            "invoice_id": str(r.invoice_id) if getattr(r, "invoice_id", None) else "",
            "warehouse_id": str(r.warehouse_id),
            "event_type": r.event_type,
            "quantity": r.quantity,
            "unit_price": float(r.unit_price),
            "total_price": float(r.total_price),
            "reference_type": r.reference_type,
            "reference_id": r.reference_id,
        }
        for r in rows
    ]
    return _csv_response(data, "billing_events.csv") if format == "csv" else data


@router.get("/inventory-reconcile")
def inventory_reconcile(
    format: str = Query(default="json"),
    client_id: str | None = Query(default=None),
    warehouse_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response | list[dict]:
    """
    Reconcile current InventoryBalance.on_hand_qty against the sum of InventoryLedger.qty_delta.
    This is a diagnostic report to prove ledger-first inventory is reconcilable.
    """
    # Aggregate ledger deltas by item+location
    ledger_stmt = select(
        InventoryLedger.client_id.label("client_id"),
        InventoryLedger.warehouse_id.label("warehouse_id"),
        InventoryLedger.location_id.label("location_id"),
        InventoryLedger.product_id.label("product_id"),
        InventoryLedger.batch_id.label("batch_id"),
        func.sum(InventoryLedger.qty_delta).label("ledger_on_hand_qty"),
    ).where(InventoryLedger.tenant_id == user.tenant_id)

    # Apply optional filters (and client isolation for client users)
    if is_client_user(user):
        if user.client_id is None:
            return [] if format == "json" else _csv_response([], "inventory_reconcile.csv")
        ledger_stmt = ledger_stmt.where(InventoryLedger.client_id == user.client_id)
    elif client_id:
        try:
            cid = uuid.UUID(client_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
        ledger_stmt = ledger_stmt.where(InventoryLedger.client_id == cid)

    if warehouse_id:
        try:
            wid = uuid.UUID(warehouse_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid warehouse_id")
        ledger_stmt = ledger_stmt.where(InventoryLedger.warehouse_id == wid)

    if product_id:
        try:
            pid = uuid.UUID(product_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id")
        ledger_stmt = ledger_stmt.where(InventoryLedger.product_id == pid)

    if location_id:
        try:
            lid = uuid.UUID(location_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location_id")
        ledger_stmt = ledger_stmt.where(InventoryLedger.location_id == lid)

    ledger_stmt = ledger_stmt.group_by(
        InventoryLedger.client_id,
        InventoryLedger.warehouse_id,
        InventoryLedger.location_id,
        InventoryLedger.product_id,
        InventoryLedger.batch_id,
    )
    ledger_rows = {  # key: (client, wh, loc, product, batch)
        (r.client_id, r.warehouse_id, r.location_id, r.product_id, r.batch_id): float(r.ledger_on_hand_qty or 0)
        for r in db.execute(ledger_stmt).all()
    }

    # Load balances for same scope and compare
    bal_stmt = select(InventoryBalance).where(InventoryBalance.tenant_id == user.tenant_id)
    if is_client_user(user) and user.client_id is not None:
        bal_stmt = bal_stmt.where(InventoryBalance.client_id == user.client_id)
    elif client_id:
        bal_stmt = bal_stmt.where(InventoryBalance.client_id == cid)  # cid set above if provided
    if warehouse_id:
        bal_stmt = bal_stmt.where(InventoryBalance.warehouse_id == wid)  # wid set above if provided
    if product_id:
        bal_stmt = bal_stmt.where(InventoryBalance.product_id == pid)  # pid set above if provided
    if location_id:
        bal_stmt = bal_stmt.where(InventoryBalance.location_id == lid)  # lid set above if provided

    balances = db.scalars(bal_stmt).all()

    out: list[dict] = []
    seen: set[tuple] = set()
    for b in balances:
        key = (b.client_id, b.warehouse_id, b.location_id, b.product_id, b.batch_id)
        seen.add(key)
        ledger_qty = ledger_rows.get(key, 0.0)
        bal_qty = float(b.on_hand_qty)
        delta = bal_qty - ledger_qty
        if abs(delta) > 1e-9:
            out.append(
                {
                    "client_id": str(b.client_id),
                    "warehouse_id": str(b.warehouse_id),
                    "location_id": str(b.location_id),
                    "product_id": str(b.product_id),
                    "batch_id": str(b.batch_id) if b.batch_id else "",
                    "balance_on_hand_qty": bal_qty,
                    "ledger_on_hand_qty": ledger_qty,
                    "difference": delta,
                }
            )

    # Ledger entries without a corresponding balance row (should be rare, but indicates missing materialization)
    for key, ledger_qty in ledger_rows.items():
        if key in seen:
            continue
        client_id_k, wh_k, loc_k, prod_k, batch_k = key
        out.append(
            {
                "client_id": str(client_id_k),
                "warehouse_id": str(wh_k),
                "location_id": str(loc_k),
                "product_id": str(prod_k),
                "batch_id": str(batch_k) if batch_k else "",
                "balance_on_hand_qty": 0.0,
                "ledger_on_hand_qty": ledger_qty,
                "difference": 0.0 - ledger_qty,
            }
        )

    return _csv_response(out, "inventory_reconcile.csv") if format == "csv" else out


