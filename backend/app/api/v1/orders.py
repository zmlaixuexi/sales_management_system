"""订单 CRUD API — 含库存扣减/回滚、金额快照、状态机"""

import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_or_404, has_permission, require_permission, resp
from app.core.sanitize import escape_like
from app.models.customer import Customer
from app.models.order import InventoryMovement, SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderBrief, OrderCreate, OrderDetail, OrderUpdate
from app.schemas.response import ApiResponse
from app.services.audit_service import get_request_meta, log_action

router = APIRouter(
    prefix="/sales-orders", tags=["订单管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "参数验证失败或库存不足"},
        404: {"description": "订单或商品不存在"},
    },
)

# 允许的状态流转
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"cancelled"},
    "cancelled": set(),
    "partially_paid": {"cancelled"},
    "completed": set(),
}

STATUS_LABELS = {
    "draft": "草稿",
    "confirmed": "已确认",
    "cancelled": "已取消",
    "partially_paid": "部分收款",
    "completed": "已完成",
}


def _generate_order_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"
    last = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_no.like(f"{prefix}%"))
        .order_by(SalesOrder.order_no.desc())
        .first()
    )
    if last and last.order_no.startswith(prefix):
        try:
            seq = int(last.order_no[len(prefix):]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _calc_order_totals(items: list[dict]) -> dict:
    """计算订单总金额、总成本、毛利、毛利率"""
    total_amount = Decimal("0")
    total_cost = Decimal("0")
    for item in items:
        total_amount += Decimal(str(item.get("subtotal_amount", "0")))
        total_cost += Decimal(str(item.get("subtotal_cost", "0")))
    gross_profit = total_amount - total_cost
    gross_margin = (gross_profit / total_amount * Decimal("100") / Decimal("100")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ) if total_amount > 0 else Decimal("0")
    return {
        "total_amount": total_amount,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
    }


def _prepare_item(
    product: Product, quantity: int, unit_price: Decimal | None = None
) -> dict:
    """准备订单明细行，含快照"""
    price = unit_price if unit_price is not None else product.sale_price
    sale_price = product.sale_price
    discount_amount = sale_price - price
    discount_rate = (discount_amount / sale_price * Decimal("100") / Decimal("100")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ) if sale_price > 0 else Decimal("0")
    subtotal_amount = price * quantity
    subtotal_cost = product.cost_price * quantity
    return {
        "product_id": product.id,
        "product_sku_snapshot": product.sku,
        "product_name_snapshot": product.name,
        "product_image_url_snapshot": product.main_image_url,
        "quantity": quantity,
        "unit_price": price,
        "discount_amount": discount_amount,
        "discount_rate": discount_rate,
        "cost_price_snapshot": product.cost_price,
        "subtotal_amount": subtotal_amount,
        "subtotal_cost": subtotal_cost,
    }


def _validate_and_prepare_items(db: Session, raw_items: list) -> list[dict]:
    """校验订单明细行并返回准备好的数据"""
    # 批量查询所有商品，将 N 次查询减少为 1 次
    product_ids = [uuid.UUID(str(ri.product_id)) for ri in raw_items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    prepared: list[dict] = []
    for ri in raw_items:
        product = product_map.get(uuid.UUID(str(ri.product_id)))
        if product is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"},
            )
        if product.status != "active":
            raise HTTPException(
                status_code=400,
                detail={"code": "VALIDATION_FAILED", "message": f"商品 {product.name} 已停用，不可下单"},
            )
        if ri.quantity <= 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "数量必须大于 0"})
        unit_price = Decimal(str(ri.unit_price)) if ri.unit_price is not None else None
        if unit_price is not None and unit_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成交单价不能为负"})
        prepared.append(_prepare_item(product, ri.quantity, unit_price))
    return prepared


