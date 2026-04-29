"""库存流水查询和手工调整 API"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.order import InventoryMovement
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import InventoryAdjust, InventoryAdjusted
from app.schemas.response import ApiResponse
from app.services.audit_service import get_request_meta, log_action

router = APIRouter(
    prefix="/inventory", tags=["库存管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "参数验证失败"},
        404: {"description": "商品不存在"},
    },
)


@router.get("/movements")
def list_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: uuid.UUID | None = None,
    movement_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:list")),
):
    """库存流水"""
    query = db.query(InventoryMovement)
    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)

    query = query.order_by(InventoryMovement.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "movement_type": m.movement_type,
                    "quantity_before": m.quantity_before,
                    "quantity_change": m.quantity_change,
                    "quantity_after": m.quantity_after,
                    "related_type": m.related_type,
                    "related_id": str(m.related_id) if m.related_id else None,
                    "remark": m.remark,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in items
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        "message": "查询成功",
    }


@router.post("/adjustments", response_model=ApiResponse[InventoryAdjusted])
def adjust_inventory(
    data: InventoryAdjust,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:adjust")),
):
    """手工库存调整"""
    product_id = data.product_id
    quantity_change = data.quantity_change
    if quantity_change == 0:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "调整数量不能为 0"})

    product = db.query(Product).filter(
        Product.id == uuid.UUID(str(product_id)), Product.deleted_at.is_(None)
    ).with_for_update().first()
    if not product:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "商品不存在"})

    before = product.stock_quantity
    after = before + quantity_change
    if after < 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVENTORY_NOT_ENOUGH",
                "message": f"库存不能为负（当前 {before}，调整 {quantity_change}）",
            },
        )

    product.stock_quantity = after

    movement = InventoryMovement(
        product_id=product.id,
        movement_type="manual_adjust",
        quantity_before=before,
        quantity_change=quantity_change,
        quantity_after=after,
        operator_id=current_user.id,
        remark=data.remark,
    )
    db.add(movement)
    log_action(
        db, action="inventory_adjust", resource_type="product",
        resource_id=str(product.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"stock_quantity": before},
        after_data={"stock_quantity": after, "change": quantity_change},
        **get_request_meta(request),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "product_id": str(product.id),
            "quantity_before": before,
            "quantity_change": quantity_change,
            "quantity_after": after,
        },
        "message": "调整成功",
    }
