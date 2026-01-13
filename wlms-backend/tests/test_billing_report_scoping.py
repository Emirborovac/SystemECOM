import uuid

from app.api.v1.routes_billing import get_invoice, list_invoices
from app.api.v1.routes_reports import billing_events_report
from app.models.user import User


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeSession:
    def __init__(self):
        self.last_stmt = None

    def scalars(self, stmt):
        self.last_stmt = stmt
        return _ScalarResult([])

    def scalar(self, stmt):
        self.last_stmt = stmt
        return None


def _user(*, tenant_id: int, client_id: uuid.UUID | None) -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        email="u@example.com",
        password_hash="x",
        full_name="U",
        role="WAREHOUSE_ADMIN",
        language_pref="en",
        is_active=True,
    )


def test_list_invoices_scoped_by_tenant():
    db = FakeSession()
    user = _user(tenant_id=77, client_id=None)
    list_invoices(db=db, user=user)
    compiled = str(db.last_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "clients.tenant_id" in compiled
    assert "77" in compiled


def test_get_invoice_scoped_by_tenant():
    db = FakeSession()
    user = _user(tenant_id=55, client_id=None)
    get_invoice(invoice_id=str(uuid.uuid4()), db=db, user=user)
    compiled = str(db.last_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "clients.tenant_id" in compiled
    assert "55" in compiled


def test_billing_events_report_scoped_by_tenant():
    db = FakeSession()
    user = _user(tenant_id=12, client_id=None)
    # dates are validated by FastAPI normally; we just need stmt construction
    import datetime as _dt

    billing_events_report(start=_dt.date(2025, 1, 1), end=_dt.date(2025, 1, 2), format="json", db=db, user=user)
    compiled = str(db.last_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "clients.tenant_id" in compiled
    assert "12" in compiled