def _deduct_inventory(db: Session, order_id: uuid.UUID, items: list[SalesOrderItem], operator_id: uuid.UUID) -> None:
    """确认订单时扣减库存，并记录流水"""
    product_ids = [item.product_id for item in items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).with_for_update().all()
    product_map = {p.id: p for p in products}

    for item in items:
        product = product_map.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"商品 {item.product_name_snapshot} 不存在",
                },
            )
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVENTORY_NOT_ENOUGH",
                    "message": (
                        f"商品 {product.name} 库存不足"
                        f"（当前 {product.stock_quantity}，需要 {item.quantity}）"
                    ),
                },
            )
        before = product.stock_quantity
        product.stock_quantity -= item.quantity
        db.add(InventoryMovement(
            product_id=product.id,
            movement_type="order_confirm",
            quantity_before=before,
            quantity_change=-item.quantity,
            quantity_after=product.stock_quantity,
            related_type="sales_order",
            related_id=order_id,
            operator_id=operator_id,
        ))


def _restore_inventory(db: Session, order_id: uuid.UUID, items: list[SalesOrderItem], operator_id: uuid.UUID) -> None:
    """取消订单时回滚库存"""
    product_ids = [item.product_id for item in items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).with_for_update().all()
    product_map = {p.id: p for p in products}

    for item in items:
        product = product_map.get(item.product_id)
        if not product:
            continue
        before = product.stock_quantity
        product.stock_quantity += item.quantity
        db.add(InventoryMovement(
            product_id=product.id,
            movement_type="order_cancel",
            quantity_before=before,
            quantity_change=item.quantity,
            quantity_after=product.stock_quantity,
            related_type="sales_order",
            related_id=order_id,
            operator_id=operator_id,
        ))


@router.get("")
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """订单列表"""
    query = db.query(SalesOrder).filter(SalesOrder.deleted_at.is_(None))

    # 数据范围：无 order:view_all 权限只能看本人订单
    if not has_permission(current_user, "order:view_all"):
        query = query.filter(SalesOrder.sales_user_id == current_user.id)
    if keyword:
        query = query.filter(SalesOrder.order_no.ilike(f"%{escape_like(keyword)}%", escape="\\"))
    if status:
        query = query.filter(SalesOrder.status == status)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)

    query = query.order_by(SalesOrder.created_at.desc())
    total = query.count()
    orders = query.options(joinedload(SalesOrder.items), joinedload(SalesOrder.payments)).offset((page - 1) * page_size).limit(page_size).all()

    items_out = []
    for o in orders:
        items_out.append({
            "id": str(o.id),
            "order_no": o.order_no,
            "customer_id": str(o.customer_id),
            "sales_user_id": str(o.sales_user_id),
            "status": o.status,
            "status_label": STATUS_LABELS.get(o.status, o.status),
            "total_amount": str(o.total_amount),
            "total_cost": str(o.total_cost),
            "gross_profit": str(o.gross_profit),
            "gross_margin": str(o.gross_margin),
            "paid_amount": str(o.paid_amount),
            "item_count": len(o.items),
            "remark": o.remark,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        })

    return resp(
        data={"items": items_out, "page": page, "page_size": page_size, "total": total},
        message="查询成功",
    )


