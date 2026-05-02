from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text as _sanitize


class InventoryAdjust(BaseModel):
    product_id: str = Field(..., description="商品 ID")
    quantity_change: int = Field(..., description="库存变动数量（正数入库，负数出库）")
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("remark")
    @classmethod
    def sanitize_remark(cls, v: str | None) -> str | None:
        return _sanitize(v)


# ── 响应模型 ──

class InventoryAdjusted(BaseModel):
    product_id: str
    quantity_before: int
    quantity_change: int
    quantity_after: int
