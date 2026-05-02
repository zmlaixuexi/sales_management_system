from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, paginate, paginated_resp, parse_uuid_or_400, resp
from app.core.sanitize import escape_like
from app.core.security import hash_password
from app.models.user import Role, User, UserRole
from app.schemas.auth import RoleBrief, UserCreate, UserUpdate
from app.services.audit_service import log_user_action

router = APIRouter(
    prefix="/users", tags=["用户管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "仅超级管理员可操作"},
        404: {"description": "用户不存在"},
    },
)


def _validate_roles_exist(db: Session, role_ids: list) -> None:
    """校验所有 role_id 是否存在"""
    found = db.query(Role.id).filter(Role.id.in_(role_ids)).all()
    found_ids = {r.id for r in found}
    missing = set(role_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": f"角色不存在: {missing.pop()}"},
        )


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户列表（需要管理员权限）"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限访问用户管理"},
        )

    query = db.query(User).filter(User.deleted_at.is_(None))
    if keyword:
        query = query.filter(User.username.ilike(f"%{escape_like(keyword)}%", escape="\\"))

    users, total = paginate(query.order_by(User.created_at.desc()), page, page_size)

    items = [{
        "id": str(u.id),
        "username": u.username,
        "display_name": u.display_name,
        "phone": u.phone,
        "email": u.email,
        "is_active": u.is_active,
        "is_superuser": u.is_superuser,
        "roles": [RoleBrief(id=str(r.id), name=r.name, display_name=r.display_name).model_dump() for r in u.roles],
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    } for u in users]

    return paginated_resp(items, page, page_size, total)


@router.post("")
def create_user(
    req: UserCreate, request: Request,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """新增用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限创建用户"},
        )

    if db.query(User).filter(User.username == req.username, User.deleted_at.is_(None)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": "用户名已存在"},
        )

    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        display_name=req.display_name,
        phone=req.phone,
        email=req.email,
    )
    db.add(user)
    db.flush()

    if req.role_ids:
        parsed_role_ids = [parse_uuid_or_400(rid, "角色 ID") for rid in req.role_ids]
        _validate_roles_exist(db, parsed_role_ids)
        for rid in parsed_role_ids:
            db.add(UserRole(user_id=user.id, role_id=rid))

    db.commit()
    db.refresh(user)

    log_user_action(
        db, request, current_user,
        action="user_create", resource_type="user", resource_id=str(user.id),
        after_data={"username": user.username, "display_name": user.display_name},
    )
    db.commit()

    return resp({"id": str(user.id), "username": user.username}, "创建成功")


@router.put("/{user_id}")
def update_user(
    user_id: str,
    req: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限编辑用户"},
        )

    user = db.query(User).filter(User.id == parse_uuid_or_400(user_id, "用户 ID"), User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": "用户不存在"},
        )

    if req.is_active is False and user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": "不能停用自己的账号"},
        )

    if req.display_name is not None:
        user.display_name = req.display_name
    if req.phone is not None:
        user.phone = req.phone
    if req.email is not None:
        user.email = req.email
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.role_ids is not None:
        parsed_role_ids = [parse_uuid_or_400(rid, "角色 ID") for rid in req.role_ids]
        _validate_roles_exist(db, parsed_role_ids)
        db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        for rid in parsed_role_ids:
            db.add(UserRole(user_id=user.id, role_id=rid))

    db.commit()

    after: dict = {"username": user.username, "display_name": user.display_name}
    if req.is_active is not None:
        after["is_active"] = req.is_active
    log_user_action(
        db, request, current_user,
        action="user_update", resource_type="user", resource_id=str(user.id),
        after_data=after,
    )
    db.commit()

    return resp(message="更新成功")


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """角色列表（需要管理员权限）"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限访问角色列表"},
        )

    roles = db.query(Role).order_by(Role.name).all()
    items = [{"id": str(r.id), "name": r.name, "display_name": r.display_name} for r in roles]
    return resp(items)
