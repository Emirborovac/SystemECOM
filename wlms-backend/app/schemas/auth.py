from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    # v1: allow username-style login; accept either username or email in this field.
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifySupervisorRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    tenant_id: int
    client_id: str | None
    email: EmailStr
    full_name: str
    role: str
    language_pref: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


