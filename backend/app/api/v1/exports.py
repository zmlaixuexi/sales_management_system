"""数据导出 API — CSV 格式流式下载"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.services.export_service import (
    export_customers,
    export_orders,
    export_payments,
    export_products,
)

router = APIRouter(prefix="/exports", tags=["数据导出"])


def _csv_filename(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"


@router.get("/products")
def export_products_csv(
    keyword: str | None = None,
    status: str | None = None,
    category_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """导出商品列表为 CSV"""
    generator = export_products(db, keyword=keyword, status=status, category_id=category_id)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={_csv_filename('products')}"},
    )


@router.get("/customers")
def export_customers_csv(
    keyword: str | None = None,
    source: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:list")),
):
    """导出客户列表为 CSV"""
    generator = export_customers(db, keyword=keyword, source=source)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={_csv_filename('customers')}"},
    )


@router.get("/orders")
def export_orders_csv(
    keyword: str | None = None,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """导出订单列表为 CSV"""
    generator = export_orders(
        db, keyword=keyword, status=status, customer_id=customer_id,
        start_date=start_date, end_date=end_date,
    )
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={_csv_filename('orders')}"},
    )


@router.get("/payments")
def export_payments_csv(
    order_id: uuid.UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:list")),
):
    """导出收款记录为 CSV"""
    generator = export_payments(db, order_id=order_id, start_date=start_date, end_date=end_date)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={_csv_filename('payments')}"},
    )
