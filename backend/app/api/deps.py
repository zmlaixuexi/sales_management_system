import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """从 JWT Token 解析当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTH_UNAUTHORIZED", "message": "未登录或 Token 无效"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == uuid.UUID(user_id), User.deleted_at.is_(None)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def _get_user_permissions(user: User) -> set[str]:
    """获取用户所有权限码"""
    perms = set()
    for role in user.roles:
        for p in role.permissions:
            perms.add(p.code)
    return perms


def require_permission(permission_code: str):
    """权限校验依赖：检查当前用户是否拥有指定权限码。
    superuser 自动通过所有权限校验。
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        perms = _get_user_permissions(current_user)
        if permission_code not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "AUTH_FORBIDDEN", "message": "无权限执行此操作"},
            )
        return current_user
    return _check


def has_permission(user: User, permission_code: str) -> bool:
    """判断用户是否有指定权限（用于数据过滤，不抛异常）"""
    if user.is_superuser:
        return True
    return permission_code in _get_user_permissions(user)


def get_or_404(db: Session, model: type, entity_id: uuid.UUID | str, label: str = "资源"):
    """按 ID 查询实体，不存在则抛 404。自动过滤软删除。"""
    uid = uuid.UUID(str(entity_id))
    query = db.query(model).filter(model.id == uid)
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    obj = query.first()
    if not obj:
        raise HTTPException(
            status_code=404,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"{label}不存在"},
        )
    return obj


def resp(data=None, message: str = "操作成功") -> dict:
    """构建标准成功响应字典。"""
    return {"success": True, "data": data, "message": message}
