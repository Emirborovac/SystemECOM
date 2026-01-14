import uuid

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as UploadFileParam, status
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_warehouse_staff
from app.db.session import get_db
from app.models.location import Location
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_zone import WarehouseZone
from app.services.audit_service import audit_log
from app.services.label_service import render_location_labels_pdf
from app.schemas.warehouse import (
    LocationCreate,
    LocationOut,
    WarehouseCreate,
    WarehouseOut,
    WarehouseUpdate,
    WarehouseZoneCreate,
    WarehouseZoneOut,
)

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)) -> list[WarehouseOut]:
    items = db.scalars(select(Warehouse).where(Warehouse.tenant_id == user.tenant_id)).all()
    return [
        WarehouseOut(id=w.id, tenant_id=w.tenant_id, name=w.name, address=w.address, timezone=w.timezone)
        for w in items
    ]


@router.post("", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> WarehouseOut:
    w = Warehouse(tenant_id=user.tenant_id, name=payload.name, address=payload.address, timezone=payload.timezone)
    db.add(w)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="warehouses.create",
        entity_type="Warehouse",
        entity_id=str(w.id),
        after={"id": str(w.id), "name": w.name},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(w)
    return WarehouseOut(id=w.id, tenant_id=w.tenant_id, name=w.name, address=w.address, timezone=w.timezone)


@router.put("/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: str,
    payload: WarehouseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> WarehouseOut:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    before = {"id": str(w.id), "name": w.name, "address": w.address, "timezone": w.timezone}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(w, k, v)
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="warehouses.update",
        entity_type="Warehouse",
        entity_id=str(w.id),
        before=before,
        after={"id": str(w.id), "name": w.name, "address": w.address, "timezone": w.timezone},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(w)
    return WarehouseOut(id=w.id, tenant_id=w.tenant_id, name=w.name, address=w.address, timezone=w.timezone)


@router.get("/{warehouse_id}/zones", response_model=list[WarehouseZoneOut])
def list_zones(
    warehouse_id: str, db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)
) -> list[WarehouseZoneOut]:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse.id).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    zones = db.scalars(select(WarehouseZone).where(WarehouseZone.warehouse_id == wid)).all()
    return [WarehouseZoneOut(id=z.id, warehouse_id=z.warehouse_id, name=z.name, zone_type=z.zone_type) for z in zones]


@router.post("/{warehouse_id}/zones", response_model=WarehouseZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(
    warehouse_id: str,
    payload: WarehouseZoneCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> WarehouseZoneOut:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse.id).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    z = WarehouseZone(warehouse_id=wid, name=payload.name, zone_type=payload.zone_type)
    db.add(z)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="warehouse_zones.create",
        entity_type="WarehouseZone",
        entity_id=str(z.id),
        after={"id": z.id, "warehouse_id": str(z.warehouse_id), "name": z.name, "zone_type": z.zone_type},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(z)
    return WarehouseZoneOut(id=z.id, warehouse_id=z.warehouse_id, name=z.name, zone_type=z.zone_type)


@router.get("/{warehouse_id}/locations", response_model=list[LocationOut])
def list_locations(
    warehouse_id: str, db: Session = Depends(get_db), user: User = Depends(require_warehouse_staff)
) -> list[LocationOut]:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse.id).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    locs = db.scalars(select(Location).where(Location.warehouse_id == wid)).all()
    return [
        LocationOut(
            id=l.id,
            warehouse_id=l.warehouse_id,
            zone_id=l.zone_id,
            code=l.code,
            barcode_value=l.barcode_value,
            aisle=l.aisle,
            rack=l.rack,
            level=l.level,
            bin=l.bin,
            is_active=l.is_active,
        )
        for l in locs
    ]


@router.post("/{warehouse_id}/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    warehouse_id: str,
    payload: LocationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> LocationOut:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse.id).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # zone must belong to this warehouse
    zone = db.scalar(select(WarehouseZone).where(WarehouseZone.id == payload.zone_id, WarehouseZone.warehouse_id == wid))
    if zone is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zone")

    l = Location(
        warehouse_id=wid,
        zone_id=payload.zone_id,
        code=payload.code,
        barcode_value=payload.barcode_value,
        aisle=payload.aisle,
        rack=payload.rack,
        level=payload.level,
        bin=payload.bin,
    )
    db.add(l)
    db.flush()
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="locations.create",
        entity_type="Location",
        entity_id=str(l.id),
        after={"id": str(l.id), "warehouse_id": str(l.warehouse_id), "zone_id": l.zone_id, "code": l.code},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(l)
    return LocationOut(
        id=l.id,
        warehouse_id=l.warehouse_id,
        zone_id=l.zone_id,
        code=l.code,
        barcode_value=l.barcode_value,
        aisle=l.aisle,
        rack=l.rack,
        level=l.level,
        bin=l.bin,
        is_active=l.is_active,
    )


@router.post("/{warehouse_id}/locations/import-csv")
def import_locations_csv(
    warehouse_id: str,
    zone_id: int,
    request: Request,
    file: UploadFile = UploadFileParam(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
) -> dict:
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    z = db.scalar(select(WarehouseZone).where(WarehouseZone.id == zone_id, WarehouseZone.warehouse_id == wid))
    if z is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zone_id")

    raw = file.file.read()
    try:
        text = raw.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8")

    reader = csv.DictReader(io.StringIO(text))
    errors: list[dict] = []
    created = 0

    # cache existing codes
    existing_codes = {
        r[0] for r in db.execute(select(Location.code).where(Location.warehouse_id == wid)).all()
    }
    seen_in_file: set[str] = set()

    for idx, row in enumerate(reader, start=2):  # header is row 1
        code = (row.get("code") or "").strip()
        if not code:
            errors.append({"row": idx, "field": "code", "message": "required"})
            continue
        if code in seen_in_file:
            errors.append({"row": idx, "field": "code", "message": "duplicate in file"})
            continue
        seen_in_file.add(code)
        if code in existing_codes:
            errors.append({"row": idx, "field": "code", "message": "already exists"})
            continue

        barcode_value = (row.get("barcode_value") or "").strip() or code
        l = Location(
            warehouse_id=wid,
            zone_id=zone_id,
            code=code,
            barcode_value=barcode_value,
            aisle=(row.get("aisle") or "").strip() or None,
            rack=(row.get("rack") or "").strip() or None,
            level=(row.get("level") or "").strip() or None,
            bin=(row.get("bin") or "").strip() or None,
        )
        db.add(l)
        db.flush()
        existing_codes.add(code)
        created += 1

    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="locations.import_csv",
        entity_type="Warehouse",
        entity_id=str(wid),
        after={"created": created, "errors": len(errors), "zone_id": zone_id},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"created": created, "errors": errors}


@router.get("/{warehouse_id}/locations/labels.pdf")
def location_labels_pdf(
    warehouse_id: str,
    zone_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_warehouse_staff),
):
    try:
        wid = uuid.UUID(warehouse_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    w = db.scalar(select(Warehouse).where(Warehouse.id == wid, Warehouse.tenant_id == user.tenant_id))
    if w is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    stmt = select(Location).where(Location.warehouse_id == wid)
    if zone_id is not None:
        stmt = stmt.where(Location.zone_id == zone_id)
    locs = db.scalars(stmt.order_by(Location.code.asc())).all()

    pdf = render_location_labels_pdf(
        locations=[{"code": l.code, "barcode_value": l.barcode_value} for l in locs],
        title=f"Location labels - {w.name}",
    )
    from fastapi import Response

    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="location_labels_{w.id}.pdf"'})


