import uuid

import pytest
from fastapi import HTTPException

from app.models.inventory_reservation import InventoryReservation
from app.services.reservation_service import consume_reservation


class FakeSession:
    def __init__(self):
        self.deleted = []

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        return None


def test_consume_reservation_reduces_and_deletes_when_zero(monkeypatch):
    db = FakeSession()
    r = InventoryReservation(
        id=uuid.uuid4(),
        tenant_id=1,
        outbound_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        warehouse_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        batch_id=None,
        location_id=uuid.uuid4(),
        qty_reserved=2,
    )

    calls = []

    def fake_adjust_reserved(_db, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.services.reservation_service.adjust_reserved", fake_adjust_reserved)

    consume_reservation(db, reservation=r, qty=2)
    assert r.qty_reserved == 0
    assert db.deleted == [r]
    assert calls and calls[0]["delta_reserved"] == -2


def test_consume_reservation_rejects_overconsume():
    db = FakeSession()
    r = InventoryReservation(
        id=uuid.uuid4(),
        tenant_id=1,
        outbound_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        warehouse_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        batch_id=None,
        location_id=uuid.uuid4(),
        qty_reserved=1,
    )

    with pytest.raises(HTTPException) as e:
        consume_reservation(db, reservation=r, qty=2)
    assert e.value.status_code == 400


