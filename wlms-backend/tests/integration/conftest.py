import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.base import Base

# Import models so Base.metadata is populated for create_all()
from app.models.audit import AuditLog  # noqa: F401
from app.models.auth_tokens import PasswordResetToken, UserInvite  # noqa: F401
from app.models.billing import BillingEvent, Invoice, InvoiceLine, PriceList  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.discrepancy import DiscrepancyReport  # noqa: F401
from app.models.file import File  # noqa: F401
from app.models.inbound import InboundLine, InboundShipment  # noqa: F401
from app.models.inventory import InventoryBalance, InventoryLedger  # noqa: F401
from app.models.inventory_reservation import InventoryReservation  # noqa: F401
from app.models.location import Location  # noqa: F401
from app.models.outbound import OutboundLine, OutboundOrder  # noqa: F401
from app.models.picking import PickingTask, PickingTaskLine  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.product_batch import ProductBatch  # noqa: F401
from app.models.return_ import Return, ReturnLine  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.warehouse import Warehouse  # noqa: F401
from app.models.warehouse_zone import WarehouseZone  # noqa: F401


def _test_db_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def engine():
    url = _test_db_url()
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run integration tests (requires Postgres).")
    eng = create_engine(url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


