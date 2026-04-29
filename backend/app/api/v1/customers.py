"""客户 CRUD API"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission, has_permission
from app.models.customer import Customer
from app.models.user import User
from app.services.audit_service import log_action, get_request_meta

router = APIRouter(prefix="/customers", tags=["客户管理"])


@router.get("")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    source: str | None = None,
    owner_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:list")),
):
    """客户列表"""
    query = db.query(Customer).filter(Customer.deleted_at.is_(None))

    # 数据范围：无 customer:view_all 权限只能看本人客户
    if not has_permission(current_user, "customer:view_all"):
        query = query.filter(Customer.owner_user_id == current_user.id)

    if keyword:
        query = query.filter(
            (Customer.name.ilike(f"%{keyword}%")) |
            (Customer.phone.ilike(f"%{keyword}%")) |
            (Customer.contact_name.ilike(f"%{keyword}%"))
        )
    if source:
        query = query.filter(Customer.source == source)
    if owner_user_id:
        query = query.filter(Customer.owner_user_id == owner_user_id)

    query = query.order_by(Customer.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for c in items:
        result_items.append({
            "id": str(c.id),
            "name": c.name,
            "contact_name": c.contact_name,
            "phone": c.phone,
            "email": c.email,
            "source": c.source,
            "level": c.level,
            "owner_user_id": str(c.owner_user_id) if c.owner_user_id else None,
            "owner_name": c.owner.display_name if c.owner else None,
            "follow_status": c.follow_status,
            "remark": c.remark,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return {
        "success": True,
        "data": {
            "items": result_items,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        "message": "查询成功",
    }


@router.post("")
def create_customer(
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create")),
):
    """新增客户"""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "客户名称不能为空"})

    # 重复手机号提醒
    phone = data.get("phone")
    if phone:
        existing = db.query(Customer).filter(
            Customer.phone == phone, Customer.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail={"code": "CUSTOMER_DUPLICATED_WARNING", "message": f"手机号 {phone} 已被客户「{existing.name}」使用"},
            )

    customer = Customer(
        name=name,
        contact_name=data.get("contact_name"),
        phone=phone,
        email=data.get("email"),
        source=data.get("source"),
        level=data.get("level", "normal"),
        owner_user_id=uuid.UUID(str(data["owner_user_id"])) if data.get("owner_user_id") else current_user.id,
        follow_status=data.get("follow_status", "new"),
        remark=data.get("remark"),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(customer)
    db.flush()

    log_action(
        db, action="customer_create", resource_type="customer",
        resource_id=str(customer.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"name": name, "phone": phone},
        **get_request_meta(request),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "id": str(customer.id),
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
            "email": customer.email,
            "source": customer.source,
            "level": customer.level,
            "owner_user_id": str(customer.owner_user_id) if customer.owner_user_id else None,
            "follow_status": customer.follow_status,
        },
        "message": "创建成功",
    }


@router.get("/{customer_id}")
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:list")),
):
    """客户详情"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.deleted_at.is_(None)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "客户不存在"})

    return {
        "success": True,
        "data": {
            "id": str(customer.id),
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
            "email": customer.email,
            "source": customer.source,
            "level": customer.level,
            "owner_user_id": str(customer.owner_user_id) if customer.owner_user_id else None,
            "owner_name": customer.owner.display_name if customer.owner else None,
            "follow_status": customer.follow_status,
            "remark": customer.remark,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        },
        "message": "查询成功",
    }


@router.put("/{customer_id}")
def update_customer(
    customer_id: uuid.UUID,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:update")),
):
    """编辑客户"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.deleted_at.is_(None)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "客户不存在"})

    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "客户名称不能为空"})
        customer.name = name

    if "contact_name" in data:
        customer.contact_name = data["contact_name"]
    if "phone" in data:
        phone = data["phone"]
        if phone:
            existing = db.query(Customer).filter(
                Customer.phone == phone,
                Customer.id != customer_id,
                Customer.deleted_at.is_(None),
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "CUSTOMER_DUPLICATED_WARNING", "message": f"手机号 {phone} 已被其他客户使用"},
                )
        customer.phone = phone
    if "email" in data:
        customer.email = data["email"]
    if "source" in data:
        customer.source = data["source"]
    if "level" in data:
        customer.level = data["level"]
    if "follow_status" in data:
        customer.follow_status = data["follow_status"]
    if "owner_user_id" in data:
        customer.owner_user_id = uuid.UUID(str(data["owner_user_id"]))
    if "remark" in data:
        customer.remark = data["remark"]

    customer.updated_by = current_user.id
    log_action(
        db, action="customer_update", resource_type="customer",
        resource_id=str(customer.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"name": customer.name, "phone": customer.phone},
        **get_request_meta(request),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "id": str(customer.id),
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
        },
        "message": "更新成功",
    }


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:delete")),
):
    """删除客户（软删除）"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.deleted_at.is_(None)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "客户不存在"})

    customer.deleted_at = datetime.now()
    customer.updated_by = current_user.id
    log_action(
        db, action="customer_delete", resource_type="customer",
        resource_id=str(customer.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        before_data={"name": customer.name, "phone": customer.phone},
        **get_request_meta(request),
    )
    db.commit()

    return {"success": True, "data": None, "message": "删除成功"}


@router.post("/{customer_id}/transfer")
def transfer_customer(
    customer_id: uuid.UUID,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:update")),
):
    """转移客户归属销售"""
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.deleted_at.is_(None)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "客户不存在"})

    new_owner_id = data.get("owner_user_id")
    if not new_owner_id:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "必须指定新归属销售"})

    customer.owner_user_id = uuid.UUID(str(new_owner_id))
    customer.updated_by = current_user.id
    log_action(
        db, action="customer_transfer", resource_type="customer",
        resource_id=str(customer.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"owner_user_id": str(new_owner_id)},
        **get_request_meta(request),
    )
    db.commit()

    return {"success": True, "data": {"id": str(customer.id), "owner_user_id": str(customer.owner_user_id)}, "message": "转移成功"}
