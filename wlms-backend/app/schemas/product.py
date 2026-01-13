import uuid

from pydantic import BaseModel


class ProductCreate(BaseModel):
    client_id: uuid.UUID
    sku: str
    name: str
    description: str | None = None
    category: str | None = None
    barcode: str | None = None
    uom: str = "piece"  # piece/carton/pallet
    carton_qty: int | None = None
    pallet_qty: int | None = None
    weight_kg: str | None = None
    dims_cm_json: dict | None = None
    lot_tracking_enabled: bool = False
    expiry_tracking_enabled: bool = False


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    barcode: str | None = None
    uom: str | None = None
    carton_qty: int | None = None
    pallet_qty: int | None = None
    weight_kg: str | None = None
    dims_cm_json: dict | None = None
    lot_tracking_enabled: bool | None = None
    expiry_tracking_enabled: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    sku: str
    name: str
    description: str | None
    category: str | None
    barcode: str | None
    uom: str
    carton_qty: int | None
    pallet_qty: int | None
    weight_kg: str | None
    dims_cm_json: dict | None
    lot_tracking_enabled: bool
    expiry_tracking_enabled: bool


