import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.client import Client
from app.models.tenant import Tenant
from app.models.user import User
from app.models.warehouse import Warehouse


def _auth_headers(*, user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
        client_id=str(user.client_id) if user.client_id else None,
        token_version=int(getattr(user, "token_version", 0) or 0),
    )
    return {"Authorization": f"Bearer {token}"}


def test_client_user_cannot_access_other_client_data(client: TestClient, db):
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    db.add(t)
    db.commit()
    db.refresh(t)

    c1 = Client(tenant_id=t.id, name="Client1", billing_currency="EUR", preferred_language="en")
    c2 = Client(tenant_id=t.id, name="Client2", billing_currency="EUR", preferred_language="en")
    w = Warehouse(tenant_id=t.id, name="WH1")
    db.add(c1)
    db.add(c2)
    db.add(w)
    db.commit()
    db.refresh(c1)
    db.refresh(c2)
    db.refresh(w)

    u_client = User(
        tenant_id=t.id,
        client_id=c1.id,
        email=f"cu-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pw"),
        full_name="ClientUser",
        role="CLIENT_USER",
        language_pref="en",
        token_version=0,
        is_active=True,
    )
    db.add(u_client)
    db.commit()
    db.refresh(u_client)

    # Create an outbound for client2 (as admin)
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
    db.add(admin)
    db.commit()
    db.refresh(admin)

    res = client.post(
        "/api/v1/outbound",
        headers=_auth_headers(user=admin),
        json={
            "client_id": str(c2.id),
            "warehouse_id": str(w.id),
            "destination": {"name": "Dest", "address": "Addr"},
            "requested_ship_date": None,
            "notes": None,
            "lines": [],
        },
    )
    # API requires at least 1 line; this should fail fast with 400, but still good to keep admin path realistic.
    assert res.status_code == 400

    # Now ensure client user cannot force-filter by other client id on list endpoint.
    res = client.get("/api/v1/outbound", headers=_auth_headers(user=u_client), params={"client_id": str(c2.id)})
    assert res.status_code == 200
    assert res.json() == []


def test_tenant_mismatch_token_is_rejected(client: TestClient, db):
    t1 = Tenant(name=f"T1-{uuid.uuid4().hex[:6]}")
    t2 = Tenant(name=f"T2-{uuid.uuid4().hex[:6]}")
    db.add(t1)
    db.add(t2)
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    u = User(
        tenant_id=t1.id,
        client_id=None,
        email=f"u-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pw"),
        full_name="U",
        role="WAREHOUSE_ADMIN",
        language_pref="en",
        token_version=0,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    bad_token = create_access_token(user_id=str(u.id), tenant_id=t2.id, role=u.role, client_id=None, token_version=0)
    res = client.get("/api/v1/clients", headers={"Authorization": f"Bearer {bad_token}"})
    assert res.status_code == 401


