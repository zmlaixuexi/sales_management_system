"""收款登记和冲正 API"""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.models.order import Payment, SalesOrder
from app.models.user import User
from app.services.audit_service import log_action, get_request_meta

router = APIRouter(prefix="/payments", tags=["收款管理"])


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
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    query = query.order_by(Payment.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
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
        "message": "查询成功",
    }


@router.post("/orders/{order_id}/payments")
def create_payment(
    order_id: uuid.UUID,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payment:create")),
):
    """登记订单收款"""
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

    if order.status not in ("confirmed", "partially_paid"):
        raise HTTPException(status_code=400, detail={"code": "ORDER_INVALID_STATUS", "message": "只有已确认/部分收款的订单可以登记收款"})

    amount = Decimal(str(data.get("amount", "0")))
    if amount <= 0:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "收款金额必须大于 0"})

    remaining = order.total_amount - order.paid_amount
    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail={"code": "PAYMENT_AMOUNT_EXCEEDED", "message": f"收款金额超过剩余应收（剩余 ¥{remaining}）"},
        )

    payment = Payment(
        order_id=order.id,
        amount=amount,
        payment_method=data.get("payment_method", "cash"),
        operator_id=current_user.id,
        status="normal",
        remark=data.get("remark"),
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
        after_data={"order_id": str(order.id), "amount": str(amount), "method": data.get("payment_method", "cash")},
        **get_request_meta(request),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "id": str(payment.id),
            "order_id": str(order.id),
            "amount": str(payment.amount),
            "payment_method": payment.payment_method,
            "order_status": order.status,
        },
        "message": "收款登记成功",
    }


@router.post("/{payment_id}/reverse")
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

    return {"success": True, "data": {"id": str(payment.id), "status": "reversed"}, "message": "冲正成功"}
