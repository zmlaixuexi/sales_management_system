from pydantic import BaseModel, Field


class OrderItemInput(BaseModel):
    product_id: str = Field(..., description="商品 ID")
    quantity: int = Field(..., gt=0, description="数量")
    unit_price: str | None = Field(None, description="成交单价，为空则使用商品售价")


class OrderCreate(BaseModel):
    customer_id: str = Field(..., description="客户 ID")
    items: list[OrderItemInput] = Field(..., min_length=1, description="订单明细")
    remark: str | None = Field(None, description="备注")


class OrderUpdate(BaseModel):
    customer_id: str | None = None
    items: list[OrderItemInput] | None = Field(None, min_length=1)
    remark: str | None = None
