"""报表 API — 销售汇总、趋势、排行、库存预警"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, has_permission, require_permission, resp
from app.core.config import settings
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User

router = APIRouter(
    prefix="/reports", tags=["报表"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
    },
)

_VALID_ORDER_STATUSES = ["confirmed", "partially_paid", "completed"]


def _date_range(period: str):
    """根据 period 参数计算起止日期"""
    today = date.today()
    if period == "today":
        start = today
    elif period == "7d":
        start = today - timedelta(days=6)
    elif period == "30d":
        start = today - timedelta(days=29)
    elif period == "this_month":
        start = today.replace(day=1)
    elif period == "last_month":
        first_this = today.replace(day=1)
        end_last = first_this - timedelta(days=1)
        start = end_last.replace(day=1)
    else:
        valid = "today, 7d, 30d, this_month, last_month"
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_FAILED", "message": f"不支持的 period 参数: {period}，可选值: {valid}"},
        )
    return start, today


def _order_period_filter(query, period: str):
    """为查询添加订单日期范围和状态过滤（不含数据范围）。"""
    start, end = _date_range(period)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    return (
        query.filter(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.status.in_(_VALID_ORDER_STATUSES),
            SalesOrder.created_at >= start_dt,
            SalesOrder.created_at <= end_dt,
        ),
        start,
        end,
    )


def _apply_data_scope(query, current_user: User):
    """非 view_all 用户只看本人订单。"""
    if not has_permission(current_user, "order:view_all"):
        return query.filter(SalesOrder.sales_user_id == current_user.id)
    return query


@router.get("/sales-summary")
def sales_summary(
    period: str = Query("30d", description="时间段: today, 7d, 30d, this_month, last_month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """销售汇总：总销售额、总成本、毛利、订单数"""
    query = (
        db.query(
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.coalesce(func.sum(SalesOrder.total_cost), 0),
            func.coalesce(func.sum(SalesOrder.gross_profit), 0),
            func.count(SalesOrder.id),
        )
    )
    query, start, end = _order_period_filter(query, period)
    query = _apply_data_scope(query, current_user)

    result = query.first()

    total_amount, total_cost, gross_profit, order_count = result
    gross_margin = (gross_profit / total_amount * 100).quantize(
        Decimal("0.01")
    ) if total_amount and total_amount > 0 else 0

    can_view_profit = has_permission(current_user, "report:profit")
    data: dict = {
        "total_amount": str(total_amount),
        "order_count": order_count,
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    if can_view_profit:
        data["total_cost"] = str(total_cost)
        data["gross_profit"] = str(gross_profit)
        data["gross_margin"] = str(gross_margin)

    return resp(data)


@router.get("/sales-trend")
def sales_trend(
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """销售趋势：按日统计销售额和订单数"""
    query = (
        db.query(
            func.date(SalesOrder.created_at).label("d"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("amount"),
            func.count(SalesOrder.id).label("cnt"),
        )
    )
    query, start, end = _order_period_filter(query, period)
    query = _apply_data_scope(query, current_user)

    rows = (
        query
        .group_by(func.date(SalesOrder.created_at))
        .order_by(func.date(SalesOrder.created_at))
        .all()
    )

    # 填充空缺日期
    data_map = {str(r.d): {"amount": str(r.amount), "count": r.cnt} for r in rows}
    items = []
    current = start
    while current <= end:
        key = current.isoformat()
        val = data_map.get(key, {"amount": "0", "count": 0})
        items.append({"date": key, "amount": val["amount"], "order_count": val["count"]})
        current += timedelta(days=1)

    return resp({"items": items, "period": period})


@router.get("/product-ranking")
def product_ranking(
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """商品销售排行：按销售额排序"""
    can_view_profit = has_permission(current_user, "report:profit")

    query = (
        db.query(
            SalesOrderItem.product_id,
            SalesOrderItem.product_name_snapshot,
            SalesOrderItem.product_sku_snapshot,
            func.coalesce(func.sum(SalesOrderItem.subtotal_amount), 0).label("total_sales"),
            func.coalesce(func.sum(SalesOrderItem.subtotal_cost), 0).label("total_cost"),
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("total_quantity"),
        )
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
    )
    query, _, _ = _order_period_filter(query, period)
    query = _apply_data_scope(query, current_user)

    rows = (
        query
        .group_by(
            SalesOrderItem.product_id,
            SalesOrderItem.product_name_snapshot,
            SalesOrderItem.product_sku_snapshot,
        )
        .order_by(func.sum(SalesOrderItem.subtotal_amount).desc())
        .limit(limit)
        .all()
    )

    items = []
    for idx, r in enumerate(rows, 1):
        row: dict = {
            "rank": idx,
            "product_id": str(r.product_id),
            "product_name": r.product_name_snapshot,
            "sku": r.product_sku_snapshot,
            "total_sales": str(r.total_sales),
            "total_quantity": r.total_quantity,
        }
        if can_view_profit:
            row["total_cost"] = str(r.total_cost)
        items.append(row)

    return resp({"items": items, "period": period})


@router.get("/customer-ranking")
def customer_ranking(
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """客户销售排行：按销售额排序"""
    can_view_profit = has_permission(current_user, "report:profit")

    query = (
        db.query(
            SalesOrder.customer_id,
            Customer.name.label("customer_name"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total_sales"),
            func.coalesce(func.sum(SalesOrder.total_cost), 0).label("total_cost"),
            func.coalesce(func.sum(SalesOrder.gross_profit), 0).label("gross_profit"),
            func.count(SalesOrder.id).label("order_count"),
        )
        .join(Customer, SalesOrder.customer_id == Customer.id)
    )
    query, _, _ = _order_period_filter(query, period)
    query = _apply_data_scope(query, current_user)

    rows = (
        query
        .group_by(SalesOrder.customer_id, Customer.name)
        .order_by(func.sum(SalesOrder.total_amount).desc())
        .limit(limit)
        .all()
    )

    items = []
    for idx, r in enumerate(rows, 1):
        row: dict = {
            "rank": idx,
            "customer_id": str(r.customer_id),
            "customer_name": r.customer_name,
            "total_sales": str(r.total_sales),
            "order_count": r.order_count,
        }
        if can_view_profit:
            row["total_cost"] = str(r.total_cost)
            row["gross_profit"] = str(r.gross_profit)
        items.append(row)

    return resp({"items": items, "period": period})


@router.get("/salesperson-ranking")
def salesperson_ranking(
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """销售人员业绩排行：按销售额排序"""
    can_view_profit = has_permission(current_user, "report:profit")

    query = (
        db.query(
            SalesOrder.sales_user_id,
            User.display_name.label("salesperson_name"),
            User.username.label("salesperson_username"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total_sales"),
            func.coalesce(func.sum(SalesOrder.total_cost), 0).label("total_cost"),
            func.coalesce(func.sum(SalesOrder.gross_profit), 0).label("gross_profit"),
            func.count(SalesOrder.id).label("order_count"),
        )
        .join(User, SalesOrder.sales_user_id == User.id)
    )
    query, _, _ = _order_period_filter(query, period)
    query = _apply_data_scope(query, current_user)

    rows = (
        query
        .group_by(SalesOrder.sales_user_id, User.display_name, User.username)
        .order_by(func.sum(SalesOrder.total_amount).desc())
        .limit(limit)
        .all()
    )

    items = []
    for idx, r in enumerate(rows, 1):
        row: dict = {
            "rank": idx,
            "user_id": str(r.sales_user_id),
            "name": r.salesperson_name or r.salesperson_username,
            "total_sales": str(r.total_sales),
            "order_count": r.order_count,
        }
        if can_view_profit:
            row["total_cost"] = str(r.total_cost)
            row["gross_profit"] = str(r.gross_profit)
        items.append(row)

    return resp({"items": items, "period": period})


@router.get("/inventory-warning")
def inventory_warning(
    threshold: int = Query(None, ge=0, description="库存预警阈值"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("report:sales")),
):
    """库存预警：低于阈值的商品列表"""
    if threshold is None:
        threshold = settings.INVENTORY_WARNING_THRESHOLD
    rows = (
        db.query(Product)
        .filter(
            Product.deleted_at.is_(None),
            Product.status == "active",
            Product.stock_quantity <= threshold,
        )
        .order_by(Product.stock_quantity.asc())
        .all()
    )

    items = [
        {
            "id": str(p.id),
            "sku": p.sku,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "sale_price": str(p.sale_price),
        }
        for p in rows
    ]

    return resp({"items": items, "threshold": threshold, "total": len(items)})
