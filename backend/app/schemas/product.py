from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    sku: str | None = Field(None, max_length=50, description="商品编码，为空则自动生成")
    sale_price: str = Field("0", description="销售价")
    cost_price: str = Field("0", description="成本价")
    stock_quantity: int = Field(0, ge=0, description="库存数量")
    category_id: str | None = Field(None, description="分类 ID")
    main_image_url: str | None = Field(None, description="主图 URL")
    status: str = Field("active", description="状态：active/inactive/disabled")
    sort_weight: int = Field(0, description="排序权重")
    remark: str | None = Field(None, description="备注")


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    sku: str | None = Field(None, max_length=50)
    sale_price: str | None = None
    cost_price: str | None = None
    stock_quantity: int | None = Field(None, ge=0)
    category_id: str | None = None
    main_image_url: str | None = None
    status: str | None = None
    sort_weight: int | None = None
    remark: str | None = None
