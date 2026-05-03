from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    parse_uuid_or_400,
    resp,
    safe_commit,
)
from app.core.sanitize import sanitize_text as _sanitize
from app.models.user import Permission, Role, RolePermission, User, UserRole
from app.services.audit_service import log_user_action

router = APIRouter(
    prefix="/roles", tags=["角色管理"],
    responses={
        401: {"description": "未认证"},
        403: {"description": "仅超级管理员可操作"},
        404: {"description": "角色不存在"},
    },
)


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=255)
    permission_ids: list[str] = []

    @field_validator("name", "display_name", "description")
    @classmethod
    def sanitize_fields(cls, v: str | None) -> str | None:
        return _sanitize(v) if v else v


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    display_name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=255)
    permission_ids: list[str] | None = None

    @field_validator("name", "display_name", "description")
    @classmethod
    def sanitize_fields(cls, v: str | None) -> str | None:
        return _sanitize(v) if v else v


def _require_superuser(current_user: User) -> None:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "仅超级管理员可管理角色"},
        )


def _serialize_role(role: Role) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "permissions": [
            {"id": str(p.id), "code": p.code, "name": p.name, "module": p.module}
            for p in role.permissions
        ],
        "user_count": len(role.users),
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }


@router.get("")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """角色列表（含权限详情和用户数量）"""
    _require_superuser(current_user)

    roles = db.query(Role).order_by(Role.name).all()
    return resp([_serialize_role(r) for r in roles])


@router.get("/permissions")
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """所有可用权限（按模块分组）"""
    _require_superuser(current_user)

    perms = db.query(Permission).order_by(Permission.module, Permission.code).all()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for p in perms:
        grouped[p.module].append({
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "module": p.module,
        })
    return resp(dict(grouped))


@router.post("")
def create_role(
    req: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建角色"""
    _require_superuser(current_user)

    if db.query(Role).filter(Role.name == req.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": "角色名已存在"},
        )

    role = Role(
        name=req.name,
        display_name=req.display_name,
        description=req.description,
    )
    db.add(role)
    db.flush()

    if req.permission_ids:
        parsed_ids = [parse_uuid_or_400(pid, "权限 ID") for pid in req.permission_ids]
        _validate_permissions_exist(db, parsed_ids)
        for pid in parsed_ids:
            db.add(RolePermission(role_id=role.id, permission_id=pid))

    safe_commit(db)
    db.refresh(role)

    log_user_action(
        db, request, current_user,
        action="role_create", resource_type="role", resource_id=str(role.id),
        after_data={"name": role.name, "display_name": role.display_name},
    )
    safe_commit(db)

    return resp(_serialize_role(role), "创建成功")


@router.put("/{role_id}")
def update_role(
    role_id: str,
    req: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑角色"""
    _require_superuser(current_user)

    role = db.query(Role).filter(Role.id == parse_uuid_or_400(role_id, "角色 ID")).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": "角色不存在"},
        )

    before = {"name": role.name, "display_name": role.display_name}

    if req.name is not None:
        existing = db.query(Role).filter(Role.name == req.name, Role.id != role.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "VALIDATION_FAILED", "message": "角色名已存在"},
            )
        role.name = req.name
    if req.display_name is not None:
        role.display_name = req.display_name
    if req.description is not None:
        role.description = req.description
    if req.permission_ids is not None:
        parsed_ids = [parse_uuid_or_400(pid, "权限 ID") for pid in req.permission_ids]
        _validate_permissions_exist(db, parsed_ids)
        db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
        for pid in parsed_ids:
            db.add(RolePermission(role_id=role.id, permission_id=pid))

    safe_commit(db)
    db.refresh(role)

    log_user_action(
        db, request, current_user,
        action="role_update", resource_type="role", resource_id=str(role.id),
        before_data=before,
        after_data={"name": role.name, "display_name": role.display_name},
    )
    safe_commit(db)

    return resp(_serialize_role(role), "更新成功")


@router.delete("/{role_id}")
def delete_role(
    role_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除角色（有用户关联时拒绝）"""
    _require_superuser(current_user)

    role = db.query(Role).filter(Role.id == parse_uuid_or_400(role_id, "角色 ID")).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": "角色不存在"},
        )

    user_count = db.query(UserRole).filter(UserRole.role_id == role.id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": f"该角色已分配给 {user_count} 个用户，无法删除"},
        )

    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    db.delete(role)

    log_user_action(
        db, request, current_user,
        action="role_delete", resource_type="role", resource_id=str(role.id),
        before_data={"name": role.name, "display_name": role.display_name},
    )
    safe_commit(db)

    return resp(message="删除成功")


def _validate_permissions_exist(db: Session, permission_ids: list) -> None:
    found = db.query(Permission.id).filter(Permission.id.in_(permission_ids)).all()
    found_ids = {p.id for p in found}
    missing = set(permission_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_FAILED", "message": f"权限不存在: {missing.pop()}"},
        )
