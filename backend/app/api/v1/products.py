"""商品 CRUD API"""

import csv
import io
import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_or_404, has_permission, require_permission, resp
from app.core.config import settings
from app.core.sanitize import escape_like
from app.models.product import Product, ProductCategory, ProductPriceHistory
from app.models.user import User
from app.schemas.product import (
    ProductBrief,
    ProductCreate,
    ProductDetail,
    ProductUpdate,
)
from app.schemas.response import ApiResponse
from app.services.audit_service import get_request_meta, log_action

router = APIRouter(
    prefix="/products", tags=["商品管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "参数验证失败"},
        404: {"description": "商品不存在"},
    },
)

# 默认分类名称
DEFAULT_CATEGORY_NAME = "未分类"


def _parse_uuid_or_400(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400, detail={"code": "VALIDATION_FAILED", "message": f"{label}格式无效"},
        ) from None


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
        query = query.filter(Product.name.ilike(f"%{escape_like(keyword)}%", escape="\\"))
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
    items = query.options(joinedload(Product.category)).offset((page - 1) * page_size).limit(page_size).all()

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

    return resp(
        data={
            "items": result_items,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        message="查询成功",
    )


@router.post("", response_model=ApiResponse[ProductBrief])
def create_product(
    data: ProductCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:create")),
):
    """新增商品"""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "商品名称不能为空"})

    try:
        cost_price = Decimal(str(data.cost_price))
        sale_price = Decimal(str(data.sale_price))
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "价格格式错误"}) from None

    if cost_price < 0 or sale_price < 0:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "价格不能为负"})

    sku = data.sku or _generate_sku(db)

    existing_sku = db.query(Product).filter(Product.sku == sku, Product.deleted_at.is_(None)).first()
    if existing_sku:
        raise HTTPException(status_code=400, detail={"code": "PRODUCT_SKU_DUPLICATED", "message": "商品编码已存在"})

    category_id = (
        _get_default_category_id(db)
        if not data.category_id
        else _parse_uuid_or_400(data.category_id, "分类 ID")
    )

    main_image_url = data.main_image_url

    product = Product(
        sku=sku,
        name=name,
        main_image_url=main_image_url,
        category_id=category_id,
        sale_price=sale_price,
        cost_price=cost_price,
        stock_quantity=data.stock_quantity,
        status=data.status,
        sort_weight=data.sort_weight,
        remark=data.remark,
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
        **get_request_meta(request),
    )
    db.commit()

    can_view_cost = has_permission(current_user, "product:view_cost")
    data: dict = {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "main_image_url": product.main_image_url,
        "category_id": str(product.category_id) if product.category_id else None,
        "sale_price": str(product.sale_price),
        "stock_quantity": product.stock_quantity,
        "status": product.status,
        "sort_weight": product.sort_weight,
    }
    if can_view_cost:
        data["cost_price"] = str(product.cost_price)
        data["unit_profit"] = str(unit_profit)
        data["gross_margin"] = str(gross_margin)

    return resp(data=data, message="创建成功")


@router.get("/{product_id}", response_model=ApiResponse[ProductDetail])
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """商品详情"""
    product = get_or_404(db, Product, product_id, "商品")

    unit_profit, gross_margin = _calc_profit(product.sale_price, product.cost_price)
    can_view_cost = has_permission(current_user, "product:view_cost")

    data: dict = {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "main_image_url": product.main_image_url,
        "category_id": str(product.category_id) if product.category_id else None,
        "category_name": product.category.name if product.category else None,
        "sale_price": str(product.sale_price),
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
    }
    if can_view_cost:
        data["cost_price"] = str(product.cost_price)
        data["unit_profit"] = str(unit_profit)
        data["gross_margin"] = str(gross_margin)

    return resp(data=data, message="查询成功")


@router.put("/{product_id}", response_model=ApiResponse[ProductBrief])
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:update")),
):
    """编辑商品"""
    product = get_or_404(db, Product, product_id, "商品")

    # 检查价格变更，记录价格历史
    old_sale_price = product.sale_price
    old_cost_price = product.cost_price

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "商品名称不能为空"})
        product.name = name

    if data.sale_price is not None:
        try:
            new_sale_price = Decimal(str(data.sale_price))
        except Exception:
            raise HTTPException(
                status_code=400, detail={"code": "VALIDATION_FAILED", "message": "销售价格式错误"},
            ) from None
        if new_sale_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "销售价不能为负"})
        product.sale_price = new_sale_price

    if data.cost_price is not None:
        try:
            new_cost_price = Decimal(str(data.cost_price))
        except Exception:
            raise HTTPException(
                status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成本价格式错误"},
            ) from None
        if new_cost_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成本价不能为负"})
        product.cost_price = new_cost_price

    if data.main_image_url is not None:
        product.main_image_url = data.main_image_url

    if data.category_id is not None:
        product.category_id = _parse_uuid_or_400(data.category_id, "分类 ID")

    if data.stock_quantity is not None:
        product.stock_quantity = data.stock_quantity

    if data.status is not None:
        product.status = data.status

    if data.sort_weight is not None:
        product.sort_weight = data.sort_weight

    if data.remark is not None:
        product.remark = data.remark

    if data.sku is not None:
        new_sku = data.sku
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
        **get_request_meta(request),
    )
    db.commit()

    unit_profit, gross_margin = _calc_profit(product.sale_price, product.cost_price)

    can_view_cost = has_permission(current_user, "product:view_cost")
    data: dict = {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "main_image_url": product.main_image_url,
        "sale_price": str(product.sale_price),
        "stock_quantity": product.stock_quantity,
        "status": product.status,
    }
    if can_view_cost:
        data["cost_price"] = str(product.cost_price)
        data["unit_profit"] = str(unit_profit)
        data["gross_margin"] = str(gross_margin)

    return resp(data=data, message="更新成功")


