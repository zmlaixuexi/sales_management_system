"""
代码质量：后端服务层函数调用链与事务边界一致性验证测试
覆盖事务提交模式、实体获取模式、
写入端点事务一致性、库存敏感操作、服务层共享模式
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
PAYMENT_SERVICE_SRC = (ROOT / "app" / "services" / "payment_service.py").read_text()

API_DIR = ROOT / "app" / "api" / "v1"
WRITE_MODULES = ["products", "customers", "orders", "payments", "inventory"]

SOURCES = {}
for name in WRITE_MODULES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()

ALL_API_SOURCES = {}
for p in API_DIR.glob("*.py"):
    ALL_API_SOURCES[p.stem] = p.read_text()


def _count_safe_commit(src: str) -> int:
    return len(re.findall(r'safe_commit\(db\)', src))


def _count_db_commit(src: str) -> int:
    # 直接 db.commit() 但不在 safe_commit 内部的
    return len(re.findall(r'(?<!safe_\w)db\.commit\(\)', src))


def _has_write_endpoints(src: str) -> bool:
    """检查是否有写入端点（POST/PUT/DELETE/PATCH）"""
    return bool(re.search(r'@router\.(post|put|delete|patch)', src))


# ═══════════════════════════════════════════════════════════
# 1. 事务提交模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTransactionCommitPatterns:
    """写入端点使用 safe_commit 而非直接 db.commit"""

    def test_safe_commit_defined_in_deps(self):
        """safe_commit 在 deps.py 中正确定义"""
        assert "def safe_commit(db: Session)" in DEPS_SRC, (
            "deps.py 应定义 safe_commit(db: Session)"
        )
        assert "db.commit()" in DEPS_SRC, "safe_commit 应调用 db.commit()"
        assert "db.rollback()" in DEPS_SRC, "safe_commit 异常时应 db.rollback()"

    def test_write_modules_use_safe_commit(self):
        """所有写入模块使用 safe_commit"""
        for name in WRITE_MODULES:
            src = SOURCES[name]
            if _has_write_endpoints(src):
                assert _count_safe_commit(src) > 0, (
                    f"{name} 有写入端点但未使用 safe_commit"
                )

    def test_no_direct_db_commit_in_route_modules(self):
        """路由模块不直接调用 db.commit()"""
        for name, src in ALL_API_SOURCES.items():
            # 排除 safe_commit 内部的 db.commit（deps.py 本身）
            if name == "deps":
                continue
            # 查找不在 safe_commit 调用中的 db.commit
            commits = re.findall(r'(?<!safe_\w{7})db\.commit\(\)', src)
            assert len(commits) == 0, (
                f"{name} 不应直接调用 db.commit()，应使用 safe_commit(db)"
            )

    def test_no_manual_rollback_in_routes(self):
        """路由模块不手动调用 db.rollback()（由 safe_commit 统一处理）"""
        for name, src in ALL_API_SOURCES.items():
            if name == "deps":
                continue
            rollbacks = re.findall(r'db\.rollback\(\)', src)
            assert len(rollbacks) == 0, (
                f"{name} 不应手动调用 db.rollback()，应由 safe_commit 统一处理"
            )

    def test_safe_commit_wraps_commit_in_try_except(self):
        """safe_commit 使用 try/except 包裹 commit"""
        safe_commit_block = DEPS_SRC[DEPS_SRC.find("def safe_commit"):]
        safe_commit_block = safe_commit_block[:safe_commit_block.find("\ndef ", 1) if "\ndef " in safe_commit_block[1:] else len(safe_commit_block)]
        assert "try:" in safe_commit_block, "safe_commit 应使用 try 包裹 db.commit()"
        assert "except Exception:" in safe_commit_block or "except:" in safe_commit_block, (
            "safe_commit 应捕获异常"
        )
        assert "raise" in safe_commit_block, "safe_commit 应重新抛出异常"


# ═══════════════════════════════════════════════════════════
# 2. 实体获取模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEntityFetchingPatterns:
    """实体获取使用正确的辅助函数"""

    def test_get_or_404_defined_in_deps(self):
        """get_or_404 在 deps.py 中定义"""
        assert "def get_or_404(" in DEPS_SRC, "应定义 get_or_404 函数"
        assert "HTTP_404_NOT_FOUND" in DEPS_SRC or "status_code=404" in DEPS_SRC, (
            "get_or_404 应抛 404"
        )
        assert "deleted_at" in DEPS_SRC, "get_or_404 应自动过滤软删除"

    def test_active_query_defined_in_deps(self):
        """active_query 在 deps.py 中定义"""
        assert "def active_query(" in DEPS_SRC, "应定义 active_query 函数"
        assert "deleted_at" in DEPS_SRC, "active_query 应自动过滤软删除"

    def test_read_endpoints_use_get_or_404(self):
        """读取详情端点使用 get_or_404"""
        for name in ["products", "customers", "orders"]:
            src = SOURCES[name]
            # GET detail 端点应使用 get_or_404
            assert "get_or_404" in src, f"{name} 应使用 get_or_404 获取实体"

    def test_concurrent_resources_use_with_for_update(self):
        """并发敏感资源使用 with_for_update 行锁"""
        for name in ["orders", "payments", "inventory"]:
            src = SOURCES[name]
            assert "with_for_update()" in src, (
                f"{name} 操作并发敏感资源应使用 with_for_update()"
            )

    def test_parse_uuid_defined_in_deps(self):
        """parse_uuid_or_400 在 deps.py 中定义"""
        assert "def parse_uuid_or_400(" in DEPS_SRC, "应定义 parse_uuid_or_400"
        assert "uuid.UUID" in DEPS_SRC, "应转换为 uuid.UUID"
        assert "400" in DEPS_SRC, "无效 UUID 应抛 400"


# ═══════════════════════════════════════════════════════════
# 3. 写入端点事务一致性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestWriteEndpointConsistency:
    """写入端点遵循一致的事务模式"""

    def test_create_endpoints_use_flush_then_safe_commit(self):
        """创建端点使用 flush + safe_commit 模式"""
        for name in ["products", "customers", "orders"]:
            src = SOURCES[name]
            if "db.add(" in src:
                # 创建操作应先 add，可能 flush 获取 ID，最后 safe_commit
                assert "safe_commit(db)" in src, (
                    f"{name} 创建端点应使用 safe_commit"
                )

    def test_audit_log_created_alongside_mutations(self):
        """数据变更同时创建审计日志"""
        for name in ["products", "customers", "orders", "payments"]:
            src = SOURCES[name]
            if _has_write_endpoints(src):
                assert "AuditLog" in src or "audit" in src.lower(), (
                    f"{name} 写入端点应创建审计日志"
                )

    def test_delete_endpoints_use_soft_delete(self):
        """删除端点使用软删除（设置 deleted_at）"""
        for name in ["products", "customers"]:
            src = SOURCES[name]
            if "def delete_" in src or "def remove_" in src:
                assert "deleted_at" in src, (
                    f"{name} 删除应使用软删除（设置 deleted_at）"
                )

    def test_products_has_multiple_safe_commit_calls(self):
        """products 模块有多个 safe_commit 调用（create/update/delete/disable/import）"""
        count = _count_safe_commit(SOURCES["products"])
        assert count >= 4, (
            f"products 模块应有 >= 4 个 safe_commit 调用，实际 {count}"
        )

    def test_orders_has_multiple_safe_commit_calls(self):
        """orders 模块有多个 safe_commit 调用（create/update/confirm/cancel/payment）"""
        count = _count_safe_commit(SOURCES["orders"])
        assert count >= 4, (
            f"orders 模块应有 >= 4 个 safe_commit 调用，实际 {count}"
        )


# ═══════════════════════════════════════════════════════════
# 4. 库存敏感操作验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestInventorySensitiveOperations:
    """库存相关操作有正确的锁定和记录"""

    def test_order_confirm_locks_products(self):
        """订单确认锁定产品行（with_for_update）"""
        orders_src = SOURCES["orders"]
        # confirm 函数中应有 with_for_update
        confirm_fn = orders_src[orders_src.find("def confirm_order"):]
        confirm_fn = confirm_fn[:confirm_fn.find("\ndef ", 1) if "\ndef " in confirm_fn[1:] else len(confirm_fn)]
        assert "with_for_update()" in confirm_fn, (
            "confirm_order 应使用 with_for_update() 锁定产品行"
        )

    def test_order_cancel_restores_inventory(self):
        """订单取消恢复库存"""
        orders_src = SOURCES["orders"]
        assert "_restore_inventory" in orders_src or "restore" in orders_src.lower(), (
            "orders 应有库存恢复逻辑"
        )
        assert "InventoryMovement" in orders_src, (
            "库存变动应创建 InventoryMovement 记录"
        )

    def test_inventory_adjustment_validates_stock(self):
        """库存调整验证不会产生负库存"""
        inventory_src = SOURCES["inventory"]
        assert "stock_quantity" in inventory_src, "应引用 stock_quantity 字段"
        # 应有负数检查
        assert "negative" in inventory_src.lower() or "< 0" in inventory_src or "< 0" in inventory_src, (
            "库存调整应验证不会产生负库存"
        )

    def test_payment_reverse_updates_order_paid_amount(self):
        """收款冲正更新订单已付金额"""
        payments_src = SOURCES["payments"]
        assert "paid_amount" in payments_src, (
            "收款冲正应更新 order.paid_amount"
        )
        assert "with_for_update()" in payments_src, (
            "收款冲正应锁定订单行"
        )

    def test_inventory_movements_created_for_stock_changes(self):
        """库存变动时创建 InventoryMovement 记录"""
        for name in ["products", "orders", "inventory"]:
            src = SOURCES[name]
            if "stock_quantity" in src or "InventoryMovement" in src:
                assert "InventoryMovement" in src, (
                    f"{name} 库存变动应创建 InventoryMovement 记录"
                )


# ═══════════════════════════════════════════════════════════
# 5. 服务层共享模式验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestServiceLayerPatterns:
    """共享服务层遵循正确的事务委托模式"""

    def test_payment_service_exists(self):
        """payment_service.py 存在且定义 register_payment"""
        assert "def register_payment" in PAYMENT_SERVICE_SRC, (
            "payment_service 应定义 register_payment 函数"
        )

    def test_payment_service_does_not_commit(self):
        """register_payment 不自行提交（由调用方提交）"""
        assert "safe_commit" not in PAYMENT_SERVICE_SRC or "db.commit()" not in PAYMENT_SERVICE_SRC, (
            "register_payment 不应自行提交事务，应由调用方提交"
        )

    def test_payment_service_uses_lock(self):
        """payment_service 使用线程锁防止并发"""
        assert "Lock" in PAYMENT_SERVICE_SRC or "threading" in PAYMENT_SERVICE_SRC, (
            "payment_service 应使用线程锁防止并发提交"
        )
        assert "with_for_update()" in PAYMENT_SERVICE_SRC, (
            "register_payment 应锁定订单行"
        )

    def test_resp_helper_builds_standard_response(self):
        """resp 辅助函数构建标准响应格式"""
        assert "def resp(" in DEPS_SRC, "应定义 resp 辅助函数"
        assert '"success"' in DEPS_SRC, "响应应包含 success 字段"
        assert '"data"' in DEPS_SRC, "响应应包含 data 字段"
        assert '"message"' in DEPS_SRC, "响应应包含 message 字段"
        assert "request_id" in DEPS_SRC, "响应应包含 request_id"

    def test_paginated_resp_helper_builds_pagination(self):
        """paginated_resp 辅助函数构建分页响应"""
        assert "def paginated_resp(" in DEPS_SRC, "应定义 paginated_resp"
        assert '"items"' in DEPS_SRC, "分页响应应包含 items"
        assert '"total"' in DEPS_SRC, "分页响应应包含 total"
        assert '"page"' in DEPS_SRC, "分页响应应包含 page"
        assert '"page_size"' in DEPS_SRC, "分页响应应包含 page_size"
