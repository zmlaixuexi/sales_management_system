"""客户 CRUD API"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    check_owner_or_forbid,
    get_db,
    get_or_404,
    has_permission,
    parse_uuid_or_400,
    require_permission,
    resp,
)
from app.core.config import settings
from app.core.sanitize import escape_like, strip_html
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import (
    CustomerBrief,
    CustomerCreate,
    CustomerDetail,
    CustomerTransfer,
    CustomerUpdate,
)
from app.schemas.response import ApiResponse
from app.services.audit_service import get_request_meta, log_action
from app.services.csv_import import validate_csv_upload

router = APIRouter(
    prefix="/customers", tags=["客户管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "无权限"},
        400: {"description": "参数验证失败"},
        404: {"description": "客户不存在"},
        409: {"description": "手机号重复"},
    },
)


def _validate_owner_user(db: Session, owner_uid: uuid.UUID) -> None:
    """校验归属用户存在且活跃"""
    target = db.query(User).filter(
        User.id == owner_uid, User.is_active.is_(True), User.deleted_at.is_(None),
    ).first()
    if not target:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_FAILED", "message": "归属用户不存在或已禁用"},
        )


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
    items = query.options(joinedload(Customer.owner)).offset((page - 1) * page_size).limit(page_size).all()

    result_items = [{
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
    } for c in items]

    return resp(
        data={
            "items": result_items,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        message="查询成功",
    )


@router.post("", response_model=ApiResponse[CustomerBrief])
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

    owner_uid = current_user.id
    if data.owner_user_id:
        owner_uid = parse_uuid_or_400(data.owner_user_id, "归属用户 ID")
        _validate_owner_user(db, owner_uid)

    customer = Customer(
        name=name,
        contact_name=data.contact_name,
        phone=phone,
        email=data.email,
        source=data.source,
        level=data.level,
        owner_user_id=owner_uid,
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

    return resp(
        data={
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
        message="创建成功",
    )


@router.get("/{customer_id}", response_model=ApiResponse[CustomerDetail])
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:list")),
):
    """客户详情"""
    customer = get_or_404(db, Customer, customer_id, "客户")

    check_owner_or_forbid(current_user, customer.owner_user_id, "customer:view_all", "客户")

    return resp(
        data={
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
        message="查询成功",
    )


@router.put("/{customer_id}")
def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:update")),
):
    """编辑客户"""
    customer = get_or_404(db, Customer, customer_id, "客户")

    check_owner_or_forbid(current_user, customer.owner_user_id, "customer:view_all", "客户")

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
        owner_uid = parse_uuid_or_400(data.owner_user_id, "归属用户 ID")
        _validate_owner_user(db, owner_uid)
        customer.owner_user_id = owner_uid
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

    return resp(
        data={
            "id": str(customer.id),
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
        },
        message="更新成功",
    )


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:delete")),
):
    """删除客户（软删除）"""
    customer = get_or_404(db, Customer, customer_id, "客户")

    check_owner_or_forbid(current_user, customer.owner_user_id, "customer:view_all", "客户")

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

    return resp(data=None, message="删除成功")


@router.post("/{customer_id}/transfer")
def transfer_customer(
    customer_id: uuid.UUID,
    data: CustomerTransfer,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:update")),
):
    """转移客户归属销售"""
    customer = get_or_404(db, Customer, customer_id, "客户")

    check_owner_or_forbid(current_user, customer.owner_user_id, "customer:view_all", "客户")

    new_owner_id = data.owner_user_id
    owner_uid = parse_uuid_or_400(new_owner_id, "归属用户 ID")

    # 校验目标用户存在且活跃
    _validate_owner_user(db, owner_uid)

    customer.owner_user_id = owner_uid
    customer.updated_by = current_user.id
    log_action(
        db, action="customer_transfer", resource_type="customer",
        resource_id=str(customer.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"owner_user_id": str(new_owner_id)},
        **get_request_meta(request),
    )
    db.commit()

    return resp(
        data={"id": str(customer.id), "owner_user_id": str(customer.owner_user_id)},
        message="转移成功",
    )


@router.post("/import")
async def import_customers_csv(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer:create")),
):
    """批量导入客户（CSV 格式）"""
    reader = await validate_csv_upload(file)

    # 批量内手机号去重
    used_phones: set[str] = set()
    # 预加载已有手机号，避免逐行查询数据库
    existing_phones = {
        p for (p,) in db.query(Customer.phone).filter(
            Customer.phone.isnot(None), Customer.deleted_at.is_(None),
        ).all()
    }
    created = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        if row_num - 1 > settings.MAX_CSV_IMPORT_ROWS:
            errors.append({"row": row_num, "message": f"超过最大行数限制 {settings.MAX_CSV_IMPORT_ROWS}"})
            break
        name = strip_html((row.get("客户名称") or row.get("name") or "").strip())
        if not name:
            errors.append({"row": row_num, "message": "客户名称不能为空"})
            continue

        phone = (row.get("电话") or row.get("phone") or "").strip() or None
        if phone:
            # 批量内去重
            if phone in used_phones:
                errors.append({"row": row_num, "message": f"手机号 {phone} 在文件中重复"})
                continue
            # 数据库去重（使用预加载的集合）
            if phone in existing_phones:
                errors.append({"row": row_num, "message": f"手机号 {phone} 已被使用"})
                continue
            used_phones.add(phone)

        contact_name = strip_html((row.get("联系人") or row.get("contact_name") or "").strip()) or None
        email = strip_html((row.get("邮箱") or row.get("email") or "").strip()) or None
        source = strip_html((row.get("来源") or row.get("source") or "").strip()) or None
        level = strip_html((row.get("等级") or row.get("level") or "").strip()) or "normal"
        remark = strip_html((row.get("备注") or row.get("remark") or "").strip()) or None

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

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "IMPORT_FAILED", "message": "导入失败，请检查数据后重试"},
        ) from None

    log_action(db, actor_id=current_user.id, actor_name=current_user.display_name,
               action="customer_import", resource_type="customer",
               after_data={"created": created, "errors": len(errors)},
               **get_request_meta(request))
    db.commit()

    return resp(
        data={"created": created, "errors": errors},
        message=f"成功导入 {created} 个客户" + (f"，{len(errors)} 行跳过" if errors else ""),
    )
