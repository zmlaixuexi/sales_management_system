from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text as _sanitize

VALID_PAYMENT_METHODS = ("cash", "transfer", "wechat", "alipay", "other")
_MAX_AMOUNT = Decimal("9999999999.99")


class PaymentCreate(BaseModel):
    amount: str = Field(..., description="收款金额")
    payment_method: Literal["cash", "transfer", "wechat", "alipay", "other"] = Field(
        ..., description="收款方式"
    )
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except InvalidOperation:
            raise ValueError("金额格式不正确") from None
        if d <= 0:
            raise ValueError("收款金额必须大于 0")
        if d > _MAX_AMOUNT:
            raise ValueError(f"收款金额不能超过 {_MAX_AMOUNT}")
        return v

    @field_validator("remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)


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
