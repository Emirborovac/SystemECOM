import uuid

from pydantic import BaseModel, Field


class PutawayTask(BaseModel):
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    from_location_id: uuid.UUID
    on_hand_qty: int
    suggested_to_location_id: uuid.UUID | None = None
    suggested_to_location_code: str | None = None


class PutawayConfirm(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int = Field(ge=1)
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID


