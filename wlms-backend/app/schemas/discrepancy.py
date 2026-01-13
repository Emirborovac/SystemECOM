import uuid

from pydantic import BaseModel, Field


class DiscrepancyCreate(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    location_id: uuid.UUID
    counted_qty: int = Field(ge=0)
    reason: str | None = None


class DiscrepancyOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    location_id: uuid.UUID
    system_qty: int
    counted_qty: int
    delta_qty: int
    reason: str | None
    status: str


