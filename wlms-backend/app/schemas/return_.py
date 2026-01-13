import uuid

from pydantic import BaseModel, Field


class ReturnCreate(BaseModel):
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    notes: str | None = None


class ReturnOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    status: str
    notes: str | None


class ReturnScanLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int = Field(ge=1)
    disposition: str  # RESTOCK/QUARANTINE/SCRAP
    to_location_id: uuid.UUID | None = None


