import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, CurrentUser, RoleBrief
from app.services.audit_service import log_action, get_request_meta

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    """用户名密码登录"""
    meta = get_request_meta(request)
    user = db.query(User).filter(User.username == req.username, User.deleted_at.is_(None)).first()
    if not user or not verify_password(req.password, user.hashed_password):
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

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        "message": "登录成功",
    }


@router.post("/refresh")
def refresh_token(req: RefreshRequest):
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
        raise credentials_exception

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        "message": "刷新成功",
    }


@router.post("/logout")
def logout():
    """退出登录（前端清除 Token 即可）"""
    return {"success": True, "message": "已退出登录"}


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

    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "username": current_user.username,
            "display_name": current_user.display_name,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "roles": [r.model_dump() for r in roles],
            "permissions": permissions,
        },
        "message": "查询成功",
    }
