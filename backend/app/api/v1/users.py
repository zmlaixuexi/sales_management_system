
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.sanitize import escape_like
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.auth import RoleBrief, UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["用户管理"])


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

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for u in users:
        roles = [RoleBrief(id=str(r.id), name=r.name, display_name=r.display_name) for r in u.roles]
        items.append({
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "phone": u.phone,
            "email": u.email,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "roles": [r.model_dump() for r in roles],
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        })

    return {
        "success": True,
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
        "message": "查询成功",
    }


@router.post("")
def create_user(req: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
        for rid in req.role_ids:
            db.add(UserRole(user_id=user.id, role_id=rid))

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "data": {"id": str(user.id), "username": user.username},
        "message": "创建成功",
    }


@router.put("/{user_id}")
def update_user(
    user_id: str,
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "无权限编辑用户"},
        )

    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": "用户不存在"},
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
        db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        for rid in req.role_ids:
            db.add(UserRole(user_id=user.id, role_id=rid))

    db.commit()

    return {"success": True, "message": "更新成功"}
