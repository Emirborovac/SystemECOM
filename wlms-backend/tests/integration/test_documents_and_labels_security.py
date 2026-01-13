import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.client import Client
from app.models.file import File
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


def test_location_labels_pdf_scoped_to_tenant(client: TestClient, db):
    t1 = Tenant(name=f"T1-{uuid.uuid4().hex[:6]}")
    t2 = Tenant(name=f"T2-{uuid.uuid4().hex[:6]}")
    db.add(t1)
    db.add(t2)
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    w1 = Warehouse(tenant_id=t1.id, name="WH1")
    db.add(w1)
    db.commit()
    db.refresh(w1)

    z1 = WarehouseZone(warehouse_id=w1.id, name="Z", zone_type="STORAGE")
    db.add(z1)
    db.commit()
    db.refresh(z1)

    l1 = Location(warehouse_id=w1.id, zone_id=z1.id, code="A-01-01", barcode_value="A-01-01")
    db.add(l1)
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

    res = client.get(f"/api/v1/warehouses/{w1.id}/locations/labels.pdf", headers=_auth_headers(user=admin_t2))
    # We return 404 if tenant mismatch, so we don't leak existence.
    assert res.status_code == 404


def test_file_download_scoped_to_tenant(client: TestClient, db):
    t1 = Tenant(name=f"T1-{uuid.uuid4().hex[:6]}")
    t2 = Tenant(name=f"T2-{uuid.uuid4().hex[:6]}")
    db.add(t1)
    db.add(t2)
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    c1 = Client(tenant_id=t1.id, name="Client1", billing_currency="EUR", preferred_language="en")
    db.add(c1)
    db.commit()
    db.refresh(c1)

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
    db.refresh(f)

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

    res = client.get(f"/api/v1/files/{f.id}/download", headers=_auth_headers(user=admin_t2))
    assert res.status_code == 404