@router.post("", response_model=ApiResponse[OrderBrief])
def create_order(
    data: OrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:create")),
):
    """创建草稿订单"""
    customer_id = data.customer_id

    get_or_404(db, Customer, str(customer_id), "客户")  # validate customer exists

    raw_items = data.items
    if not raw_items:
        raise HTTPException(status_code=400, detail={"code": "ORDER_EMPTY_ITEMS", "message": "订单明细不能为空"})

    # 构建明细行（含快照）
    prepared_items = _validate_and_prepare_items(db, raw_items)

    totals = _calc_order_totals(prepared_items)
    order_no = _generate_order_no(db)

    order = SalesOrder(
        order_no=order_no,
        customer_id=uuid.UUID(str(customer_id)),
        sales_user_id=current_user.id,
        status="draft",
        total_amount=totals["total_amount"],
        total_cost=totals["total_cost"],
        gross_profit=totals["gross_profit"],
        gross_margin=totals["gross_margin"],
        paid_amount=Decimal("0"),
        remark=data.remark,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(order)
    db.flush()

    for pi in prepared_items:
        db.add(SalesOrderItem(order_id=order.id, **pi))

    log_action(
        db, action="order_create", resource_type="order",
        resource_id=str(order.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"order_no": order_no, "total_amount": str(order.total_amount)},
        **get_request_meta(request),
    )
    db.commit()

    return resp(
        data={
            "id": str(order.id),
            "order_no": order.order_no,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "total_cost": str(order.total_cost),
            "gross_profit": str(order.gross_profit),
            "gross_margin": str(order.gross_margin),
        },
        message="创建成功",
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderDetail])
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """订单详情"""
    order = get_or_404(db, SalesOrder, order_id, "订单")

    items_out = []
    for item in order.items:
        items_out.append({
            "id": str(item.id),
            "product_id": str(item.product_id),
            "product_sku_snapshot": item.product_sku_snapshot,
            "product_name_snapshot": item.product_name_snapshot,
            "product_image_url_snapshot": item.product_image_url_snapshot,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "discount_amount": str(item.discount_amount),
            "discount_rate": str(item.discount_rate),
            "cost_price_snapshot": str(item.cost_price_snapshot),
            "subtotal_amount": str(item.subtotal_amount),
            "subtotal_cost": str(item.subtotal_cost),
        })

    payments_out = []
    for p in order.payments:
        if p.status == "normal":
            payments_out.append({
                "id": str(p.id),
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "remark": p.remark,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

    return resp(
        data={
            "id": str(order.id),
            "order_no": order.order_no,
            "customer_id": str(order.customer_id),
            "sales_user_id": str(order.sales_user_id),
            "status": order.status,
            "status_label": STATUS_LABELS.get(order.status, order.status),
            "total_amount": str(order.total_amount),
            "total_cost": str(order.total_cost),
            "gross_profit": str(order.gross_profit),
            "gross_margin": str(order.gross_margin),
            "paid_amount": str(order.paid_amount),
            "remark": order.remark,
            "items": items_out,
            "payments": payments_out,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        message="查询成功",
    )


@router.put("/{order_id}")
def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:update")),
):
    """编辑草稿订单"""
    order = get_or_404(db, SalesOrder, order_id, "订单")
    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以编辑"})

    raw_items = data.items
    if raw_items is not None:
        if not raw_items:
            raise HTTPException(status_code=400, detail={"code": "ORDER_EMPTY_ITEMS", "message": "订单明细不能为空"})

        # 删除旧明细
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).delete()

        prepared_items = _validate_and_prepare_items(db, raw_items)

        totals = _calc_order_totals(prepared_items)
        order.total_amount = totals["total_amount"]
        order.total_cost = totals["total_cost"]
        order.gross_profit = totals["gross_profit"]
        order.gross_margin = totals["gross_margin"]

        for pi in prepared_items:
            db.add(SalesOrderItem(order_id=order.id, **pi))

    if data.remark is not None:
        order.remark = data.remark
    if data.customer_id is not None:
        order.customer_id = uuid.UUID(str(data.customer_id))

    order.updated_by = current_user.id
    log_action(
        db, action="order_update", resource_type="order",
        resource_id=str(order.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"order_no": order.order_no},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data={"id": str(order.id), "order_no": order.order_no}, message="更新成功")


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:confirm")),
):
    """确认订单 — 扣减库存"""
    order = get_or_404(db, SalesOrder, order_id, "订单")
    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以确认"})

    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
    _deduct_inventory(db, order.id, items, current_user.id)

    order.status = "confirmed"
    order.updated_by = current_user.id
    log_action(
        db, action="order_confirm", resource_type="order",
        resource_id=str(order.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"order_no": order.order_no, "status": "confirmed"},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data={"id": str(order.id), "status": order.status}, message="确认成功")


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:cancel")),
):
    """取消订单 — 回滚库存"""
    order = get_or_404(db, SalesOrder, order_id, "订单")

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if "cancelled" not in allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ORDER_INVALID_STATUS",
                "message": (
                    f"订单状态 {STATUS_LABELS.get(order.status, order.status)} 不允许取消"
                ),
            },
        )

    # 已确认订单回滚库存
    if order.status == "confirmed":
        items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
        _restore_inventory(db, order.id, items, current_user.id)

    order.status = "cancelled"
    order.updated_by = current_user.id
    log_action(
        db, action="order_cancel", resource_type="order",
        resource_id=str(order.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"order_no": order.order_no, "status": "cancelled"},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data={"id": str(order.id), "status": order.status}, message="取消成功")
