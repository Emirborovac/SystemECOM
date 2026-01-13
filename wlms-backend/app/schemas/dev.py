from pydantic import BaseModel, EmailStr


class DevInitRequest(BaseModel):
    tenant_name: str = "SystemECOM"
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str = "Admin"
    admin_language_pref: str = "en"


