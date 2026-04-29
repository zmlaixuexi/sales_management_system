"""订单 CRUD API — 含库存扣减/回滚、金额快照、状态机"""

import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem, InventoryMovement, Payment
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/sales-orders", tags=["订单管理"])

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


def _deduct_inventory(db: Session, order_id: uuid.UUID, items: list[SalesOrderItem], operator_id: uuid.UUID) -> None:
    """确认订单时扣减库存，并记录流水"""
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
        if not product:
            raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": f"商品 {item.product_name_snapshot} 不存在"})
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVENTORY_NOT_ENOUGH", "message": f"商品 {product.name} 库存不足（当前 {product.stock_quantity}，需要 {item.quantity}）"},
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
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
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
    current_user: User = Depends(get_current_user),
):
    """订单列表"""
    query = db.query(SalesOrder).filter(SalesOrder.deleted_at.is_(None))
    if keyword:
        query = query.filter(SalesOrder.order_no.ilike(f"%{keyword}%"))
    if status:
        query = query.filter(SalesOrder.status == status)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)

    query = query.order_by(SalesOrder.created_at.desc())
    total = query.count()
    orders = query.offset((page - 1) * page_size).limit(page_size).all()

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

    return {
        "success": True,
        "data": {"items": items_out, "page": page, "page_size": page_size, "total": total},
        "message": "查询成功",
    }


@router.post("")
def create_order(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建草稿订单"""
    customer_id = data.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "请选择客户"})

    customer = db.query(Customer).filter(Customer.id == uuid.UUID(str(customer_id)), Customer.deleted_at.is_(None)).first()
    if not customer:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "客户不存在"})

    raw_items = data.get("items", [])
    if not raw_items:
        raise HTTPException(status_code=400, detail={"code": "ORDER_EMPTY_ITEMS", "message": "订单明细不能为空"})

    # 构建明细行（含快照）
    prepared_items: list[dict] = []
    for ri in raw_items:
        product_id = ri.get("product_id")
        if not product_id:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "明细缺少商品 ID"})
        product = db.query(Product).filter(
            Product.id == uuid.UUID(str(product_id)), Product.deleted_at.is_(None)
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})
        if product.status != "active":
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": f"商品 {product.name} 已停用，不可下单"})

        quantity = int(ri.get("quantity", 0))
        if quantity <= 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "数量必须大于 0"})

        unit_price = Decimal(str(ri["unit_price"])) if "unit_price" in ri else None
        if unit_price is not None and unit_price < 0:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "成交单价不能为负"})

        prepared_items.append(_prepare_item(product, quantity, unit_price))

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
        remark=data.get("remark"),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(order)
    db.flush()

    for pi in prepared_items:
        db.add(SalesOrderItem(order_id=order.id, **pi))

    db.commit()

    return {
        "success": True,
        "data": {
            "id": str(order.id),
            "order_no": order.order_no,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "total_cost": str(order.total_cost),
            "gross_profit": str(order.gross_profit),
            "gross_margin": str(order.gross_margin),
        },
        "message": "创建成功",
    }


@router.get("/{order_id}")
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """订单详情"""
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

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

    return {
        "success": True,
        "data": {
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
        "message": "查询成功",
    }


@router.put("/{order_id}")
def update_order(
    order_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑草稿订单"""
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})
    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以编辑"})

    raw_items = data.get("items")
    if raw_items is not None:
        if not raw_items:
            raise HTTPException(status_code=400, detail={"code": "ORDER_EMPTY_ITEMS", "message": "订单明细不能为空"})

        # 删除旧明细
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).delete()

        prepared_items: list[dict] = []
        for ri in raw_items:
            product_id = ri.get("product_id")
            product = db.query(Product).filter(
                Product.id == uuid.UUID(str(product_id)), Product.deleted_at.is_(None)
            ).first()
            if not product:
                raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})
            if product.status != "active":
                raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": f"商品 {product.name} 已停用"})

            quantity = int(ri.get("quantity", 0))
            if quantity <= 0:
                raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "数量必须大于 0"})

            unit_price = Decimal(str(ri["unit_price"])) if "unit_price" in ri else None
            prepared_items.append(_prepare_item(product, quantity, unit_price))

        totals = _calc_order_totals(prepared_items)
        order.total_amount = totals["total_amount"]
        order.total_cost = totals["total_cost"]
        order.gross_profit = totals["gross_profit"]
        order.gross_margin = totals["gross_margin"]

        for pi in prepared_items:
            db.add(SalesOrderItem(order_id=order.id, **pi))

    if "remark" in data:
        order.remark = data["remark"]
    if "customer_id" in data:
        order.customer_id = uuid.UUID(str(data["customer_id"]))

    order.updated_by = current_user.id
    db.commit()

    return {"success": True, "data": {"id": str(order.id), "order_no": order.order_no}, "message": "更新成功"}


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认订单 — 扣减库存"""
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})
    if order.status != "draft":
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有草稿订单可以确认"})

    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
    _deduct_inventory(db, order.id, items, current_user.id)

    order.status = "confirmed"
    order.updated_by = current_user.id
    db.commit()

    return {"success": True, "data": {"id": str(order.id), "status": order.status}, "message": "确认成功"}


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消订单 — 回滚库存"""
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if "cancelled" not in allowed:
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": f"订单状态 {STATUS_LABELS.get(order.status, order.status)} 不允许取消"})

    # 已确认订单回滚库存
    if order.status == "confirmed":
        items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
        _restore_inventory(db, order.id, items, current_user.id)

    order.status = "cancelled"
    order.updated_by = current_user.id
    db.commit()

    return {"success": True, "data": {"id": str(order.id), "status": order.status}, "message": "取消成功"}