@router.delete("/{product_id}")
def delete_product(
    product_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:delete")),
):
    """删除或软删除商品"""
    product = get_or_404(db, Product, product_id, "商品")

    # MVP：直接软删除，后续检查是否有订单引用
    product.deleted_at = datetime.now()
    product.updated_by = current_user.id
    log_action(
        db, action="product_delete", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"name": product.name, "sku": product.sku},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data=None, message="删除成功")


@router.post("/{product_id}/disable")
def disable_product(
    product_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:update")),
):
    """停用商品"""
    product = get_or_404(db, Product, product_id, "商品")

    product.status = "disabled"
    product.updated_by = current_user.id
    log_action(
        db, action="product_disable", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"status": "active"}, after_data={"status": "disabled"},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data={"id": str(product.id), "status": product.status}, message="停用成功")


@router.get("/{product_id}/price-history", response_model=ApiResponse[dict])
def price_history(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """查看价格变更记录"""
    can_view_cost = has_permission(current_user, "product:view_cost")
    history = db.query(ProductPriceHistory).filter(
        ProductPriceHistory.product_id == product_id
    ).order_by(ProductPriceHistory.created_at.desc()).all()

    items = []
    for h in history:
        row: dict = {
            "id": str(h.id),
            "old_sale_price": str(h.old_sale_price) if h.old_sale_price is not None else None,
            "new_sale_price": str(h.new_sale_price) if h.new_sale_price is not None else None,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        if can_view_cost:
            row["old_cost_price"] = str(h.old_cost_price) if h.old_cost_price is not None else None
            row["new_cost_price"] = str(h.new_cost_price) if h.new_cost_price is not None else None
        items.append(row)

    return resp(data={"items": items}, message="查询成功")


@router.post("/import")
async def import_products_csv(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:create")),
):
    """批量导入商品（CSV 格式）"""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "请上传 CSV 文件",
        })

    content = await file.read()
    max_size = settings.MAX_CSV_IMPORT_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED",
            "message": f"CSV 文件不能超过 {settings.MAX_CSV_IMPORT_SIZE_MB}MB",
        })

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "文件编码错误，请使用 UTF-8",
        }) from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "CSV 文件为空或缺少表头",
        })

    # 获取默认分类
    default_cat = db.query(ProductCategory).filter(
        ProductCategory.name == DEFAULT_CATEGORY_NAME,
    ).first()

    created = 0
    errors: list[dict] = []
    used_skus: set[str] = set()
    # 预加载已有 SKU，避免逐行查询数据库
    existing_skus = {
        s for (s,) in db.query(Product.sku).filter(Product.deleted_at.is_(None)).all()
    }

    # 预计算批量 SKU 前缀和起始序号
    today = datetime.now().strftime("%Y%m%d")
    sku_prefix = f"SPU-{today}-"
    last_product = (
        db.query(Product)
        .filter(Product.sku.like(f"{sku_prefix}%"))
        .order_by(Product.sku.desc())
        .first()
    )
    sku_seq = 1
    if last_product and last_product.sku.startswith(sku_prefix):
        try:
            sku_seq = int(last_product.sku[len(sku_prefix):]) + 1
        except ValueError:
            sku_seq = 1

    for row_num, row in enumerate(reader, start=2):
        name = (row.get("商品名称") or row.get("name") or "").strip()
        if not name:
            errors.append({"row": row_num, "message": "商品名称不能为空"})
            continue

        # 解析字段
        sku = (row.get("SKU") or row.get("sku") or "").strip() or None
        try:
            sale_price = Decimal(row.get("销售价") or row.get("sale_price") or "0")
        except Exception:
            errors.append({"row": row_num, "message": "销售价格式错误"})
            continue
        try:
            cost_price = Decimal(row.get("成本价") or row.get("cost_price") or "0")
        except Exception:
            errors.append({"row": row_num, "message": "成本价格式错误"})
            continue

        if sale_price < 0 or cost_price < 0:
            errors.append({"row": row_num, "message": "价格不能为负"})
            continue

        # SKU 唯一性检查
        if sku:
            if sku in used_skus:
                errors.append({"row": row_num, "message": f"SKU {sku} 已存在"})
                continue
            if sku in existing_skus:
                errors.append({"row": row_num, "message": f"SKU {sku} 已存在"})
                continue
        else:
            sku = f"{sku_prefix}{sku_seq:04d}"
            sku_seq += 1
        used_skus.add(sku)

        try:
            stock = int(row.get("库存数量") or row.get("stock_quantity") or "0")
        except ValueError:
            stock = 0

        product = Product(
            id=uuid.uuid4(),
            sku=sku,
            name=name,
            sale_price=sale_price,
            cost_price=cost_price,
            stock_quantity=stock,
            category_id=default_cat.id if default_cat else None,
            status="active",
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        db.add(product)
        created += 1

    db.commit()

    log_action(db, actor_id=current_user.id, actor_name=current_user.display_name,
               action="product_import", resource_type="product",
               after_data={"created": created, "errors": len(errors)},
               **get_request_meta(request))
    db.commit()

    return resp(
        data={"created": created, "errors": errors},
        message=f"成功导入 {created} 个商品" + (f"，{len(errors)} 行跳过" if errors else ""),
    )
