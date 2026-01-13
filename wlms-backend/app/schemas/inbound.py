import uuid
from datetime import date

from pydantic import BaseModel, Field


class InboundCreate(BaseModel):
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    supplier: str | None = None
    notes: str | None = None


class InboundOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    reference_number: str
    status: str
    supplier: str | None
    notes: str | None


class InboundScanLine(BaseModel):
    barcode: str = Field(min_length=1, max_length=128)
    qty: int = Field(ge=1)
    uom: str | None = None  # piece/carton/pallet
    batch_number: str | None = None
    expiry_date: date | None = None
    location_staging_id: uuid.UUID


class InboundLineOut(BaseModel):
    id: int
    inbound_id: uuid.UUID
    product_id: uuid.UUID
    expected_qty: int | None
    received_qty: int
    batch_id: uuid.UUID | None
    notes: str | None


