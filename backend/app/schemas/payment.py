from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    amount: str = Field(..., description="收款金额")
    payment_method: str = Field(..., description="收款方式：cash/transfer/wechat/alipay/other")
    remark: str | None = Field(None, description="备注")


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
