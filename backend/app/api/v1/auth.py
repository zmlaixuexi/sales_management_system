
import time
import uuid
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import active_query, get_current_user, get_db, resp
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, RoleBrief
from app.services.audit_service import get_request_meta, log_action

router = APIRouter(
    prefix="/auth", tags=["认证"],
    responses={
        401: {"description": "用户名或密码错误"},
        403: {"description": "账户已禁用"},
    },
)

# 登录失败速率限制：每 IP 最多 LOGIN_FAIL_MAX 次失败 / LOGIN_FAIL_WINDOW_SECONDS 秒
_login_fail_lock = Lock()
_login_fail_counts: dict[str, list[float]] = defaultdict(list)


def _check_login_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _login_fail_lock:
        cutoff = now - settings.LOGIN_FAIL_WINDOW_SECONDS
        timestamps = _login_fail_counts[ip]
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if len(timestamps) >= settings.LOGIN_FAIL_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "RATE_LIMIT_EXCEEDED", "message": "登录失败次数过多，请 15 分钟后再试"},
            )


def _record_login_fail(ip: str) -> None:
    with _login_fail_lock:
        _login_fail_counts[ip].append(time.monotonic())


@router.post("/login")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    """用户名密码登录"""
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    meta = get_request_meta(request)
    user = active_query(db, User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        _record_login_fail(client_ip)
        log_action(db, action="login_failed", resource_type="user", actor_name=req.username, **meta)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "用户名或密码错误"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "账号已被禁用"},
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    log_action(
        db, action="login_success", resource_type="user",
        resource_id=str(user.id), actor_id=user.id, actor_name=user.display_name or user.username,
        **meta,
    )
    db.commit()

    return resp({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }, "登录成功")


@router.post("/refresh")
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """刷新 Token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTH_UNAUTHORIZED", "message": "Refresh Token 无效或已过期"},
    )
    try:
        payload = jwt.decode(req.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    user = active_query(db, User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    return resp({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }, "刷新成功")


@router.post("/logout")
def logout():
    """退出登录（前端清除 Token 即可）"""
    return resp(message="已退出登录")


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    roles = [
        RoleBrief(id=str(r.id), name=r.name, display_name=r.display_name)
        for r in current_user.roles
    ]
    permissions = list({
        p.code
        for r in current_user.roles
        for p in r.permissions
    })

    return resp({
        "id": str(current_user.id),
        "username": current_user.username,
        "display_name": current_user.display_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": [r.model_dump() for r in roles],
        "permissions": permissions,
    }, "查询成功")


@router.post("/change-password")
def change_password(
    request: Request,
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码"""
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PASSWORD", "message": "原密码错误"},
        )

    current_user.hashed_password = hash_password(req.new_password)
    meta = get_request_meta(request)
    log_action(
        db, action="password_change", resource_type="user",
        resource_id=str(current_user.id), actor_id=current_user.id,
        actor_name=current_user.display_name or current_user.username,
        after_data={"username": current_user.username, "action": "password_change"},
        **meta,
    )
    db.commit()

    return resp(message="密码修改成功")
