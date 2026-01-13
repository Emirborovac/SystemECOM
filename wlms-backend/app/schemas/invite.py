import uuid

from pydantic import BaseModel, EmailStr


class InviteCreate(BaseModel):
    email: EmailStr
    client_id: uuid.UUID
    language: str = "en"


class InviteAccept(BaseModel):
    token: str
    password: str
    full_name: str = ""
    language_pref: str = "en"


