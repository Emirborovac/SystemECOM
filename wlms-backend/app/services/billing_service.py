import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.billing import BillingEvent, Invoice, InvoiceLine, PriceList
from app.models.client import Client
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.warehouse_zone import WarehouseZone


def validate_price_list_rules(*, rules: dict, client_currency: str) -> None:
    """
    Minimal v1 validation so we can fail fast on broken price lists.
    """
    if not isinstance(rules, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json must be an object")

    currency = (rules.get("currency") or "").strip()
    if not currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.currency is required")
    if len(currency) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.currency must be a 3-letter code")
    if currency.upper() != (client_currency or "EUR").upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"rules_json.currency must match client billing_currency ({client_currency})",
        )

    storage = rules.get("storage") or {}
    if not isinstance(storage, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.storage must be an object")
    storage_type = storage.get("type")
    if storage_type != "PALLET_POSITION_DAY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rules_json.storage.type must be PALLET_POSITION_DAY in v1",
        )
    try:
        unit_price = float(storage.get("unit_price"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.storage.unit_price must be a number")
    if unit_price < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.storage.unit_price must be >= 0")

    inbound = rules.get("inbound") or {}
    if not isinstance(inbound, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.inbound must be an object")
    if "per_line" in inbound:
        try:
            if float(inbound.get("per_line") or 0) < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.inbound.per_line must be >= 0")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.inbound.per_line must be a number")

    dispatch = rules.get("dispatch") or {}
    if not isinstance(dispatch, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.dispatch must be an object")
    if "per_order" in dispatch:
        try:
            if float(dispatch.get("per_order") or 0) < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.dispatch.per_order must be >= 0")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.dispatch.per_order must be a number")

    printing = rules.get("printing") or {}
    if printing and not isinstance(printing, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.printing must be an object")
    if isinstance(printing, dict) and "per_label" in printing:
        try:
            if float(printing.get("per_label") or 0) < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.printing.per_label must be >= 0")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rules_json.printing.per_label must be a number")


def get_active_price_list(db: Session, *, client_id: uuid.UUID, as_of: date) -> PriceList | None:
    return db.scalar(
        select(PriceList)
        .where(PriceList.client_id == client_id, PriceList.effective_from <= as_of)
        .order_by(PriceList.effective_from.desc())
    )


def _price_from_rules(rules: dict, event_type: str) -> float:
    # Minimal rules convention:
    # { "currency":"EUR", "storage": {"type":"PALLET_POSITION_DAY","unit_price": 8.5}, "inbound": {"per_line": 1.0}, "dispatch": {"per_order": 3.5}}
    if event_type == "STORAGE_DAY":
        return float((rules.get("storage") or {}).get("unit_price") or 0)
    if event_type == "INBOUND_LINE":
        return float((rules.get("inbound") or {}).get("per_line") or 0)
    if event_type == "DISPATCH_ORDER":
        return float((rules.get("dispatch") or {}).get("per_order") or 0)
    if event_type == "PRINT_LABEL":
        return float((rules.get("printing") or {}).get("per_label") or 0)
    return 0.0


def create_billing_event(
    db: Session,
    *,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    event_type: str,
    quantity: int,
    reference_type: str,
    reference_id: str,
    event_date: date,
) -> BillingEvent:
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be > 0")

    price_list = get_active_price_list(db, client_id=client_id, as_of=event_date)
    unit_price = _price_from_rules(price_list.rules_json if price_list else {}, event_type)
    total = unit_price * quantity

    ev = BillingEvent(
        client_id=client_id,
        warehouse_id=warehouse_id,
        event_type=event_type,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total,
        reference_type=reference_type,
        reference_id=reference_id,
        event_date=event_date,
    )
    db.add(ev)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # idempotent behavior via unique constraint
        existing = db.scalar(
            select(BillingEvent).where(
                BillingEvent.client_id == client_id,
                BillingEvent.event_type == event_type,
                BillingEvent.reference_type == reference_type,
                BillingEvent.reference_id == reference_id,
                BillingEvent.event_date == event_date,
            )
        )
        if existing is None:
            raise
        return existing
    db.refresh(ev)
    return ev


def run_daily_storage(db: Session, *, event_date: date) -> int:
    # For v1: PALLET_POSITION_DAY approximated as count of distinct locations with on_hand>0 per client+warehouse.
    rows = db.execute(
        select(InventoryBalance.client_id, InventoryBalance.warehouse_id, func.count(func.distinct(InventoryBalance.location_id)))
        .where(InventoryBalance.on_hand_qty > 0)
        .group_by(InventoryBalance.client_id, InventoryBalance.warehouse_id)
    ).all()

    created = 0
    for client_id, warehouse_id, loc_count in rows:
        if loc_count <= 0:
            continue
        create_billing_event(
            db,
            client_id=client_id,
            warehouse_id=warehouse_id,
            event_type="STORAGE_DAY",
            quantity=int(loc_count),
            reference_type="CRON",
            reference_id=event_date.isoformat(),
            event_date=event_date,
        )
        created += 1
    return created


def generate_invoice(
    db: Session,
    *,
    client_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> Invoice:
    client = db.scalar(select(Client).where(Client.id == client_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    # Prevent double-billing: only invoice events that have not yet been assigned to an invoice.
    events = db.scalars(
        select(BillingEvent).where(
            BillingEvent.client_id == client_id,
            BillingEvent.event_date >= period_start,
            BillingEvent.event_date <= period_end,
            BillingEvent.invoice_id.is_(None),
        )
    ).all()
    if not events:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No uninvoiced billing events in period")

    currency = client.billing_currency
    vat_rate = float(getattr(client, "vat_rate", 0) or 0)
    invoice = Invoice(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        status="DRAFT",
        currency=currency,
        subtotal=0,
        tax_total=0,
        total=0,
    )
    db.add(invoice)
    db.flush()

    # Link events to this invoice for auditability/traceability.
    for ev in events:
        ev.invoice_id = invoice.id

    # Group by event_type and sum
    grouped: dict[str, dict[str, float]] = {}
    for ev in events:
        g = grouped.setdefault(ev.event_type, {"qty": 0, "total": 0, "unit": float(ev.unit_price)})
        g["qty"] += ev.quantity
        g["total"] += float(ev.total_price)
        # keep latest unit if any
        g["unit"] = float(ev.unit_price)

    subtotal = 0.0
    for event_type, g in grouped.items():
        qty = int(g["qty"])
        unit = float(g["unit"])
        total = float(g["total"])
        subtotal += total
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description_key=f"invoice.line.{event_type}",
                description_params_json={"event_type": event_type},
                quantity=qty,
                unit_price=unit,
                total_price=total,
                tax_rate=vat_rate,
                drilldown_query_json={"client_id": str(client_id), "event_type": event_type, "period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
            )
        )

    invoice.subtotal = subtotal
    invoice.tax_total = round(subtotal * vat_rate, 2)
    invoice.total = float(invoice.subtotal) + float(invoice.tax_total)
    db.commit()
    db.refresh(invoice)
    return invoice


