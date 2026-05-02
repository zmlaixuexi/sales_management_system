"""初始化管理员账号和基础角色、权限的种子数据脚本"""

import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Permission, Role, RolePermission, User, UserRole

logger = logging.getLogger(__name__)


# 基础权限定义
PERMISSIONS = [
    # 用户管理
    ("user:list", "查看用户列表", "用户管理"),
    ("user:create", "创建用户", "用户管理"),
    ("user:update", "编辑用户", "用户管理"),
    ("user:delete", "删除用户", "用户管理"),
    # 角色管理
    ("role:list", "查看角色列表", "角色管理"),
    ("role:create", "创建角色", "角色管理"),
    ("role:update", "编辑角色", "角色管理"),
    ("role:delete", "删除角色", "角色管理"),
    # 商品管理
    ("product:list", "查看商品列表", "商品管理"),
    ("product:create", "创建商品", "商品管理"),
    ("product:update", "编辑商品", "商品管理"),
    ("product:delete", "删除商品", "商品管理"),
    ("product:view_cost", "查看成本价和毛利", "商品管理"),
    # 客户管理
    ("customer:list", "查看客户列表", "客户管理"),
    ("customer:create", "创建客户", "客户管理"),
    ("customer:update", "编辑客户", "客户管理"),
    ("customer:delete", "删除客户", "客户管理"),
    ("customer:view_all", "查看全部客户（含其他销售客户）", "客户管理"),
    # 订单管理
    ("order:list", "查看订单列表", "订单管理"),
    ("order:create", "创建订单", "订单管理"),
    ("order:update", "编辑订单", "订单管理"),
    ("order:confirm", "确认订单", "订单管理"),
    ("order:cancel", "取消订单", "订单管理"),
    ("order:view_all", "查看全部订单（含其他销售订单）", "订单管理"),
    # 库存管理
    ("inventory:list", "查看库存", "库存管理"),
    ("inventory:adjust", "库存调整", "库存管理"),
    # 收款管理
    ("payment:list", "查看收款列表", "收款管理"),
    ("payment:create", "登记收款", "收款管理"),
    ("payment:reverse", "冲正收款", "收款管理"),
    # 报表
    ("report:sales", "查看销售报表（含排行榜）", "报表"),
    ("report:profit", "查看利润报表", "报表"),
    # 审计日志
    ("audit:view", "查看操作日志", "审计"),
]

# 角色定义：角色名 -> 权限 code 列表
ROLE_PERMISSIONS = {
    "admin": [p[0] for p in PERMISSIONS],
    "sales_manager": [
        "product:list", "product:view_cost",
        "customer:list", "customer:create", "customer:update", "customer:view_all",
        "order:list", "order:create", "order:update", "order:confirm", "order:cancel", "order:view_all",
        "payment:list",
        "report:sales", "report:profit",
        "inventory:list",
    ],
    "sales": [
        "product:list",
        "customer:list", "customer:create", "customer:update",
        "order:list", "order:create", "order:update", "order:confirm",
        "payment:list",
    ],
    "inventory": [
        "product:list", "product:create", "product:update",
        "inventory:list", "inventory:adjust",
        "order:list",
    ],
    "finance": [
        "product:list", "product:view_cost",
        "order:list", "order:view_all",
        "payment:list", "payment:create", "payment:reverse",
        "report:sales", "report:profit",
    ],
    "audit": [
        "audit:view",
    ],
}


def seed_all(db: Session | None = None) -> None:
    """执行全部种子数据初始化"""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        _seed_permissions(db)
        _seed_roles(db)
        _seed_admin_user(db)
        db.commit()
        logger.info("种子数据初始化完成")
    except Exception as e:
        db.rollback()
        logger.error("种子数据初始化失败: %s", e)
        raise
    finally:
        if close_db:
            db.close()


def _seed_permissions(db: Session) -> None:
    for code, name, module in PERMISSIONS:
        existing = db.query(Permission).filter(Permission.code == code).first()
        if not existing:
            db.add(Permission(code=code, name=name, module=module))


def _seed_roles(db: Session) -> None:
    role_display = {
        "admin": "系统管理员",
        "sales_manager": "销售主管",
        "sales": "销售人员",
        "inventory": "库存/运营",
        "finance": "财务/老板",
        "audit": "只读审计",
    }
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, display_name=role_display.get(role_name, role_name))
            db.add(role)
            db.flush()

            for code in perm_codes:
                perm = db.query(Permission).filter(Permission.code == code).first()
                if perm:
                    existing_rp = db.query(RolePermission).filter(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    ).first()
                    if not existing_rp:
                        db.add(RolePermission(role_id=role.id, permission_id=perm.id))


def _seed_admin_user(db: Session) -> None:
    admin = db.query(User).filter(User.username == "admin", User.deleted_at.is_(None)).first()
    if not admin:
        admin = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            display_name="系统管理员",
            is_superuser=True,
            is_active=True,
        )
        db.add(admin)
        db.flush()

        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            existing = db.query(UserRole).filter(
                UserRole.user_id == admin.id,
                UserRole.role_id == admin_role.id,
            ).first()
            if not existing:
                db.add(UserRole(user_id=admin.id, role_id=admin_role.id))


if __name__ == "__main__":
    seed_all()
