"""数据导出 API — CSV 格式流式下载"""

import uuid
from datetime import date, datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, has_permission, require_permission, safe_commit
from app.models.user import User
from app.services.audit_service import log_user_action
from app.services.export_service import (
    export_customers,
    export_orders,
    export_payments,
    export_products,
)

router = APIRouter(
    prefix="/exports", tags=["数据导出"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
    },
)


def _csv_filename(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"


def _disposition(filename: str) -> str:
    """生成兼容中文的 Content-Disposition 头（RFC 5987）"""
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.get("/products")
def export_products_csv(
    request: Request,
    keyword: str | None = None,
    status: Literal["active", "inactive", "disabled"] | None = None,
    category_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product:list")),
):
    """导出商品列表为 CSV"""
    can_view_cost = has_permission(current_user, "product:view_cost")
    generator = export_products(
        db, keyword=keyword, status=status,
        category_id=category_id, can_view_cost=can_view_cost,
    )
    log_user_action(db, request, current_user,
                    action="export_products", resource_type="product",
                    after_data={"keyword": keyword, "status": status})
    safe_commit(db)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(_csv_filename("商品列表"))},
    )


@router.get("/customers")
def export_customers_csv(
    request: Request,
    keyword: str | None = None,
    source: Literal["referral", "online", "offline", "ad", "other"] | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:list")),
):
    """导出客户列表为 CSV"""
    owner_user_id = None if has_permission(current_user, "customer:view_all") else current_user.id
    generator = export_customers(db, keyword=keyword, source=source, owner_user_id=owner_user_id)
    log_user_action(db, request, current_user,
                    action="export_customers", resource_type="customer",
                    after_data={"keyword": keyword, "source": source})
    safe_commit(db)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(_csv_filename("客户列表"))},
    )


@router.get("/orders")
def export_orders_csv(
    request: Request,
    keyword: str | None = None,
    status: Literal["draft", "confirmed", "cancelled", "partially_paid", "completed"] | None = None,
    customer_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("order:list")),
):
    """导出订单列表为 CSV"""
    sales_user_id = None if has_permission(current_user, "order:view_all") else current_user.id
    can_view_cost = has_permission(current_user, "product:view_cost")
    generator = export_orders(
        db, keyword=keyword, status=status, customer_id=customer_id,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        sales_user_id=sales_user_id,
        can_view_cost=can_view_cost,
    )
    log_user_action(db, request, current_user,
                    action="export_orders", resource_type="order",
                    after_data={"keyword": keyword, "status": status})
    safe_commit(db)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(_csv_filename("销售订单"))},
    )


@router.get("/payments")
def export_payments_csv(
    request: Request,
    order_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:list")),
):
    """导出收款记录为 CSV"""
    sales_user_id = None if has_permission(current_user, "order:view_all") else current_user.id
    generator = export_payments(
        db, order_id=order_id,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        sales_user_id=sales_user_id,
    )
    log_user_action(db, request, current_user,
                    action="export_payments", resource_type="payment",
                    after_data={"order_id": str(order_id) if order_id else None})
    safe_commit(db)
    return StreamingResponse(
        generator,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(_csv_filename("收款记录"))},
    )
