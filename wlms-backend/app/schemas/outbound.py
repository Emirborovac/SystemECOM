import uuid
from datetime import date

from pydantic import BaseModel, Field


class OutboundDestination(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=1000)
    contact: str | None = None
    notes: str | None = None


class OutboundLineCreate(BaseModel):
    product_id: uuid.UUID
    qty: int = Field(ge=1)
    uom: str | None = None  # piece/carton/pallet


class OutboundCreate(BaseModel):
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    requested_ship_date: date | None = None
    destination: OutboundDestination
    notes: str | None = None
    lines: list[OutboundLineCreate]


class OutboundOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    order_number: str
    status: str
    destination_json: dict
    requested_ship_date: date | None


class OutboundLineOut(BaseModel):
    id: int
    outbound_id: uuid.UUID
    product_id: uuid.UUID
    requested_qty: int
    reserved_qty: int
    picked_qty: int


