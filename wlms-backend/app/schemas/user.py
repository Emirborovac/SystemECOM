import uuid

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str | None = None
    email: EmailStr
    password: str
    full_name: str = ""
    role: str
    language_pref: str = "en"
    client_id: uuid.UUID | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    tenant_id: int
    client_id: uuid.UUID | None
    email: EmailStr
    username: str | None = None
    full_name: str
    role: str
    language_pref: str
    is_active: bool


class UserMeUpdate(BaseModel):
    full_name: str | None = None
    language_pref: str | None = None

