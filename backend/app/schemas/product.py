from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text as _sanitize

ProductStatus = Literal["active", "inactive", "disabled"]


def _validate_price(v: str | None, field_name: str) -> str | None:
    if v is None:
        return v
    try:
        d = Decimal(v)
    except InvalidOperation:
        raise ValueError(f"{field_name}格式不正确") from None
    if d < 0:
        raise ValueError(f"{field_name}不能为负数")
    return v


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="商品名称")
    sku: str | None = Field(None, max_length=50, description="商品编码，为空则自动生成")
    sale_price: str = Field("0", description="销售价")
    cost_price: str = Field("0", description="成本价")
    stock_quantity: int = Field(0, ge=0, description="库存数量")
    category_id: str | None = Field(None, description="分类 ID")
    main_image_url: str | None = Field(None, max_length=500, description="主图 URL")
    status: ProductStatus = Field("active", description="状态：active/inactive/disabled")
    sort_weight: int = Field(0, description="排序权重")
    remark: str | None = Field(None, max_length=500, description="备注")

    @field_validator("sale_price")
    @classmethod
    def validate_sale_price(cls, v: str) -> str:
        return _validate_price(v, "销售价") or v

    @field_validator("cost_price")
    @classmethod
    def validate_cost_price(cls, v: str) -> str:
        return _validate_price(v, "成本价") or v

    @field_validator("name", "remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    sku: str | None = Field(None, max_length=50)
    sale_price: str | None = None
    cost_price: str | None = None
    stock_quantity: int | None = Field(None, ge=0)
    category_id: str | None = None
    main_image_url: str | None = Field(None, max_length=500)
    status: ProductStatus | None = None
    sort_weight: int | None = None
    remark: str | None = Field(None, max_length=500)

    @field_validator("sale_price")
    @classmethod
    def validate_sale_price(cls, v: str | None) -> str | None:
        return _validate_price(v, "销售价")

    @field_validator("cost_price")
    @classmethod
    def validate_cost_price(cls, v: str | None) -> str | None:
        return _validate_price(v, "成本价")

    @field_validator("name", "remark")
    @classmethod
    def sanitize_text(cls, v: str | None) -> str | None:
        return _sanitize(v)


# ── 响应模型 ──

class ProductItem(BaseModel):
    id: str
    sku: str
    name: str
    main_image_url: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    sale_price: str
    cost_price: str | None = None
    unit_profit: str | None = None
    gross_margin: str | None = None
    stock_quantity: int
    status: str
    sort_weight: int
    remark: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProductBrief(BaseModel):
    id: str
    sku: str
    name: str
    main_image_url: str | None = None
    category_id: str | None = None
    sale_price: str
    cost_price: str | None = None
    unit_profit: str | None = None
    gross_margin: str | None = None
    stock_quantity: int
    status: str
    sort_weight: int = 0


class ProductImageItem(BaseModel):
    id: str
    file_id: str
    url: str | None = None
    is_primary: bool
    sort_order: int


class ProductDetail(BaseModel):
    id: str
    sku: str
    name: str
    main_image_url: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    sale_price: str
    cost_price: str | None = None
    unit_profit: str | None = None
    gross_margin: str | None = None
    stock_quantity: int
    status: str
    sort_weight: int
    remark: str | None = None
    images: list[ProductImageItem] = []
    created_at: str | None = None
    updated_at: str | None = None


class PriceHistoryItem(BaseModel):
    id: str
    old_sale_price: str | None = None
    new_sale_price: str | None = None
    old_cost_price: str | None = None
    new_cost_price: str | None = None
    created_at: str | None = None


class ImportResult(BaseModel):
    created: int
    errors: list[dict]
