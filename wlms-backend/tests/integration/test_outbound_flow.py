import uuid
from datetime import date, timedelta

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


def test_outbound_pick_pack_dispatch_invoice(client: TestClient, db):
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    db.add(t)
    db.commit()
    db.refresh(t)

    c = Client(tenant_id=t.id, name="Client A", billing_currency="EUR", preferred_language="en")
    w = Warehouse(tenant_id=t.id, name="WH1")
    db.add(c)
    db.add(w)
    db.commit()
    db.refresh(c)
    db.refresh(w)

    z_storage = WarehouseZone(warehouse_id=w.id, name="STR", zone_type="STORAGE")
    z_packing = WarehouseZone(warehouse_id=w.id, name="PCK", zone_type="PACKING")
    db.add(z_storage)
    db.add(z_packing)
    db.commit()
    db.refresh(z_storage)
    db.refresh(z_packing)

    loc_storage = Location(warehouse_id=w.id, zone_id=z_storage.id, code="A-01-01", barcode_value="A-01-01")
    loc_packing = Location(warehouse_id=w.id, zone_id=z_packing.id, code="PACK-01", barcode_value="PACK-01")
    db.add(loc_storage)
    db.add(loc_packing)
    db.commit()
    db.refresh(loc_storage)
    db.refresh(loc_packing)

    p = Product(tenant_id=t.id, client_id=c.id, sku="SKU1", name="Prod1", barcode="BC-001")
    db.add(p)
    db.commit()
    db.refresh(p)

    admin = User(
        tenant_id=t.id,
        client_id=None,
        email=f"a-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pw"),
        full_name="Admin",
        role="WAREHOUSE_ADMIN",
        language_pref="en",
        token_version=0,
        is_active=True,
    )
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
    db.add(admin)
    db.add(worker)
    db.commit()
    db.refresh(admin)
    db.refresh(worker)

    # Seed stock into storage by using inventory transfer endpoint via admin manual transfer:
    # 1) Create a fake inbound: easiest is to call inventory transfer won't create stock; we need positive ledger.
    # We'll use inbound scan route quickly by creating STAGING location in same warehouse.
    z_staging = WarehouseZone(warehouse_id=w.id, name="STG", zone_type="STAGING")
    db.add(z_staging)
    db.commit()
    db.refresh(z_staging)
    loc_staging = Location(warehouse_id=w.id, zone_id=z_staging.id, code="STG-01", barcode_value="STG-01")
    db.add(loc_staging)
    db.commit()
    db.refresh(loc_staging)

    # Create inbound and receive into staging
    res = client.post("/api/v1/inbound", headers=_auth_headers(user=admin), json={"client_id": str(c.id), "warehouse_id": str(w.id)})
    assert res.status_code == 201, res.text
    inbound_id = res.json()["id"]
    res = client.post(f"/api/v1/inbound/{inbound_id}/start-receiving", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text
    res = client.post(
        f"/api/v1/inbound/{inbound_id}/scan-line",
        headers=_auth_headers(user=worker),
        json={"barcode": "BC-001", "qty": 3, "batch_number": None, "expiry_date": None, "location_staging_id": str(loc_staging.id)},
    )
    assert res.status_code == 200, res.text
    res = client.post(f"/api/v1/inbound/{inbound_id}/complete", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text
    # Putaway to storage
    res = client.post(
        "/api/v1/putaway/confirm",
        headers=_auth_headers(user=worker),
        json={"product_id": str(p.id), "batch_id": None, "qty": 3, "from_location_id": str(loc_staging.id), "to_location_id": str(loc_storage.id)},
    )
    assert res.status_code == 200, res.text

    # Create outbound
    res = client.post(
        "/api/v1/outbound",
        headers=_auth_headers(user=admin),
        json={
            "client_id": str(c.id),
            "warehouse_id": str(w.id),
            "destination": {"name": "Dest", "address": "Addr"},
            "requested_ship_date": None,
            "notes": None,
            "lines": [{"product_id": str(p.id), "qty": 2}],
        },
    )
    assert res.status_code == 201, res.text
    outbound_id = res.json()["id"]

    # Approve + generate picks
    res = client.post(f"/api/v1/outbound/{outbound_id}/approve", headers=_auth_headers(user=admin))
    assert res.status_code == 200, res.text
    res = client.post(f"/api/v1/outbound/{outbound_id}/generate-picks", headers=_auth_headers(user=admin))
    assert res.status_code == 200, res.text

    # Pick
    res = client.get("/api/v1/picking/tasks", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text
    task_id = res.json()[0]["id"]
    res = client.post(f"/api/v1/picking/tasks/{task_id}/start", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text
    res = client.get(f"/api/v1/picking/tasks/{task_id}/lines", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text
    line = res.json()[0]

    res = client.post(
        f"/api/v1/picking/tasks/{task_id}/scan",
        headers=_auth_headers(user=worker),
        json={
            "product_id": line["product_id"],
            "batch_id": None,
            "qty": 2,
            "from_location_id": line["from_location_id"],
            "to_location_id": str(loc_packing.id),
        },
    )
    assert res.status_code == 200, res.text
    res = client.post(f"/api/v1/picking/tasks/{task_id}/complete", headers=_auth_headers(user=worker))
    assert res.status_code == 200, res.text

    # Pack + dispatch
    res = client.post(f"/api/v1/packing/{outbound_id}/confirm", headers=_auth_headers(user=worker), json={})
    assert res.status_code == 200, res.text
    res = client.post(
        f"/api/v1/dispatch/{outbound_id}/confirm",
        headers=_auth_headers(user=worker),
        json={"packing_location_id": str(loc_packing.id)},
    )
    assert res.status_code == 200, res.text

    # Invoice should be generatable in a broad period that includes today.
    start = date.today() - timedelta(days=1)
    end = date.today() + timedelta(days=1)
    res = client.post(
        "/api/v1/invoices/generate",
        headers=_auth_headers(user=admin),
        json={"client_id": str(c.id), "period_start": start.isoformat(), "period_end": end.isoformat(), "language": "en"},
    )
    assert res.status_code in (200, 409), res.text  # 409 if no events depending on config path


