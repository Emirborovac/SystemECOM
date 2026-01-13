import uuid

import pytest
from fastapi import HTTPException

from app.services.inventory_service import LedgerCreate, add_ledger_and_apply_on_hand, adjust_reserved


class FakeSession:
    """
    In-memory DB stub for InventoryBalance + InventoryLedger.
    We only implement the minimal API inventory_service uses.
    """

    def __init__(self):
        self.balances = []  # InventoryBalance objects
        self.ledgers = []  # InventoryLedger objects

    def add(self, obj):
        # InventoryBalance has __tablename__ attribute; InventoryLedger too.
        name = obj.__class__.__name__
        if name == "InventoryBalance":
            self.balances.append(obj)
        elif name == "InventoryLedger":
            self.ledgers.append(obj)

    def flush(self):
        return None

    def scalar(self, stmt):
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Extremely small matcher: select InventoryBalance where tenant_id/product_id/batch_id/location_id match
        if "inventory_balances" in compiled:
            def _contains(v: str) -> bool:
                return v in compiled

            for b in self.balances:
                if not _contains(f"inventory_balances.tenant_id = {b.tenant_id}"):
                    continue
                if not _contains(f"inventory_balances.product_id = '{b.product_id}'"):
                    continue
                if b.batch_id is None:
                    if "inventory_balances.batch_id IS NULL" not in compiled:
                        continue
                else:
                    if not _contains(f"inventory_balances.batch_id = '{b.batch_id}'"):
                        continue
                if not _contains(f"inventory_balances.location_id = '{b.location_id}'"):
                    continue
                return b
        return None


def test_ledger_add_increases_on_hand_and_available():
    db = FakeSession()
    tenant_id = 1
    client_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()
    location_id = uuid.uuid4()

    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=None,
            from_location_id=None,
            to_location_id=location_id,
            qty_delta=10,
            event_type="INBOUND",
            reference_type="INBOUND",
            reference_id="x",
            performed_by_user_id=None,
        ),
    )

    assert len(db.balances) == 1
    b = db.balances[0]
    assert b.on_hand_qty == 10
    assert b.reserved_qty == 0
    assert b.available_qty == 10


def test_adjust_reserved_updates_available():
    db = FakeSession()
    tenant_id = 1
    client_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()
    location_id = uuid.uuid4()

    # Seed stock
    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=None,
            from_location_id=None,
            to_location_id=location_id,
            qty_delta=5,
            event_type="INBOUND",
            reference_type="INBOUND",
            reference_id="x",
            performed_by_user_id=None,
        ),
    )

    adjust_reserved(
        db,
        tenant_id=tenant_id,
        client_id=client_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_id=None,
        location_id=location_id,
        delta_reserved=3,
    )
    b = db.balances[0]
    assert b.on_hand_qty == 5
    assert b.reserved_qty == 3
    assert b.available_qty == 2


def test_cannot_reduce_on_hand_below_reserved():
    db = FakeSession()
    tenant_id = 1
    client_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()
    loc = uuid.uuid4()

    add_ledger_and_apply_on_hand(
        db,
        entry=LedgerCreate(
            tenant_id=tenant_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            batch_id=None,
            from_location_id=None,
            to_location_id=loc,
            qty_delta=5,
            event_type="INBOUND",
            reference_type="INBOUND",
            reference_id="x",
            performed_by_user_id=None,
        ),
    )
    adjust_reserved(
        db,
        tenant_id=tenant_id,
        client_id=client_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_id=None,
        location_id=loc,
        delta_reserved=4,
    )

    with pytest.raises(HTTPException) as e:
        add_ledger_and_apply_on_hand(
            db,
            entry=LedgerCreate(
                tenant_id=tenant_id,
                client_id=client_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                batch_id=None,
                from_location_id=loc,
                to_location_id=None,
                qty_delta=-2,  # would drop on_hand to 3 < reserved 4
                event_type="MOVE",
                reference_type="MANUAL",
                reference_id="x",
                performed_by_user_id=None,
            ),
        )
    assert e.value.status_code == 400


