import uuid

from pydantic import BaseModel


class InventoryBalanceOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    location_id: uuid.UUID
    on_hand_qty: int
    reserved_qty: int
    available_qty: int


