"""报表 API — 销售汇总、趋势、排行、库存预警"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["报表"])


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
        start = today - timedelta(days=29)
    return start, today


@router.get("/sales-summary")
def sales_summary(
    period: str = Query("30d", description="时间段: today, 7d, 30d, this_month, last_month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """销售汇总：总销售额、总成本、毛利、订单数"""
    start, end = _date_range(period)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    result = (
        db.query(
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.coalesce(func.sum(SalesOrder.total_cost), 0),
            func.coalesce(func.sum(SalesOrder.gross_profit), 0),
            func.count(SalesOrder.id),
        )
        .filter(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.status.in_(["confirmed", "partially_paid", "completed"]),
            SalesOrder.created_at >= start_dt,
            SalesOrder.created_at <= end_dt,
        )
        .first()
    )

    total_amount, total_cost, gross_profit, order_count = result
    gross_margin = (gross_profit / total_amount * 100).quantize(
        __import__("decimal").Decimal("0.01")
    ) if total_amount and total_amount > 0 else 0

    return {
        "success": True,
        "data": {
            "total_amount": str(total_amount),
            "total_cost": str(total_cost),
            "gross_profit": str(gross_profit),
            "gross_margin": str(gross_margin),
            "order_count": order_count,
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "message": "查询成功",
    }


@router.get("/sales-trend")
def sales_trend(
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """销售趋势：按日统计销售额和订单数"""
    start, end = _date_range(period)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    rows = (
        db.query(
            func.date(SalesOrder.created_at).label("d"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("amount"),
            func.count(SalesOrder.id).label("cnt"),
        )
        .filter(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.status.in_(["confirmed", "partially_paid", "completed"]),
            SalesOrder.created_at >= start_dt,
            SalesOrder.created_at <= end_dt,
        )
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

    return {
        "success": True,
        "data": {"items": items, "period": period},
        "message": "查询成功",
    }


@router.get("/product-ranking")
def product_ranking(
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """商品销售排行：按销售额排序"""
    start, end = _date_range(period)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    rows = (
        db.query(
            SalesOrderItem.product_id,
            SalesOrderItem.product_name_snapshot,
            SalesOrderItem.product_sku_snapshot,
            func.coalesce(func.sum(SalesOrderItem.subtotal_amount), 0).label("total_sales"),
            func.coalesce(func.sum(SalesOrderItem.subtotal_cost), 0).label("total_cost"),
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("total_quantity"),
        )
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .filter(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.status.in_(["confirmed", "partially_paid", "completed"]),
            SalesOrder.created_at >= start_dt,
            SalesOrder.created_at <= end_dt,
        )
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
        items.append({
            "rank": idx,
            "product_id": str(r.product_id),
            "product_name": r.product_name_snapshot,
            "sku": r.product_sku_snapshot,
            "total_sales": str(r.total_sales),
            "total_cost": str(r.total_cost),
            "total_quantity": r.total_quantity,
        })

    return {"success": True, "data": {"items": items, "period": period}, "message": "查询成功"}


@router.get("/inventory-warning")
def inventory_warning(
    threshold: int = Query(10, ge=0, description="库存预警阈值"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """库存预警：低于阈值的商品列表"""
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

    return {
        "success": True,
        "data": {"items": items, "threshold": threshold, "total": len(items)},
        "message": "查询成功",
    }
