"""收款登记和冲正 API"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import check_owner_or_forbid, get_db, get_or_404, has_permission, require_permission, resp
from app.models.order import Payment, SalesOrder
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentCreated, PaymentReversed
from app.schemas.response import ApiResponse
from app.services.audit_service import get_request_meta, log_action

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
        query = query.join(SalesOrder).filter(SalesOrder.sales_user_id == current_user.id)
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    query = query.order_by(Payment.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return resp(
        data={
            "items": [
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
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        message="查询成功",
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
    order = get_or_404(db, SalesOrder, order_id, "订单")

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    if order.status not in ("confirmed", "partially_paid"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ORDER_INVALID_STATUS",
                "message": "只有已确认/部分收款的订单可以登记收款",
            },
        )

    amount = Decimal(str(data.amount))

    remaining = order.total_amount - order.paid_amount
    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail={"code": "PAYMENT_AMOUNT_EXCEEDED", "message": f"收款金额超过剩余应收（剩余 ¥{remaining}）"},
        )

    payment = Payment(
        order_id=order.id,
        amount=amount,
        payment_method=data.payment_method,
        operator_id=current_user.id,
        status="normal",
        remark=data.remark,
    )
    db.add(payment)

    order.paid_amount += amount

    # 更新订单状态
    if order.paid_amount >= order.total_amount:
        order.status = "completed"
    else:
        order.status = "partially_paid"

    order.updated_by = current_user.id
    log_action(
        db, action="payment_create", resource_type="payment",
        resource_id=str(payment.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"order_id": str(order.id), "amount": str(amount), "method": data.payment_method},
        **get_request_meta(request),
    )
    db.commit()

    return resp(
        data={
            "id": str(payment.id),
            "order_id": str(order.id),
            "amount": str(payment.amount),
            "payment_method": payment.payment_method,
            "order_status": order.status,
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

    order = db.query(SalesOrder).filter(SalesOrder.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "关联订单不存在"})

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    order.paid_amount -= payment.amount
    if order.paid_amount <= 0:
        order.paid_amount = Decimal("0")

    # 如果订单已完成，回退到已确认
    if order.status == "completed":
        order.status = "confirmed"

    payment.status = "reversed"
    order.updated_by = current_user.id
    log_action(
        db, action="payment_reverse", resource_type="payment",
        resource_id=str(payment.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"amount": str(payment.amount), "status": "normal"},
        after_data={"status": "reversed"},
        **get_request_meta(request),
    )
    db.commit()

    return resp(data={"id": str(payment.id), "status": "reversed"}, message="冲正成功")
