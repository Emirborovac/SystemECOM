import uuid
from pydantic import BaseModel


class InventoryTransfer(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID


class InventoryLedgerOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    from_location_id: uuid.UUID | None
    to_location_id: uuid.UUID | None
    qty_delta: int
    event_type: str
    reference_type: str
    reference_id: str

