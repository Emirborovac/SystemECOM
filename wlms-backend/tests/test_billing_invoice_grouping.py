import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.services import billing_service


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeClient:
    def __init__(self, *, billing_currency: str = "EUR"):
        self.billing_currency = billing_currency


class FakeBillingEvent:
    def __init__(self, *, event_type: str, quantity: int, unit_price: float, total_price: float, event_date: date):
        self.event_type = event_type
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price
        self.event_date = event_date


class FakeSession:
    """
    DB stub for generate_invoice: returns a Client, a list of BillingEvents, records Invoice/InvoiceLine adds.
    """

    def __init__(self, *, client, events):
        self._client = client
        self._events = events
        self.added = []
        self.committed = False

    def scalar(self, stmt):
        # First scalar(select(Client)...) call returns client
        return self._client

    def scalars(self, stmt):
        return _ScalarResult(self._events)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        # Give invoice an id if it's missing (simulate DB default)
        for o in self.added:
            if o.__class__.__name__ == "Invoice" and getattr(o, "id", None) is None:
                o.id = uuid.uuid4()

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


def test_generate_invoice_groups_by_event_type_and_totals_match():
    client_id = uuid.uuid4()
    events = [
        FakeBillingEvent(event_type="STORAGE_DAY", quantity=2, unit_price=10.0, total_price=20.0, event_date=date(2025, 1, 1)),
        FakeBillingEvent(event_type="STORAGE_DAY", quantity=1, unit_price=10.0, total_price=10.0, event_date=date(2025, 1, 2)),
        FakeBillingEvent(event_type="INBOUND_LINE", quantity=3, unit_price=1.0, total_price=3.0, event_date=date(2025, 1, 2)),
    ]
    db = FakeSession(
        client=FakeClient(billing_currency="EUR"),
        events=events,
    )

    inv = billing_service.generate_invoice(db, client_id=client_id, period_start=date(2025, 1, 1), period_end=date(2025, 1, 31))
    assert db.committed is True
    assert float(inv.total) == pytest.approx(33.0)

    # Traceability: events are linked to the generated invoice
    assert all(getattr(e, "invoice_id", None) == inv.id for e in events)

    lines = [o for o in db.added if o.__class__.__name__ == "InvoiceLine"]
    assert len(lines) == 2  # STORAGE_DAY + INBOUND_LINE
    by_key = {l.description_key: l for l in lines}
    assert by_key["invoice.line.STORAGE_DAY"].quantity == 3
    assert float(by_key["invoice.line.STORAGE_DAY"].total_price) == pytest.approx(30.0)
    assert by_key["invoice.line.INBOUND_LINE"].quantity == 3


def test_generate_invoice_rejects_no_events():
    client_id = uuid.uuid4()
    db = FakeSession(client=FakeClient(), events=[])
    with pytest.raises(HTTPException) as e:
        billing_service.generate_invoice(db, client_id=client_id, period_start=date(2025, 1, 1), period_end=date(2025, 1, 31))
    assert e.value.status_code == 409


