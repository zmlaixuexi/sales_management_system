"""pytest 配置：确保速率限制测试最后运行 + 自动标记分类"""



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
    }
    for item in items:
        for pattern, marker in file_markers.items():
            if pattern in item.nodeid:
                item.add_marker(marker)
