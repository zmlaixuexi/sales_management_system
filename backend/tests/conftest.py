"""pytest 配置：确保速率限制测试最后运行 + 自动标记分类"""

import pytest


_prev_module = None


@pytest.fixture(autouse=True)
def _fast_health_database_probe(monkeypatch):
    """测试环境默认跳过真实 PostgreSQL 探测，避免无数据库时健康检查阻塞。"""
    from unittest.mock import MagicMock

    from app.api.v1 import health as health_mod

    mock_session = MagicMock()
    mock_session.execute.return_value = None
    mock_session.close.return_value = None
    monkeypatch.setattr(health_mod, "SessionLocal", lambda: mock_session)


def pytest_runtest_setup(item):
    """每个测试前清空收款防抖状态；模块切换时清空全局速率限制计数器"""
    # 每个测试前重置收款防抖（同一模块内连续测试可能操作同一订单）
    from app.services.payment_service import reset_payment_debounce
    reset_payment_debounce()

    if "test_ratelimit" in item.nodeid:
        return
    global _prev_module
    mod = item.module
    if mod is not _prev_module:
        _prev_module = mod
        from app.core.ratelimit import clear_rate_limit
        clear_rate_limit()
        # 清空登录失败计数器，防止跨模块累积触发 429
        from app.api.v1.auth import _login_fail_counts
        _login_fail_counts.clear()



def pytest_collection_modifyitems(items):
    """将 test_ratelimit.py 的测试移到末尾，并根据文件名自动添加标记"""
    ratelimit = []
    others = []
    for item in items:
        if "test_ratelimit" in item.nodeid:
            ratelimit.append(item)
        else:
            others.append(item)
    items[:] = others + ratelimit

    # 根据文件名自动添加标记
    file_markers = {
        "test_product_crud": "crud",
        "test_customer_crud": "crud",
        "test_order_crud": "crud",
        "test_payment_crud": "crud",
        "test_inventory_crud": "crud",
        "test_user_management": "crud",
        "test_edge_cases": "boundary",
        "test_boundary": "boundary",
        "test_validation": "boundary",
        "test_auth": "security",
        "test_permissions": "security",
        "test_ratelimit": "security",
        "test_sanitize": "security",
        "test_export": "export",
        "test_product_import": "import",
        "test_customer_import": "import",
        "test_reports_audit": "report",
        "test_audit_log": "report",
        "test_integration": "integration",
        "test_health": "infra",
        "test_deps": "security",
        "test_file_upload": "integration",
        "test_order_calc": "crud",
        "test_audit_service": "report",
        "test_product_calc": "crud",
        "test_logging": "infra",
        "test_export_helpers": "export",
        "test_csv_import": "import",
        "test_file_service": "security",
        "test_auth_rate_limit": "security",
        "test_product_helpers": "crud",
        "test_customer_helpers": "crud",
        "test_order_inventory": "crud",
        "test_order_validate_items": "crud",
        "test_payment_register": "crud",
        "test_body_limit": "security",
    }
    for item in items:
        for pattern, marker in file_markers.items():
            if pattern in item.nodeid:
                item.add_marker(marker)
