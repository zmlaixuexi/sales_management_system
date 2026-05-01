"""收款登记和冲正 API"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    check_owner_or_forbid,
    get_db,
    has_permission,
    paginate,
    paginated_resp,
    require_permission,
    resp,
)
from app.models.order import Payment, SalesOrder
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentCreated, PaymentReversed
from app.schemas.response import ApiResponse
from app.services.audit_service import log_user_action
from app.services.payment_service import register_payment

router = APIRouter(
    prefix="/payments", tags=["收款管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "金额无效或订单状态不允许"},
        404: {"description": "订单或收款记录不存在"},
    },
)


@router.get("")
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:list")),
):
    """收款列表"""
    query = db.query(Payment).filter(Payment.status == "normal")
    # 数据范围：无 order:view_all 权限只能看本人订单的收款
    if not has_permission(current_user, "order:view_all"):
        query = query.join(SalesOrder).filter(
            SalesOrder.sales_user_id == current_user.id,
            SalesOrder.deleted_at.is_(None),
        )
    else:
        query = query.join(SalesOrder, Payment.order_id == SalesOrder.id).filter(
            SalesOrder.deleted_at.is_(None),
        )
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    query = query.order_by(Payment.created_at.desc())

    items, total = paginate(query, page, page_size)

    return paginated_resp(
        [
            {
                "id": str(p.id),
                "order_id": str(p.order_id),
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "status": p.status,
                "remark": p.remark,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in items
        ],
        page,
        page_size,
        total,
    )


@router.post("/orders/{order_id}/payments", response_model=ApiResponse[PaymentCreated])
def create_payment(
    order_id: uuid.UUID,
    data: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:create")),
):
    """登记订单收款"""
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


@router.post("/{payment_id}/reverse", response_model=ApiResponse[PaymentReversed])
def reverse_payment(
    payment_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:reverse")),
):
    """冲正收款"""
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.status == "normal").first()
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "收款记录不存在或已冲正"})

    order = db.query(SalesOrder).filter(
        SalesOrder.id == payment.order_id, SalesOrder.deleted_at.is_(None),
    ).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "关联订单不存在"})

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    if order.status not in ("confirmed", "partially_paid", "completed"):
        raise HTTPException(
            status_code=400,
            detail={"code": "ORDER_INVALID_STATUS", "message": "订单状态不允许冲正收款"},
        )

    order.paid_amount -= payment.amount
    if order.paid_amount <= 0:
        order.paid_amount = Decimal("0")
        order.status = "confirmed"
    elif order.status == "completed":
        order.status = "partially_paid"

    payment.status = "reversed"
    order.updated_by = current_user.id
    log_user_action(
        db, request, current_user,
        action="payment_reverse", resource_type="payment",
        resource_id=str(payment.id),
        before_data={"amount": str(payment.amount), "status": "normal"},
        after_data={"status": "reversed"},
    )
    db.commit()

    return resp(data={"id": str(payment.id), "status": "reversed"}, message="冲正成功")
