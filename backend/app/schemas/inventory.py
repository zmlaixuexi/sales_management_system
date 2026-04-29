from pydantic import BaseModel, Field


class InventoryAdjust(BaseModel):
    product_id: str = Field(..., description="商品 ID")
    quantity_change: int = Field(..., description="库存变动数量（正数入库，负数出库）")
    remark: str | None = Field(None, description="备注")


# ── 响应模型 ──

class InventoryAdjusted(BaseModel):
    product_id: str
    quantity_before: int
    quantity_change: int
    quantity_after: int
