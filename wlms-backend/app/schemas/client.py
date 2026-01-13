from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    address: str | None = None
    tax_id: str | None = None
    billing_currency: str = "EUR"
    vat_rate: float = 0.17
    preferred_language: str = "en"  # en/bs/de


class ClientUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    tax_id: str | None = None
    billing_currency: str | None = None
    vat_rate: float | None = None
    preferred_language: str | None = None


class ClientOut(BaseModel):
    id: str
    tenant_id: int
    name: str
    address: str | None
    tax_id: str | None
    billing_currency: str
    vat_rate: float
    preferred_language: str


