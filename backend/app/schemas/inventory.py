import uuid as _uuid

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text as _sanitize


class InventoryAdjust(BaseModel):
    product_id: str = Field(..., description="商品 ID")
    quantity_change: int = Field(..., ge=-9999999, le=9999999, description="库存变动数量（正数入库，负数出库）")
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("remark")
    @classmethod
    def sanitize_remark(cls, v: str | None) -> str | None:
        return _sanitize(v)

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: str) -> str:
        try:
            _uuid.UUID(v)
        except (ValueError, AttributeError):
            raise ValueError("商品 ID 格式不正确") from None
        return v


# ── 响应模型 ──

class InventoryAdjusted(BaseModel):
    product_id: str
    quantity_before: int
    quantity_change: int
    quantity_after: int
