import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import strip_html


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=6, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("新密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("新密码必须包含至少一个数字")
        return v


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

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        return v

    @field_validator("display_name", "email")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return strip_html(v) if v else v


class UserUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None
    role_ids: list[str] | None = None

    @field_validator("display_name", "email")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return strip_html(v) if v else v


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
