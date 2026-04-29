from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class CurrentUser(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    is_active: bool
    is_superuser: bool
    roles: list["RoleBrief"] = []
    permissions: list[str] = []


class RoleBrief(BaseModel):
    id: str
    name: str
    display_name: str | None = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    display_name: str | None = None
    phone: str | None = None
    email: str | None = None
    role_ids: list[str] = []


class UserUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None
    role_ids: list[str] | None = None


class UserBrief(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    is_superuser: bool
    roles: list[RoleBrief] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
