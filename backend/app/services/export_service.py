"""数据导出服务 — CSV 流式生成"""

import csv
import io
import uuid
from decimal import Decimal
from typing import Generator

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import Payment, SalesOrder
from app.models.product import Product

# UTF-8 BOM，确保 Excel 正确识别编码
BOM = "﻿"


def _dec(v: Decimal | None) -> str:
    if v is None:
        return ""
    return str(v)


def _str(v: object) -> str:
    if v is None:
        return ""
    return str(v)


def _dt(v: object) -> str:
    if v is None:
        return ""
    val = str(v)
    return val[:19].replace("T", " ")


# ─── 商品导出 ────────────────────────────────────────────────

PRODUCT_HEADERS = ["SKU", "商品名称", "销售价", "成本价", "库存", "状态", "分类", "备注", "创建时间"]


def _product_row(p: Product) -> list[str]:
    status_map = {"active": "上架", "inactive": "下架", "disabled": "停用"}
    cat_name = p.category.name if p.category else "未分类"
    return [
        p.sku or "",
        p.name or "",
        _dec(p.sale_price),
        _dec(p.cost_price),
        str(p.stock_quantity or 0),
        status_map.get(p.status, p.status or ""),
        cat_name,
        p.remark or "",
        _dt(p.created_at),
    ]


def export_products(
    db: Session,
    *,
    keyword: str | None = None,
    status: str | None = None,
    category_id: uuid.UUID | None = None,
) -> Generator[str, None, None]:
    query = db.query(Product).filter(Product.deleted_at.is_(None))
    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    if status:
        query = query.filter(Product.status == status)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    query = query.order_by(Product.created_at.desc())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(PRODUCT_HEADERS)
    yield BOM + buf.getvalue()

    for product in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_product_row(product))
        yield buf.getvalue()


# ─── 客户导出 ────────────────────────────────────────────────

CUSTOMER_HEADERS = ["客户名称", "联系人", "电话", "邮箱", "来源", "等级", "归属销售", "跟进状态", "备注", "创建时间"]


def _customer_row(c: Customer) -> list[str]:
    owner_name = c.owner.display_name if c.owner else ""
    return [
        c.name or "",
        c.contact_name or "",
        c.phone or "",
        c.email or "",
        c.source or "",
        c.level or "",
        owner_name,
        c.follow_status or "",
        c.remark or "",
        _dt(c.created_at),
    ]


def export_customers(
    db: Session,
    *,
    keyword: str | None = None,
    source: str | None = None,
) -> Generator[str, None, None]:
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))
    if keyword:
        query = query.filter(
            (Customer.name.ilike(f"%{keyword}%"))
            | (Customer.phone.ilike(f"%{keyword}%"))
            | (Customer.contact_name.ilike(f"%{keyword}%"))
        )
    if source:
        query = query.filter(Customer.source == source)
    query = query.order_by(Customer.created_at.desc())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CUSTOMER_HEADERS)
    yield BOM + buf.getvalue()

    for customer in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_customer_row(customer))
        yield buf.getvalue()


# ─── 订单导出 ────────────────────────────────────────────────

ORDER_HEADERS = [
    "订单号", "客户ID", "状态", "销售额", "成本", "毛利", "毛利率",
    "已收金额", "明细数", "备注", "创建时间",
]

STATUS_MAP = {
    "draft": "草稿",
    "confirmed": "已确认",
    "cancelled": "已取消",
    "partially_paid": "部分收款",
    "completed": "已完成",
}


def _order_row(o: SalesOrder) -> list[str]:
    return [
        o.order_no or "",
        str(o.customer_id),
        STATUS_MAP.get(o.status, o.status or ""),
        _dec(o.total_amount),
        _dec(o.total_cost),
        _dec(o.gross_profit),
        _dec(o.gross_margin),
        _dec(o.paid_amount),
        str(len(o.items)) if o.items else "0",
        o.remark or "",
        _dt(o.created_at),
    ]


def export_orders(
    db: Session,
    *,
    keyword: str | None = None,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Generator[str, None, None]:
    query = db.query(SalesOrder).filter(SalesOrder.deleted_at.is_(None))
    if keyword:
        query = query.filter(SalesOrder.order_no.ilike(f"%{keyword}%"))
    if status:
        query = query.filter(SalesOrder.status == status)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if start_date:
        query = query.filter(SalesOrder.created_at >= start_date)
    if end_date:
        query = query.filter(SalesOrder.created_at <= end_date)
    query = query.order_by(SalesOrder.created_at.desc())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(ORDER_HEADERS)
    yield BOM + buf.getvalue()

    for order in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_order_row(order))
        yield buf.getvalue()


# ─── 收款导出 ────────────────────────────────────────────────

PAYMENT_HEADERS = ["收款ID", "订单ID", "金额", "收款方式", "状态", "收款时间", "备注", "创建时间"]


def _payment_row(p: Payment) -> list[str]:
    return [
        str(p.id),
        str(p.order_id),
        _dec(p.amount),
        p.payment_method or "",
        "正常" if p.status == "normal" else "已冲正",
        _dt(p.paid_at),
        p.remark or "",
        _dt(p.created_at),
    ]


def export_payments(
    db: Session,
    *,
    order_id: uuid.UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Generator[str, None, None]:
    query = db.query(Payment)
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    query = query.order_by(Payment.created_at.desc())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(PAYMENT_HEADERS)
    yield BOM + buf.getvalue()

    for payment in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_payment_row(payment))
        yield buf.getvalue()
