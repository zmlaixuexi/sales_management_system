import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.config import settings
from app.core.user_context import user_id_ctx
from app.db.session import Base, SessionLocal
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
        raise credentials_exception from None

    user = db.query(User).filter(User.id == uuid.UUID(user_id), User.deleted_at.is_(None)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    user_id_ctx.set(user_id)
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


def check_owner_or_forbid(user: User, owner_id, view_all_code: str, label: str = "资源"):
    """对象级权限：非 view_all 用户只能操作本人数据，否则 403。"""
    if user.is_superuser:
        return
    if has_permission(user, view_all_code):
        return
    if owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": f"无权访问此{label}"},
        )


def parse_uuid_or_400(value: str, label: str) -> uuid.UUID:
    """将字符串安全转换为 UUID，无效则抛 400 VALIDATION_FAILED。"""
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_FAILED", "message": f"{label}格式无效"},
        ) from None


def get_or_404(db: Session, model: type[Base], entity_id: uuid.UUID | str, label: str = "资源"):
    """按 ID 查询实体，不存在或 ID 格式无效则抛 404。自动过滤软删除。"""
    try:
        uid = uuid.UUID(str(entity_id))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=404,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"{label}不存在"},
        ) from None
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
    from app.core.request_id import request_id_ctx
    rid = request_id_ctx.get("")
    result = {"success": True, "data": data, "message": message}
    if rid:
        result["request_id"] = rid
    return result


def generate_sequential_code(db: Session, model: type[Base], column: InstrumentedAttribute[str], prefix: str) -> str:
    """生成带日期前缀的序号编码，格式: {prefix}YYYYMMDD-NNNN。

    查询当天最大序号并递增，用于订单号和 SKU 自动生成。
    """
    today = datetime.now().strftime("%Y%m%d")
    full_prefix = f"{prefix}{today}-"
    last = (
        db.query(model)
        .filter(column.like(f"{full_prefix}%"))
        .order_by(column.desc())
        .first()
    )
    last_value = getattr(last, column.key, None) if last else None
    if last_value and str(last_value).startswith(full_prefix):
        try:
            seq = int(str(last_value)[len(full_prefix):]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{full_prefix}{seq:04d}"
