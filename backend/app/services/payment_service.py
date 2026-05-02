"""收款登记共享逻辑 — payments.py 和 orders.py 的规范路径共用"""

import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import active_query, check_owner_or_forbid
from app.models.order import Payment, SalesOrder
from app.models.user import User
from app.schemas.payment import PaymentCreate


def register_payment(
    db: Session,
    order_id: str,
    data: PaymentCreate,
    current_user: User,
) -> dict:
    """登记订单收款，返回响应数据 dict。"""
    # 加行锁防止并发收款导致超额
    order = (
        active_query(db, SalesOrder)
        .filter(SalesOrder.id == uuid.UUID(order_id))
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "订单不存在"})

    check_owner_or_forbid(current_user, order.sales_user_id, "order:view_all", "订单")

    if order.status not in ("confirmed", "partially_paid"):
        raise HTTPException(
            status_code=400,
            detail={"code": "ORDER_INVALID_STATUS", "message": "只有已确认/部分收款的订单可以登记收款"},
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
    if order.paid_amount >= order.total_amount:
        order.status = "completed"
    else:
        order.status = "partially_paid"

    order.updated_by = current_user.id
    db.flush()

    return {
        "payment": payment,
        "order": order,
        "amount": amount,
        "method": data.payment_method,
    }
