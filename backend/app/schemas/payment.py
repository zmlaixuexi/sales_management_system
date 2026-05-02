from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import strip_html

VALID_PAYMENT_METHODS = ("cash", "transfer", "wechat", "alipay", "other")


class PaymentCreate(BaseModel):
    amount: str = Field(..., description="收款金额")
    payment_method: Literal["cash", "transfer", "wechat", "alipay", "other"] = Field(
        ..., description="收款方式"
    )
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: str) -> str:
        if Decimal(v) <= 0:
            raise ValueError("收款金额必须大于 0")
        return v

    @field_validator("remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return strip_html(v) if v else v


# ── 响应模型 ──

class PaymentCreated(BaseModel):
    id: str
    order_id: str
    amount: str
    payment_method: str
    order_status: str


class PaymentReversed(BaseModel):
    id: str
    status: str
