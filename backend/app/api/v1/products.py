"""商品 CRUD API"""

import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_permission, has_permission
from app.models.product import Product, ProductCategory, ProductPriceHistory
from app.models.user import User
from app.services.audit_service import log_action, model_to_dict

router = APIRouter(prefix="/products", tags=["商品管理"])

# 默认分类名称
DEFAULT_CATEGORY_NAME = "未分类"


def _generate_sku(db: Session) -> str:
    """生成 SKU: SPU-YYYYMMDD-四位序号"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"SPU-{today}-"

    last_product = (
        db.query(Product)
        .filter(Product.sku.like(f"{prefix}%"))
        .order_by(Product.sku.desc())
        .first()
    )

    if last_product and last_product.sku.startswith(prefix):
        try:
            seq = int(last_product.sku[len(prefix):]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


def _get_default_category_id(db: Session) -> uuid.UUID:
    """获取默认分类 ID"""
    cat = db.query(ProductCategory).filter(ProductCategory.name == DEFAULT_CATEGORY_NAME).first()
    if not cat:
        cat = ProductCategory(name=DEFAULT_CATEGORY_NAME)
        db.add(cat)
        db.flush()
    return cat.id


def _calc_profit(sale_price: Decimal, cost_price: Decimal) -> tuple[Decimal, Decimal]:
    """计算利润和毛利率"""
    profit = sale_price - cost_price
    margin = (profit / sale_price * Decimal("100") / Decimal("100")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ) if sale_price > 0 else Decimal("0")
    return profit, margin


@router.get("")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    category_id: uuid.UUID | None = None,
    sort_by: str = Query("sort_weight"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """商品列表"""
    can_view_cost = has_permission(current_user, "product:view_cost")
    query = db.query(Product).filter(Product.deleted_at.is_(None))

    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    if status:
        query = query.filter(Product.status == status)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # 排序
    sort_col = getattr(Product, sort_by, None)
    if sort_col is None:
        sort_col = Product.sort_weight
    if sort_order == "asc":
        query = query.order_by(sort_col.asc(), Product.created_at.desc())
    else:
        query = query.order_by(sort_col.desc(), Product.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for p in items:
        unit_profit, gross_margin = _calc_profit(p.sale_price, p.cost_price)
        row: dict = {
            "id": str(p.id),
            "sku": p.sku,
            "name": p.name,
            "main_image_url": p.main_image_url,
            "category_id": str(p.category_id) if p.category_id else None,
            "category_name": p.category.name if p.category else None,
            "sale_price": str(p.sale_price),
            "stock_quantity": p.stock_quantity,
            "status": p.status,
            "sort_weight": p.sort_weight,
            "remark": p.remark,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        if can_view_cost:
            row["cost_price"] = str(p.cost_price)
            row["unit_profit"] = str(unit_profit)
            row["gross_margin"] = str(gross_margin)
        result_items.append(row)

    return {
        "success": True,
        "data": {
            "items": result_items,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        "message": "查询成功",
    }


@router.post("")
def create_product(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:create")),
):
    """新增商品"""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "商品名称不能为空"})

    try:
        cost_price = Decimal(str(data.get("cost_price", "0")))
        sale_price = Decimal(str(data.get("sale_price", "0")))
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "价格格式错误"})

    if cost_price < 0 or sale_price < 0:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "价格不能为负"})

    sku = data.get("sku") or _generate_sku(db)

    existing_sku = db.query(Product).filter(Product.sku == sku, Product.deleted_at.is_(None)).first()
    if existing_sku:
        raise HTTPException(status_code=400, detail={"code": "PRODUCT_SKU_DUPLICATED", "message": "商品编码已存在"})

    category_id = data.get("category_id")
    if not category_id:
        category_id = _get_default_category_id(db)
    else:
        category_id = uuid.UUID(str(category_id))

    main_image_url = data.get("main_image_url")

    product = Product(
        sku=sku,
        name=name,
        main_image_url=main_image_url,
        category_id=category_id,
        sale_price=sale_price,
        cost_price=cost_price,
        stock_quantity=int(data.get("stock_quantity", 0)),
        status=data.get("status", "active"),
        sort_weight=int(data.get("sort_weight", 0)),
        remark=data.get("remark"),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(product)
    db.flush()

    unit_profit, gross_margin = _calc_profit(sale_price, cost_price)

    log_action(
        db, action="product_create", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"name": name, "sku": sku, "sale_price": str(sale_price), "cost_price": str(cost_price)},
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "main_image_url": product.main_image_url,
            "category_id": str(product.category_id) if product.category_id else None,
            "sale_price": str(product.sale_price),
            "cost_price": str(product.cost_price),
            "unit_profit": str(unit_profit),
            "gross_margin": str(gross_margin),
            "stock_quantity": product.stock_quantity,
            "status": product.status,
            "sort_weight": product.sort_weight,
        },
        "message": "创建成功",
    }


@router.get("/{product_id}")
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """商品详情"""
    product = db.query(Product).filter(
        Product.id == product_id, Product.deleted_at.is_(None)
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})

    unit_profit, gross_margin = _calc_profit(product.sale_price, product.cost_price)

    return {
        "success": True,
        "data": {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "main_image_url": product.main_image_url,
            "category_id": str(product.category_id) if product.category_id else None,
            "category_name": product.category.name if product.category else None,
            "sale_price": str(product.sale_price),
            "cost_price": str(product.cost_price),
            "unit_profit": str(unit_profit),
            "gross_margin": str(gross_margin),
            "stock_quantity": product.stock_quantity,
            "status": product.status,
            "sort_weight": product.sort_weight,
            "remark": product.remark,
            "images": [
                {
                    "id": str(img.id),
                    "file_id": str(img.file_id),
                    "url": img.file.public_url if img.file else None,
                    "is_primary": img.is_primary,
                    "sort_order": img.sort_order,
                }
                for img in product.images
            ],
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        },
        "message": "查询成功",
    }


@router.put("/{product_id}")
def update_product(
    product_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:update")),
):
    """编辑商品"""
    product = db.query(Product).filter(
        Product.id == product_id, Product.deleted_at.is_(None)
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})

    # 检查价格变更，记录价格历史
    old_sale_price = product.sale_price
    old_cost_price = product.cost_price

    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "商品名称不能为空"})
        product.name = name

    if "sale_price" in data:
        try:
            new_sale_price = Decimal(str(data["sale_price"]))
        except Exception:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "销售价格式错误"})
        if new_sale_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "销售价不能为负"})
        product.sale_price = new_sale_price

    if "cost_price" in data:
        try:
            new_cost_price = Decimal(str(data["cost_price"]))
        except Exception:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成本价格式错误"})
        if new_cost_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成本价不能为负"})
        product.cost_price = new_cost_price

    if "main_image_url" in data:
        product.main_image_url = data["main_image_url"]

    if "category_id" in data:
        product.category_id = uuid.UUID(str(data["category_id"]))

    if "stock_quantity" in data:
        stock = int(data["stock_quantity"])
        if stock < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "库存不能为负"})
        product.stock_quantity = stock

    if "status" in data:
        product.status = data["status"]

    if "sort_weight" in data:
        product.sort_weight = int(data["sort_weight"])

    if "remark" in data:
        product.remark = data["remark"]

    if "sku" in data:
        new_sku = data["sku"]
        existing = db.query(Product).filter(
            Product.sku == new_sku, Product.id != product_id, Product.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail={"code": "PRODUCT_SKU_DUPLICATED", "message": "商品编码已存在"})
        product.sku = new_sku

    product.updated_by = current_user.id

    # 记录价格变更
    if product.sale_price != old_sale_price or product.cost_price != old_cost_price:
        db.add(ProductPriceHistory(
            product_id=product.id,
            old_sale_price=old_sale_price,
            new_sale_price=product.sale_price,
            old_cost_price=old_cost_price,
            new_cost_price=product.cost_price,
            changed_by=current_user.id,
        ))

    log_action(
        db, action="product_update", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"name": product.name, "sale_price": str(old_sale_price), "cost_price": str(old_cost_price)},
        after_data={"name": product.name, "sale_price": str(product.sale_price), "cost_price": str(product.cost_price)},
    )
    db.commit()

    unit_profit, gross_margin = _calc_profit(product.sale_price, product.cost_price)

    return {
        "success": True,
        "data": {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "main_image_url": product.main_image_url,
            "sale_price": str(product.sale_price),
            "cost_price": str(product.cost_price),
            "unit_profit": str(unit_profit),
            "gross_margin": str(gross_margin),
            "stock_quantity": product.stock_quantity,
            "status": product.status,
        },
        "message": "更新成功",
    }


@router.delete("/{product_id}")
def delete_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:delete")),
):
    """删除或软删除商品"""
    product = db.query(Product).filter(
        Product.id == product_id, Product.deleted_at.is_(None)
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})

    # MVP：直接软删除，后续检查是否有订单引用
    product.deleted_at = datetime.now()
    product.updated_by = current_user.id
    log_action(
        db, action="product_delete", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"name": product.name, "sku": product.sku},
    )
    db.commit()

    return {"success": True, "data": None, "message": "删除成功"}


@router.post("/{product_id}/disable")
def disable_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:update")),
):
    """停用商品"""
    product = db.query(Product).filter(
        Product.id == product_id, Product.deleted_at.is_(None)
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})

    product.status = "disabled"
    product.updated_by = current_user.id
    log_action(
        db, action="product_disable", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"status": "active"}, after_data={"status": "disabled"},
    )
    db.commit()

    return {"success": True, "data": {"id": str(product.id), "status": product.status}, "message": "停用成功"}


@router.get("/{product_id}/price-history")
def price_history(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """查看价格变更记录"""
    history = db.query(ProductPriceHistory).filter(
        ProductPriceHistory.product_id == product_id
    ).order_by(ProductPriceHistory.created_at.desc()).all()

    items = []
    for h in history:
        items.append({
            "id": str(h.id),
            "old_sale_price": str(h.old_sale_price) if h.old_sale_price is not None else None,
            "new_sale_price": str(h.new_sale_price) if h.new_sale_price is not None else None,
            "old_cost_price": str(h.old_cost_price) if h.old_cost_price is not None else None,
            "new_cost_price": str(h.new_cost_price) if h.new_cost_price is not None else None,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        })

    return {"success": True, "data": {"items": items}, "message": "查询成功"}
