"""测试公共辅助函数"""

import uuid

from app.core.security import create_access_token, hash_password
from app.models.user import Permission, Role, RolePermission, User, UserRole


def make_user_with_perms(session_factory, username: str, perms: list[str]) -> str:
    """创建一个拥有指定权限列表的非超管用户，返回 JWT token。

    Args:
        session_factory: TestSession 类（可调用返回 session）
        username: 用户名
        perms: 权限代码列表（如 ["order:list", "order:view"]）
    """
    db = session_factory()
    try:
        user = User(
            id=uuid.uuid4(), username=username,
            hashed_password=hash_password("TestPass123!"),
            display_name=username, is_active=True, is_superuser=False,
        )
        db.add(user)
        role = Role(id=uuid.uuid4(), name=f"{username}_role", display_name=username)
        db.add(role)
        db.flush()
        for code in perms:
            perm = db.query(Permission).filter(Permission.code == code).first()
            if not perm:
                perm = Permission(id=uuid.uuid4(), code=code, name=code, module="test")
                db.add(perm)
                db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return create_access_token(str(user.id))
    finally:
        db.close()


def admin_auth_header(session_factory, username: str) -> dict:
    """直接生成 admin token 并返回 Authorization header。

    Args:
        session_factory: TestSession 类
        username: 已存在的管理员用户名
    """
    db = session_factory()
    try:
        user = db.query(User).filter(User.username == username).first()
        return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()
