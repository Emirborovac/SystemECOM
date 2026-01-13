import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryBalance, InventoryLedger


@dataclass(frozen=True)
class LedgerCreate:
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    from_location_id: uuid.UUID | None
    to_location_id: uuid.UUID | None
    qty_delta: int
    event_type: str
    reference_type: str
    reference_id: str
    performed_by_user_id: uuid.UUID | None


def _recalc_available(bal: InventoryBalance) -> None:
    bal.available_qty = bal.on_hand_qty - bal.reserved_qty


def adjust_reserved(
    db: Session,
    *,
    tenant_id: int,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    location_id: uuid.UUID,
    delta_reserved: int,
) -> None:
    if delta_reserved == 0:
        return

    bal = get_or_create_balance(
        db,
        tenant_id=tenant_id,
        client_id=client_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_id=batch_id,
        location_id=location_id,
    )
    if bal.reserved_qty + delta_reserved < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient reserved qty")
    if bal.on_hand_qty - (bal.reserved_qty + delta_reserved) < 0:
        # cannot reserve more than on_hand at this location
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient available qty")
    bal.reserved_qty += delta_reserved
    _recalc_available(bal)
    db.flush()


def get_or_create_balance(
    db: Session,
    *,
    tenant_id: int,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    location_id: uuid.UUID,
) -> InventoryBalance:
    bal = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.tenant_id == tenant_id,
            InventoryBalance.product_id == product_id,
            InventoryBalance.batch_id == batch_id,
            InventoryBalance.location_id == location_id,
        )
    )
    if bal is not None:
        return bal

    bal = InventoryBalance(
        tenant_id=tenant_id,
        client_id=client_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_id=batch_id,
        location_id=location_id,
        on_hand_qty=0,
        reserved_qty=0,
        available_qty=0,
    )
    db.add(bal)
    db.flush()
    return bal


def add_ledger_and_apply_on_hand(db: Session, *, entry: LedgerCreate) -> InventoryLedger:
    if entry.qty_delta == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty_delta cannot be 0")

    ledger = InventoryLedger(
        tenant_id=entry.tenant_id,
        client_id=entry.client_id,
        warehouse_id=entry.warehouse_id,
        product_id=entry.product_id,
        batch_id=entry.batch_id,
        from_location_id=entry.from_location_id,
        to_location_id=entry.to_location_id,
        qty_delta=entry.qty_delta,
        event_type=entry.event_type,
        reference_type=entry.reference_type,
        reference_id=entry.reference_id,
        performed_by_user_id=entry.performed_by_user_id,
    )
    db.add(ledger)

    # Apply to balances (on_hand only for v1 inbound/putaway)
    if entry.qty_delta > 0:
        if entry.to_location_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing to_location_id")
        bal = get_or_create_balance(
            db,
            tenant_id=entry.tenant_id,
            client_id=entry.client_id,
            warehouse_id=entry.warehouse_id,
            product_id=entry.product_id,
            batch_id=entry.batch_id,
            location_id=entry.to_location_id,
        )
        bal.on_hand_qty += entry.qty_delta
        _recalc_available(bal)
    else:
        if entry.from_location_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing from_location_id")
        bal = get_or_create_balance(
            db,
            tenant_id=entry.tenant_id,
            client_id=entry.client_id,
            warehouse_id=entry.warehouse_id,
            product_id=entry.product_id,
            batch_id=entry.batch_id,
            location_id=entry.from_location_id,
        )
        new_on_hand = bal.on_hand_qty + entry.qty_delta
        if new_on_hand < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient on-hand qty")
        # Do not allow moving/dispatching stock below reserved qty at this location.
        if new_on_hand < bal.reserved_qty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reduce on-hand below reserved qty")
        bal.on_hand_qty = new_on_hand
        _recalc_available(bal)

    db.flush()
    return ledger


def move_on_hand(
    db: Session,
    *,
    tenant_id: int,
    client_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    from_location_id: uuid.UUID,
    to_location_id: uuid.UUID,
    qty: int,
    reference_type: str,
    reference_id: str,
    performed_by_user_id: uuid.UUID | None,
    event_type: str = "PUTAWAY_MOVE",
) -> None:
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=batch_id,
            from_location_id=from_location_id,
            to_location_id=None,
            qty_delta=-qty,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_user_id=performed_by_user_id,
        ),
    )
    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=batch_id,
            from_location_id=None,
            to_location_id=to_location_id,
            qty_delta=qty,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_user_id=performed_by_user_id,
        ),
    )


