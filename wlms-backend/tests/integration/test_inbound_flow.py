import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.client import Client
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone
from app.models.location import Location


def _auth_headers(*, user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
        client_id=str(user.client_id) if user.client_id else None,
        token_version=int(getattr(user, "token_version", 0) or 0),
    )
    return {"Authorization": f"Bearer {token}"}


def test_inbound_receive_putaway_happy_path(client: TestClient, db):
    # Seed tenant + client + warehouse + zones + locations
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    db.add(t)
    db.commit()
    db.refresh(t)

    c = Client(tenant_id=t.id, name="Client A", billing_currency="EUR", preferred_language="en")
    db.add(c)
    w = Warehouse(tenant_id=t.id, name="WH1")
    db.add(w)
    db.commit()
    db.refresh(c)
    db.refresh(w)

    z_staging = WarehouseZone(warehouse_id=w.id, name="STG", zone_type="STAGING")
    z_storage = WarehouseZone(warehouse_id=w.id, name="STR", zone_type="STORAGE")
    db.add(z_staging)
    db.add(z_storage)
    db.commit()
    db.refresh(z_staging)
    db.refresh(z_storage)

    loc_staging = Location(warehouse_id=w.id, zone_id=z_staging.id, code="STG-01", barcode_value="STG-01")
    loc_storage = Location(warehouse_id=w.id, zone_id=z_storage.id, code="A-01-01", barcode_value="A-01-01")
    db.add(loc_staging)
    db.add(loc_storage)
    db.commit()
    db.refresh(loc_staging)
    db.refresh(loc_storage)

    p = Product(tenant_id=t.id, client_id=c.id, sku="SKU1", name="Prod1", barcode="BC-001")
    db.add(p)
    db.commit()
    db.refresh(p)

    worker = User(
        tenant_id=t.id,
        client_id=None,
        email=f"w-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pw"),
        full_name="Worker",
        role="WAREHOUSE_WORKER",
        language_pref="en",
        token_version=0,
        is_active=True,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    # Create inbound
    res = client.post(
        "/api/v1/inbound",
        headers=_auth_headers(user=worker),
        json={"client_id": str(c.id), "warehouse_id": str(w.id), "supplier": "Supp", "notes": "n"},
    )
    assert res.status_code == 201, res.text
    inbound = res.json()
    inbound_id = inbound["id"]

    # Start receiving
    res = client.post(f"/api/v1/inbound/{inbound_id}/start-receiving", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text

    # Scan into staging
    res = client.post(
        f"/api/v1/inbound/{inbound_id}/scan-line",
        headers=_auth_headers(user=worker),
        json={
            "barcode": "BC-001",
            "qty": 5,
            "batch_number": None,
            "expiry_date": None,
            "location_staging_id": str(loc_staging.id),
        },
    )
    assert res.status_code == 200, res.text

    # Complete inbound (should generate receiving PDF + billing events)
    res = client.post(f"/api/v1/inbound/{inbound_id}/complete", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text

    # Put-away move to storage
    res = client.post(
        "/api/v1/putaway/confirm",
        headers=_auth_headers(user=worker),
        json={
            "product_id": str(p.id),
            "batch_id": None,
            "qty": 5,
            "from_location_id": str(loc_staging.id),
            "to_location_id": str(loc_storage.id),
        },
    )
    assert res.status_code == 200, res.text

    # Verify balances exist (fast check via API)
    res = client.get(
        "/api/v1/inventory/balances",
        headers=_auth_headers(user=worker),
        params={"product_id": str(p.id), "location_id": str(loc_storage.id)},
    )
    assert res.status_code == 200, res.text
    rows = res.json()
    assert rows and rows[0]["on_hand_qty"] == 5


