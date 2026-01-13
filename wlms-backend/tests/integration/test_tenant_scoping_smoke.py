import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.client import Client
from app.models.file import File
from app.models.inventory import InventoryBalance
from app.models.location import Location
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone


def _auth_headers(*, user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
        client_id=str(user.client_id) if user.client_id else None,
        token_version=int(getattr(user, "token_version", 0) or 0),
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_endpoints_are_scoped_to_tenant(client: TestClient, db):
    t1 = Tenant(name=f"T1-{uuid.uuid4().hex[:6]}")
    t2 = Tenant(name=f"T2-{uuid.uuid4().hex[:6]}")
    db.add(t1)
    db.add(t2)
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    c1 = Client(tenant_id=t1.id, name="C1", billing_currency="EUR", preferred_language="en")
    w1 = Warehouse(tenant_id=t1.id, name="WH1")
    db.add(c1)
    db.add(w1)
    db.commit()
    db.refresh(c1)
    db.refresh(w1)

    z1 = WarehouseZone(warehouse_id=w1.id, name="Z1", zone_type="STORAGE")
    db.add(z1)
    db.commit()
    db.refresh(z1)

    loc = Location(warehouse_id=w1.id, zone_id=z1.id, code="A-01-01", barcode_value="A-01-01")
    prod = Product(tenant_id=t1.id, client_id=c1.id, sku="SKU1", name="Prod", barcode="BC1", category="CAT")
    db.add(loc)
    db.add(prod)
    db.commit()
    db.refresh(loc)
    db.refresh(prod)

    bal = InventoryBalance(
        tenant_id=t1.id,
        client_id=c1.id,
        warehouse_id=w1.id,
        product_id=prod.id,
        batch_id=None,
        location_id=loc.id,
        on_hand_qty=5,
        reserved_qty=0,
        available_qty=5,
    )
    db.add(bal)

    f = File(
        tenant_id=t1.id,
        client_id=c1.id,
        file_type="INVOICE_PDF",
        storage_provider="LOCAL",
        storage_key="does-not-exist",
        original_name="x.pdf",
        mime_type="application/pdf",
        size_bytes=0,
        created_by_user_id=None,
    )
    db.add(f)
    db.commit()

    admin_t2 = User(
        tenant_id=t2.id,
        client_id=None,
        email=f"a2-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pw"),
        full_name="Admin2",
        role="WAREHOUSE_ADMIN",
        language_pref="en",
        token_version=0,
        is_active=True,
    )
    db.add(admin_t2)
    db.commit()
    db.refresh(admin_t2)

    # Warehouses list should be empty (tenant2 cannot see tenant1 warehouses)
    res = client.get("/api/v1/warehouses", headers=_auth_headers(user=admin_t2))
    assert res.status_code == 200
    assert res.json() == []

    # Inventory balances list should be empty
    res = client.get("/api/v1/inventory/balances", headers=_auth_headers(user=admin_t2))
    assert res.status_code == 200
    assert res.json() == []

    # Files list should be empty
    res = client.get("/api/v1/files", headers=_auth_headers(user=admin_t2))
    assert res.status_code == 200
    assert res.json() == []


