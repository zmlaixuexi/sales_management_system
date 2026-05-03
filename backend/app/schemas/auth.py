import uuid as _uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.password_strength import validate_password_strength
from app.core.sanitize import sanitize_text as _sanitize


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=2048)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=6, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


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
    display_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=100)
    role_ids: list[str] = Field(default=[], max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("display_name", "email")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)

    @field_validator("username")
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        return _sanitize(v) or v

    @field_validator("phone")
    @classmethod
    def sanitize_phone(cls, v: str | None) -> str | None:
        return _sanitize(v)

    @field_validator("role_ids")
    @classmethod
    def validate_role_ids(cls, v: list[str]) -> list[str]:
        for rid in v:
            try:
                _uuid.UUID(rid)
            except (ValueError, AttributeError):
                raise ValueError(f"角色 ID 格式不正确: {rid}") from None
        return v


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    role_ids: list[str] | None = Field(None, max_length=50)

    @field_validator("display_name", "email", "phone")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)

    @field_validator("role_ids")
    @classmethod
    def validate_role_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for rid in v:
                try:
                    _uuid.UUID(rid)
                except (ValueError, AttributeError):
                    raise ValueError(f"角色 ID 格式不正确: {rid}") from None
        return v


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
