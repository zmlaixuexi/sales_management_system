"""收款登记共享逻辑 — payments.py 和 orders.py 的规范路径共用"""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import check_owner_or_forbid, get_or_404
from app.models.order import Payment, SalesOrder
from app.models.user import User
from app.schemas.payment import PaymentCreate


def register_payment(
    db: Session,
    order_id: str,
    data: PaymentCreate,
    current_user: User,
    request_meta: dict,
) -> dict:
    """登记订单收款，返回响应数据 dict。"""
    order = get_or_404(db, SalesOrder, order_id, "订单")
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
