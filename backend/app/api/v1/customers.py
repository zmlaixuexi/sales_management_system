"""客户 CRUD API"""

import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, has_permission, require_permission
from app.core.sanitize import escape_like
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerTransfer, CustomerUpdate
from app.models.user import User
from app.services.audit_service import get_request_meta, log_action

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
        escaped = escape_like(keyword)
        query = query.filter(
            (Customer.name.ilike(f"%{escaped}%", escape="\\")) |
            (Customer.phone.ilike(f"%{escaped}%", escape="\\")) |
            (Customer.contact_name.ilike(f"%{escaped}%", escape="\\"))
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
    data: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create")),
):
    """新增客户"""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "客户名称不能为空"})

    # 重复手机号提醒
    phone = data.phone
    if phone:
        existing = db.query(Customer).filter(
            Customer.phone == phone, Customer.deleted_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CUSTOMER_DUPLICATED_WARNING",
                    "message": f"手机号 {phone} 已被客户「{existing.name}」使用",
                },
            )

    customer = Customer(
        name=name,
        contact_name=data.contact_name,
        phone=phone,
        email=data.email,
        source=data.source,
        level=data.level,
        owner_user_id=uuid.UUID(str(data.owner_user_id)) if data.owner_user_id else current_user.id,
        follow_status=data.follow_status,
        remark=data.remark,
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
    data: CustomerUpdate,
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

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_FAILED", "message": "客户名称不能为空"})
        customer.name = name

    if data.contact_name is not None:
        customer.contact_name = data.contact_name
    if data.phone is not None:
        phone = data.phone
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
    if data.email is not None:
        customer.email = data.email
    if data.source is not None:
        customer.source = data.source
    if data.level is not None:
        customer.level = data.level
    if data.follow_status is not None:
        customer.follow_status = data.follow_status
    if data.owner_user_id is not None:
        customer.owner_user_id = uuid.UUID(str(data.owner_user_id))
    if data.remark is not None:
        customer.remark = data.remark

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
    data: CustomerTransfer,
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

    new_owner_id = data.owner_user_id

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

    return {
        "success": True,
        "data": {"id": str(customer.id), "owner_user_id": str(customer.owner_user_id)},
        "message": "转移成功",
    }


@router.post("/import")
async def import_customers_csv(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create")),
):
    """批量导入客户（CSV 格式）"""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "请上传 CSV 文件",
        })

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "文件编码错误，请使用 UTF-8",
        })

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail={
            "code": "VALIDATION_FAILED", "message": "CSV 文件为空或缺少表头",
        })

    # 批量内手机号去重
    used_phones: set[str] = set()
    created = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        name = (row.get("客户名称") or row.get("name") or "").strip()
        if not name:
            errors.append({"row": row_num, "message": "客户名称不能为空"})
            continue

        phone = (row.get("电话") or row.get("phone") or "").strip() or None
        if phone:
            # 批量内去重
            if phone in used_phones:
                errors.append({"row": row_num, "message": f"手机号 {phone} 在文件中重复"})
                continue
            # 数据库去重
            existing = db.query(Customer).filter(
                Customer.phone == phone, Customer.deleted_at.is_(None),
            ).first()
            if existing:
                errors.append({"row": row_num, "message": f"手机号 {phone} 已被客户「{existing.name}」使用"})
                continue
            used_phones.add(phone)

        contact_name = (row.get("联系人") or row.get("contact_name") or "").strip() or None
        email = (row.get("邮箱") or row.get("email") or "").strip() or None
        source = (row.get("来源") or row.get("source") or "").strip() or None
        level = (row.get("等级") or row.get("level") or "").strip() or "normal"
        remark = (row.get("备注") or row.get("remark") or "").strip() or None

        customer = Customer(
            id=uuid.uuid4(),
            name=name,
            contact_name=contact_name,
            phone=phone,
            email=email,
            source=source,
            level=level,
            owner_user_id=current_user.id,
            follow_status="new",
            remark=remark,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        db.add(customer)
        created += 1

    db.commit()

    log_action(db, actor_id=current_user.id, actor_name=current_user.display_name,
               action="customer_import", resource_type="customer",
               after_data={"created": created, "errors": len(errors)},
               **get_request_meta(request))
    db.commit()

    return {
        "success": True,
        "data": {"created": created, "errors": errors},
        "message": f"成功导入 {created} 个客户" + (f"，{len(errors)} 行跳过" if errors else ""),
    }
