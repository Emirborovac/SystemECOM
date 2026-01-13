import uuid
from datetime import date

from pydantic import BaseModel


class PriceListOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    effective_from: date
    rules_json: dict


class PriceListUpsert(BaseModel):
    effective_from: date
    rules_json: dict


class RunDailyStorageBody(BaseModel):
    event_date: date


class GenerateInvoiceBody(BaseModel):
    client_id: uuid.UUID
    period_start: date
    period_end: date
    language: str | None = None


class InvoiceOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    currency: str
    subtotal: float
    tax_total: float
    total: float
    pdf_file_id: uuid.UUID | None


class InvoiceLineOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    description_key: str
    description_params_json: dict
    quantity: int
    unit_price: float
    total_price: float
    tax_rate: float
    drilldown_query_json: dict


class BillingEventOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID | None
    client_id: uuid.UUID
    warehouse_id: uuid.UUID
    event_type: str
    quantity: int
    unit_price: float
    total_price: float
    reference_type: str
    reference_id: str
    event_date: date

