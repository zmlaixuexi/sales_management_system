from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import strip_html

CustomerSource = Literal["referral", "online", "offline", "ad", "other"]
CustomerLevel = Literal["vip", "important", "normal", "potential"]
FollowStatus = Literal["new", "following", "closed", "lost"]


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    contact_name: str | None = Field(None, description="联系人")
    phone: str | None = Field(None, max_length=20, description="电话")
    email: str | None = Field(None, description="邮箱")
    source: CustomerSource | None = Field(None, description="来源：referral/online/offline/ad/other")
    level: CustomerLevel = Field("normal", description="等级：vip/important/normal/potential")
    owner_user_id: str | None = Field(None, description="归属销售 ID")
    follow_status: FollowStatus = Field("new", description="跟进状态")
    remark: str | None = Field(None, description="备注")

    @field_validator("name", "contact_name", "email", "remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return strip_html(v) if v else v


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    contact_name: str | None = None
    phone: str | None = Field(None, max_length=20)
    email: str | None = None
    source: CustomerSource | None = None
    level: CustomerLevel | None = None
    follow_status: FollowStatus | None = None
    owner_user_id: str | None = None
    remark: str | None = None

    @field_validator("name", "contact_name", "email", "remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return strip_html(v) if v else v


class CustomerTransfer(BaseModel):
    owner_user_id: str = Field(..., description="新归属销售 ID")


# ── 响应模型 ──

class CustomerBrief(BaseModel):
    id: str
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    level: str | None = None
    owner_user_id: str | None = None
    follow_status: str | None = None


class CustomerDetail(BaseModel):
    id: str
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    level: str | None = None
    owner_user_id: str | None = None
    owner_name: str | None = None
    follow_status: str | None = None
    remark: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
