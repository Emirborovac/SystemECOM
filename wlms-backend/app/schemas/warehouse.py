import uuid

from pydantic import BaseModel


class WarehouseCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None


class WarehouseOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    name: str
    address: str | None
    timezone: str | None


class WarehouseZoneCreate(BaseModel):
    name: str
    zone_type: str  # STAGING/STORAGE/PACKING/RETURNS/QUARANTINE


class WarehouseZoneOut(BaseModel):
    id: int
    warehouse_id: uuid.UUID
    name: str
    zone_type: str


class LocationCreate(BaseModel):
    zone_id: int
    code: str
    barcode_value: str
    aisle: str | None = None
    rack: str | None = None
    level: str | None = None
    bin: str | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    zone_id: int
    code: str
    barcode_value: str
    aisle: str | None
    rack: str | None
    level: str | None
    bin: str | None
    is_active: bool


