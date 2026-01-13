import uuid

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File as UploadFileParam, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, is_client_user
from app.core.rbac import ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR
from app.db.session import get_db
from app.models.client import Client
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.audit_service import audit_log

router = APIRouter(prefix="/products", tags=["products"])


def _to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        tenant_id=p.tenant_id,
        client_id=p.client_id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        category=p.category,
        barcode=p.barcode,
        uom=p.uom,
        carton_qty=p.carton_qty,
        pallet_qty=p.pallet_qty,
        weight_kg=p.weight_kg,
        dims_cm_json=p.dims_cm_json,
        lot_tracking_enabled=p.lot_tracking_enabled,
        expiry_tracking_enabled=p.expiry_tracking_enabled,
    )


@router.get("", response_model=list[ProductOut])
def list_products(
    client_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProductOut]:
    stmt = select(Product).where(Product.tenant_id == user.tenant_id)

    if is_client_user(user):
        if user.client_id is None:
            return []
        stmt = stmt.where(Product.client_id == user.client_id)
    else:
        if client_id:
            try:
                cid = uuid.UUID(client_id)
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
            stmt = stmt.where(Product.client_id == cid)

    items = db.scalars(stmt).all()
    return [_to_out(p) for p in items]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> ProductOut:
    # Client users can only create for their own client_id
    if is_client_user(user):
        if user.client_id is None or user.client_id != payload.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    else:
        # Warehouse roles can create for any client in same tenant
        if user.role not in {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    # Ensure client belongs to tenant
    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    p = Product(
        tenant_id=user.tenant_id,
        client_id=payload.client_id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        barcode=payload.barcode,
        uom=payload.uom,
        carton_qty=payload.carton_qty,
        pallet_qty=payload.pallet_qty,
        weight_kg=payload.weight_kg,
        dims_cm_json=payload.dims_cm_json,
        lot_tracking_enabled=payload.lot_tracking_enabled,
        expiry_tracking_enabled=payload.expiry_tracking_enabled,
    )
    db.add(p)
    try:
        db.flush()
        audit_log(
            db,
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            action="products.create",
            entity_type="Product",
            entity_id=str(p.id),
            after=_to_out(p).model_dump(),
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU or barcode already exists for this client",
        )
    db.refresh(p)
    return _to_out(p)


@router.post("/import-csv")
def import_products_csv(
    client_id: str,
    file: UploadFile = UploadFileParam(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> dict:
    # Only warehouse roles can bulk import
    if user.role not in {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        cid = uuid.UUID(client_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    client = db.scalar(select(Client).where(Client.id == cid, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    raw = file.file.read()
    try:
        text = raw.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8")

    def _bool(v: str) -> bool:
        vv = (v or "").strip().lower()
        return vv in {"1", "true", "yes", "y", "on"}

    reader = csv.DictReader(io.StringIO(text))
    errors: list[dict] = []
    created = 0

    for idx, row in enumerate(reader, start=2):
        sku = (row.get("sku") or "").strip()
        name = (row.get("name") or "").strip()
        if not sku:
            errors.append({"row": idx, "field": "sku", "message": "required"})
            continue
        if not name:
            errors.append({"row": idx, "field": "name", "message": "required"})
            continue

        barcode = (row.get("barcode") or "").strip() or None
        uom = (row.get("uom") or "piece").strip() or "piece"
        carton_qty_raw = (row.get("carton_qty") or "").strip()
        carton_qty = int(carton_qty_raw) if carton_qty_raw.isdigit() else None

        try:
            with db.begin_nested():
                p = Product(
                    tenant_id=user.tenant_id,
                    client_id=cid,
                    sku=sku,
                    name=name,
                    category=(row.get("category") or "").strip() or None,
                    description=(row.get("description") or "").strip() or None,
                    barcode=barcode,
                    uom=uom,
                    carton_qty=carton_qty,
                    pallet_qty=int((row.get("pallet_qty") or "").strip()) if (row.get("pallet_qty") or "").strip().isdigit() else None,
                    lot_tracking_enabled=_bool(row.get("lot_tracking_enabled") or ""),
                    expiry_tracking_enabled=_bool(row.get("expiry_tracking_enabled") or ""),
                )
                db.add(p)
                db.flush()
                created += 1
        except IntegrityError:
            errors.append({"row": idx, "field": "sku/barcode", "message": "conflict"})
            continue

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="products.import_csv",
        entity_type="Client",
        entity_id=str(cid),
        after={"created": created, "errors": len(errors)},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"created": created, "errors": errors}


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductOut:
    try:
        pid = uuid.UUID(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    stmt = select(Product).where(Product.id == pid, Product.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        stmt = stmt.where(Product.client_id == user.client_id)

    p = db.scalar(stmt)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _to_out(p)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request | None = None,
) -> ProductOut:
    try:
        pid = uuid.UUID(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    stmt = select(Product).where(Product.id == pid, Product.tenant_id == user.tenant_id)
    if is_client_user(user):
        if user.client_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        stmt = stmt.where(Product.client_id == user.client_id)
    else:
        if user.role not in {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    p = db.scalar(stmt)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    before = _to_out(p).model_dump()
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)

    try:
        audit_log(
            db,
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            action="products.update",
            entity_type="Product",
            entity_id=str(p.id),
            before=before,
            after=_to_out(p).model_dump(),
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU or barcode already exists for this client",
        )
    db.refresh(p)
    return _to_out(p)


