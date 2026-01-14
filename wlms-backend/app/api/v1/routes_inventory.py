import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user
from app.db.session import get_db
from app.models.inventory import InventoryBalance, InventoryLedger
from app.models.location import Location
from app.models.product import Product
from app.models.product_batch import ProductBatch
from app.models.warehouse import Warehouse
from app.models.user import User
from app.schemas.inventory import InventoryBalanceOut
from app.schemas.inventory_moves import InventoryLedgerOut, InventoryTransfer
from app.services.inventory_service import move_on_hand
from app.services.audit_service import audit_log

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/balances", response_model=list[InventoryBalanceOut])
def list_balances(
    client_id: str | None = Query(default=None),
    warehouse_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    expiry_after: str | None = Query(default=None),
    expiry_before: str | None = Query(default=None),
    product_category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventoryBalanceOut]:
    stmt = select(InventoryBalance).where(InventoryBalance.tenant_id == user.tenant_id)

    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(InventoryBalance.client_id == user.client_id)
    elif client_id:
        try:
            cid = uuid.UUID(client_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
        stmt = stmt.where(InventoryBalance.client_id == cid)

    if warehouse_id:
        try:
            wid = uuid.UUID(warehouse_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid warehouse_id")
        stmt = stmt.where(InventoryBalance.warehouse_id == wid)

    if product_id:
        try:
            pid = uuid.UUID(product_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product_id")
        stmt = stmt.where(InventoryBalance.product_id == pid)

    if location_id:
        try:
            lid = uuid.UUID(location_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location_id")
        stmt = stmt.where(InventoryBalance.location_id == lid)

    if product_category:
        stmt = stmt.join(Product, InventoryBalance.product_id == Product.id).where(Product.category == product_category)

    if expiry_after or expiry_before:
        stmt = stmt.join(ProductBatch, InventoryBalance.batch_id == ProductBatch.id)
        if expiry_after:
            try:
                da = date.fromisoformat(expiry_after)
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expiry_after")
            stmt = stmt.where(ProductBatch.expiry_date >= da)
        if expiry_before:
            try:
                dbefore = date.fromisoformat(expiry_before)
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expiry_before")
            stmt = stmt.where(ProductBatch.expiry_date <= dbefore)

    items = db.scalars(stmt).all()
    return [
        InventoryBalanceOut(
            id=b.id,
            tenant_id=b.tenant_id,
            client_id=b.client_id,
            warehouse_id=b.warehouse_id,
            product_id=b.product_id,
            batch_id=b.batch_id,
            location_id=b.location_id,
            on_hand_qty=b.on_hand_qty,
            reserved_qty=b.reserved_qty,
            available_qty=b.available_qty,
        )
        for b in items
    ]


@router.get("/movements", response_model=list[InventoryLedgerOut])
def list_movements(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventoryLedgerOut]:
    stmt = select(InventoryLedger).where(InventoryLedger.tenant_id == user.tenant_id).order_by(InventoryLedger.created_at.desc()).limit(limit)
    if is_client_user(user) and user.client_id is not None:
        stmt = stmt.where(InventoryLedger.client_id == user.client_id)
    rows = db.scalars(stmt).all()
    return [
        InventoryLedgerOut(
            id=r.id,
            tenant_id=r.tenant_id,
            client_id=r.client_id,
            warehouse_id=r.warehouse_id,
            product_id=r.product_id,
            batch_id=r.batch_id,
            from_location_id=r.from_location_id,
            to_location_id=r.to_location_id,
            qty_delta=r.qty_delta,
            event_type=r.event_type,
            reference_type=r.reference_type,
            reference_id=r.reference_id,
        )
        for r in rows
    ]


@router.post("/transfer")
def transfer(
    payload: InventoryTransfer,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    if payload.qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    from_loc = db.scalar(select(Location).where(Location.id == payload.from_location_id))
    to_loc = db.scalar(select(Location).where(Location.id == payload.to_location_id))
    if from_loc is None or to_loc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location")
    if from_loc.warehouse_id != to_loc.warehouse_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Locations must be in same warehouse")

    wh = db.scalar(select(Warehouse).where(Warehouse.id == from_loc.warehouse_id, Warehouse.tenant_id == user.tenant_id))
    if wh is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    # Determine client_id from the source balance row (authoritative)
    bal = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.tenant_id == user.tenant_id,
            InventoryBalance.location_id == payload.from_location_id,
            InventoryBalance.product_id == payload.product_id,
            InventoryBalance.batch_id == payload.batch_id,
        )
    )
    if bal is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No stock at from_location_id for that item")

    move_on_hand(
        db,
        tenant_id=user.tenant_id,
        client_id=bal.client_id,
        warehouse_id=bal.warehouse_id,
        product_id=bal.product_id,
        batch_id=bal.batch_id,
        from_location_id=payload.from_location_id,
        to_location_id=payload.to_location_id,
        qty=payload.qty,
        reference_type="MANUAL",
        reference_id=str(user.id),
        performed_by_user_id=user.id,
        event_type="TRANSFER",
    )

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="inventory.transfer",
        entity_type="InventoryMove",
        entity_id=f"{payload.from_location_id}->{payload.to_location_id}",
        after={
            "product_id": str(payload.product_id),
            "batch_id": str(payload.batch_id) if payload.batch_id else None,
            "qty": payload.qty,
        },
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


