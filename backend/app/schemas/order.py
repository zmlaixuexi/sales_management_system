from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text as _sanitize


class OrderItemInput(BaseModel):
    product_id: str = Field(..., description="商品 ID")
    quantity: int = Field(..., gt=0, description="数量")
    unit_price: str | None = Field(None, description="成交单价，为空则使用商品售价")

    @field_validator("unit_price")
    @classmethod
    def unit_price_must_be_non_negative(cls, v: str | None) -> str | None:
        if v is not None and Decimal(v) < 0:
            raise ValueError("成交单价不能为负")
        return v


class OrderCreate(BaseModel):
    customer_id: str = Field(..., description="客户 ID")
    items: list[OrderItemInput] = Field(..., min_length=1, description="订单明细")
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)


class OrderUpdate(BaseModel):
    customer_id: str | None = None
    items: list[OrderItemInput] | None = Field(None, min_length=1)
    remark: str | None = Field(None, max_length=500)

    @field_validator("remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)


# ── 响应模型 ──

class OrderBrief(BaseModel):
    id: str
    order_no: str
    status: str | None = None
    total_amount: str | None = None
    total_cost: str | None = None
    gross_profit: str | None = None
    gross_margin: str | None = None


class OrderItemResponse(BaseModel):
    id: str | None = None
    product_id: str | None = None
    product_sku_snapshot: str | None = None
    product_name_snapshot: str | None = None
    product_image_url_snapshot: str | None = None
    quantity: int | None = None
    unit_price: str | None = None
    discount_amount: str | None = None
    discount_rate: str | None = None
    cost_price_snapshot: str | None = None
    subtotal_amount: str | None = None
    subtotal_cost: str | None = None


class OrderPaymentResponse(BaseModel):
    id: str | None = None
    amount: str | None = None
    payment_method: str | None = None
    paid_at: str | None = None
    remark: str | None = None
    created_at: str | None = None


class OrderDetail(BaseModel):
    id: str
    order_no: str
    customer_id: str | None = None
    sales_user_id: str | None = None
    status: str | None = None
    status_label: str | None = None
    total_amount: str | None = None
    total_cost: str | None = None
    gross_profit: str | None = None
    gross_margin: str | None = None
    paid_amount: str | None = None
    remark: str | None = None
    items: list[OrderItemResponse] = []
    payments: list[OrderPaymentResponse] = []
    created_at: str | None = None
    updated_at: str | None = None
