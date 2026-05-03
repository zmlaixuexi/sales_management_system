"""订单 CRUD API — 含库存扣减/回滚、金额快照、状态机"""

import json
import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    PaginationParams,
    active_query,
    check_owner_or_forbid,
    fmt_dt,
    generate_sequential_code,
    get_db,
    get_or_404,
    has_permission,
    paginate,
    paginated_resp,
    parse_uuid_or_400,
    require_permission,
    resp,
)
from app.core.metrics import INVENTORY_STOCKOUT, ORDER_CANCELLED, ORDER_CONFIRMED, ORDER_CREATED
from app.core.sanitize import escape_like
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.models.order import InventoryMovement, SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderBrief, OrderCreate, OrderDetail, OrderUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.response import ApiResponse
from app.services.audit_service import log_user_action
from app.services.payment_service import register_payment

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
    "confirmed": {"cancelled", "partially_paid"},
    "cancelled": set(),
    "partially_paid": {"partially_paid", "cancelled"},
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
    return generate_sequential_code(db, SalesOrder, SalesOrder.order_no, "ORD-")


def _calc_order_totals(items: list[dict]) -> dict:
    """计算订单总金额、总成本、毛利、毛利率"""
    total_amount = Decimal("0")
    total_cost = Decimal("0")
    for item in items:
        total_amount += Decimal(str(item.get("subtotal_amount", "0")))
        total_cost += Decimal(str(item.get("subtotal_cost", "0")))
    gross_profit = total_amount - total_cost
    gross_margin = (gross_profit / total_amount).quantize(
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
    # MVP：成交单价低于成本价时阻止提交
    if price < product.cost_price:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PRICE_BELOW_COST",
                "message": f"商品「{product.name}」成交单价低于成本价，无法提交",
            },
        )
    sale_price = product.sale_price
    discount_amount = sale_price - price
    discount_rate = (discount_amount / sale_price).quantize(
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
    product_ids = [parse_uuid_or_400(ri.product_id, "商品 ID") for ri in raw_items]
    products = active_query(db, Product).filter(
        Product.id.in_(product_ids),
    ).all()
    product_map = {p.id: p for p in products}

    prepared: list[dict] = []
    for ri in raw_items:
        product = product_map.get(parse_uuid_or_400(ri.product_id, "商品 ID"))
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
        unit_price = Decimal(str(ri.unit_price)) if ri.unit_price is not None else None
        prepared.append(_prepare_item(product, ri.quantity, unit_price))
    return prepared


def _deduct_inventory(db: Session, order_id: uuid.UUID, items: list[SalesOrderItem], operator_id: uuid.UUID) -> None:
    """确认订单时扣减库存，并记录流水"""
    product_ids = [item.product_id for item in items]
    products = active_query(db, Product).filter(
        Product.id.in_(product_ids),
    ).with_for_update().all()
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
            INVENTORY_STOCKOUT.inc()
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVENTORY_NOT_ENOUGH",
                    "message": f"商品 {product.name} 库存不足，无法确认",
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
    products = active_query(db, Product).filter(
        Product.id.in_(product_ids),
    ).with_for_update().all()
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
    pagination: PaginationParams = Depends(),
    keyword: str | None = None,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """订单列表"""
    can_view_cost = has_permission(current_user, "product:view_cost")
    query = active_query(db, SalesOrder)

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
    orders, total = paginate(query, pagination.page, pagination.page_size)

    items_out = []
    for o in orders:
        row: dict = {
            "id": str(o.id),
            "order_no": o.order_no,
            "customer_id": str(o.customer_id),
            "sales_user_id": str(o.sales_user_id),
            "status": o.status,
            "status_label": STATUS_LABELS.get(o.status, o.status),
            "total_amount": str(o.total_amount),
            "paid_amount": str(o.paid_amount),
            "item_count": len(o.items),
            "remark": o.remark,
            "created_at": fmt_dt(o.created_at),
            "updated_at": fmt_dt(o.updated_at),
        }
        if can_view_cost:
            row["total_cost"] = str(o.total_cost)
            row["gross_profit"] = str(o.gross_profit)
            row["gross_margin"] = str(o.gross_margin)
        items_out.append(row)

    return paginated_resp(items_out, pagination.page, pagination.page_size, total)


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

    if not raw_items:  # pragma: no cover — schema 验证已拦截空 items
        raise HTTPException(
            status_code=400,
            detail={"code": "ORDER_EMPTY_ITEMS", "message": "订单明细不能为空"},
        )

    # 构建明细行（含快照）
    prepared_items = _validate_and_prepare_items(db, raw_items)

    totals = _calc_order_totals(prepared_items)
    order_no = _generate_order_no(db)

    order = SalesOrder(
        order_no=order_no,
        customer_id=parse_uuid_or_400(customer_id, "客户 ID"),
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

    log_user_action(
        db, request, current_user,
        action="order_create", resource_type="order",
        resource_id=str(order.id),
        after_data={
            "order_no": order_no,
            "status": order.status,
            "customer_id": str(order.customer_id),
            "total_amount": str(order.total_amount),
            "items": [
                {"product_id": str(pi["product_id"]), "quantity": pi["quantity"], "unit_price": str(pi["unit_price"])}
                for pi in prepared_items
            ],
        },
    )
    db.commit()
    ORDER_CREATED.labels(status="draft").inc()

    can_view_cost = has_permission(current_user, "product:view_cost")
    result: dict = {
        "id": str(order.id),
        "order_no": order.order_no,
        "status": order.status,
        "total_amount": str(order.total_amount),
    }
    if can_view_cost:
        result["total_cost"] = str(order.total_cost)
        result["gross_profit"] = str(order.gross_profit)
        result["gross_margin"] = str(order.gross_margin)

    return resp(data=result, message="创建成功")


@router.get("/{order_id}", response_model=ApiResponse[OrderDetail])
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """订单详情"""
    order = get_or_404(db, SalesOrder, order_id, "订单")

    # 对象级权限：非 view_all 只能看本人订单
    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    can_view_cost = has_permission(current_user, "product:view_cost")

    items_out = []
    for item in order.items:
        irow: dict = {
            "id": str(item.id),
            "product_id": str(item.product_id),
            "product_sku_snapshot": item.product_sku_snapshot,
            "product_name_snapshot": item.product_name_snapshot,
            "product_image_url_snapshot": item.product_image_url_snapshot,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "discount_amount": str(item.discount_amount),
            "discount_rate": str(item.discount_rate),
            "subtotal_amount": str(item.subtotal_amount),
        }
        if can_view_cost:
            irow["cost_price_snapshot"] = str(item.cost_price_snapshot)
            irow["subtotal_cost"] = str(item.subtotal_cost)
        items_out.append(irow)

    payments_out = [{
        "id": str(p.id),
        "amount": str(p.amount),
        "payment_method": p.payment_method,
        "paid_at": fmt_dt(p.paid_at),
        "remark": p.remark,
        "created_at": fmt_dt(p.created_at),
    } for p in order.payments if p.status == "normal"]

    data: dict = {
        "id": str(order.id),
        "order_no": order.order_no,
        "customer_id": str(order.customer_id),
        "sales_user_id": str(order.sales_user_id),
        "status": order.status,
        "status_label": STATUS_LABELS.get(order.status, order.status),
        "total_amount": str(order.total_amount),
        "paid_amount": str(order.paid_amount),
        "remark": order.remark,
        "items": items_out,
        "payments": payments_out,
        "created_at": fmt_dt(order.created_at),
        "updated_at": fmt_dt(order.updated_at),
    }
    if can_view_cost:
        data["total_cost"] = str(order.total_cost)
        data["gross_profit"] = str(order.gross_profit)
        data["gross_margin"] = str(order.gross_margin)

    return resp(data=data, message="查询成功")


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

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以编辑"})

    raw_items = data.items
    before_snapshot = {
        "order_no": order.order_no,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "remark": order.remark,
        "customer_id": str(order.customer_id),
    }
    if raw_items is not None:

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
        new_cid = parse_uuid_or_400(data.customer_id, "客户 ID")
        get_or_404(db, Customer, new_cid, "客户")
        order.customer_id = new_cid

    order.updated_by = current_user.id
    after_payload: dict = {
        "order_no": order.order_no, "status": order.status,
        "total_amount": str(order.total_amount), "customer_id": str(order.customer_id),
    }
    if raw_items is not None:
        after_payload["items"] = [
            {"product_id": str(pi["product_id"]), "quantity": pi["quantity"], "unit_price": str(pi["unit_price"])}
            for pi in prepared_items
        ]
    log_user_action(
        db, request, current_user,
        action="order_update", resource_type="order",
        resource_id=str(order.id),
        before_data=before_snapshot,
        after_data=after_payload,
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
    order = active_query(db, SalesOrder).filter(
        SalesOrder.id == order_id,
    ).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以确认"})

    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
    _deduct_inventory(db, order.id, items, current_user.id)

    order.status = "confirmed"
    order.updated_by = current_user.id
    log_user_action(
        db, request, current_user,
        action="order_confirm", resource_type="order",
        resource_id=str(order.id),
        before_data={
            "order_no": order.order_no, "status": "draft",
            "total_amount": str(order.total_amount), "customer_id": str(order.customer_id),
        },
        after_data={
            "order_no": order.order_no, "status": "confirmed",
            "total_amount": str(order.total_amount), "customer_id": str(order.customer_id),
        },
    )
    db.commit()
    ORDER_CONFIRMED.inc()

    return resp(data={"id": str(order.id), "status": order.status}, message="确认成功")


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:cancel")),
):
    """取消订单 — 回滚库存"""
    order = active_query(db, SalesOrder).filter(
        SalesOrder.id == order_id,
    ).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

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

    # 部分收款的订单必须先冲正所有收款才能取消
    if order.status == "partially_paid" and (order.paid_amount or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ORDER_HAS_PAYMENTS",
                "message": "该订单已有收款记录，请先冲正所有收款后再取消订单",
            },
        )

    # 已确认/部分付款订单回滚库存
    if order.status in ("confirmed", "partially_paid"):
        items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
        _restore_inventory(db, order.id, items, current_user.id)

    old_status = order.status
    order.status = "cancelled"
    order.updated_by = current_user.id
    log_user_action(
        db, request, current_user,
        action="order_cancel", resource_type="order",
        resource_id=str(order.id),
        before_data={
            "order_no": order.order_no, "status": old_status,
            "total_amount": str(order.total_amount), "customer_id": str(order.customer_id),
        },
        after_data={
            "order_no": order.order_no, "status": "cancelled",
            "total_amount": str(order.total_amount), "customer_id": str(order.customer_id),
        },
    )
    db.commit()
    ORDER_CANCELLED.inc()

    return resp(data={"id": str(order.id), "status": order.status}, message="取消成功")


@router.get("/{order_id}/logs")
def order_logs(
    order_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:view")),
):
    """查询指定订单的操作日志"""
    order = get_or_404(db, SalesOrder, order_id, "订单")
    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    query = db.query(AuditLog).filter(
        AuditLog.resource_type == "order",
        AuditLog.resource_id == str(order_id),
    )

    items, total = paginate(
        query.order_by(AuditLog.created_at.desc()), pagination.page, pagination.page_size,
    )

    # 无 product:view_cost 权限时，从审计数据中移除敏感字段
    cost_fields = {"cost_price", "unit_profit", "gross_margin", "total_cost", "subtotal_cost"}
    can_view_cost = has_permission(current_user, "product:view_cost")

    def _safe_parse(raw):
        return json.loads(raw) if raw else None

    def _strip_sensitive(data):
        if not isinstance(data, dict):  # pragma: no cover — 审计日志数据总是 dict
            return data
        return {k: v for k, v in data.items() if k not in cost_fields}

    def _filter(raw):
        parsed = _safe_parse(raw)
        if parsed and not can_view_cost:
            return _strip_sensitive(parsed)
        return parsed

    result_items = [
        {
            "id": str(item.id),
            "actor_id": str(item.actor_id) if item.actor_id else None,
            "actor_name": item.actor_name,
            "action": item.action,
            "before_data": _filter(item.before_data),
            "after_data": _filter(item.after_data),
            "ip_address": item.ip_address,
            "user_agent": item.user_agent,
            "request_id": item.request_id,
            "created_at": fmt_dt(item.created_at),
        }
        for item in items
    ]

    return paginated_resp(result_items, pagination.page, pagination.page_size, total)


@router.post("/{order_id}/payments")
def create_order_payment(
    order_id: uuid.UUID,
    data: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:create")),
):
    """登记订单收款（规范路径）"""
    result = register_payment(db, str(order_id), data, current_user)

    log_user_action(
        db, request, current_user,
        action="payment_create", resource_type="payment",
        resource_id=str(result["payment"].id),
        after_data={
            "order_id": str(result["order"].id),
            "amount": str(result["amount"]),
            "method": result["method"],
        },
    )
    db.commit()

    return resp(
        data={
            "id": str(result["payment"].id),
            "order_id": str(result["order"].id),
            "amount": str(result["payment"].amount),
            "payment_method": result["payment"].payment_method,
            "order_status": result["order"].status,
        },
        message="收款登记成功",
    )
