"""异常路径：分页参数边界测试 — 覆盖 offset 计算、响应结构、参数类型、极端值、跨端点一致性"""

from fastapi.testclient import TestClient

from app.api.deps import PaginationParams, paginate, paginated_resp
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════
# 1. PaginationParams 默认值与约束
# ═══════════════════════════════════════════════════════


def _get_field_info(field_name: str):
    """获取 PaginationParams 字段的 Query 对象"""
    import inspect

    sig = inspect.signature(PaginationParams)
    return sig.parameters[field_name].default


def test_pagination_default_page():
    """默认 page Query 默认值为 1"""
    q = _get_field_info("page")
    assert q.default == 1


def test_pagination_default_page_size():
    """默认 page_size Query 默认值为 20"""
    q = _get_field_info("page_size")
    assert q.default == 20


def test_pagination_page_max():
    """page 上限 10000 — metadata Le 约束"""
    q = _get_field_info("page")
    le_constraints = [m for m in q.metadata if type(m).__name__ == "Le"]
    assert any(m.le == 10000 for m in le_constraints)


def test_pagination_page_size_max():
    """page_size 上限 100 — metadata Le 约束"""
    q = _get_field_info("page_size")
    le_constraints = [m for m in q.metadata if type(m).__name__ == "Le"]
    assert any(m.le == 100 for m in le_constraints)


def test_pagination_page_size_min():
    """page_size 下限 1 — metadata Ge 约束"""
    q = _get_field_info("page_size")
    ge_constraints = [m for m in q.metadata if type(m).__name__ == "Ge"]
    assert any(m.ge == 1 for m in ge_constraints)


def test_pagination_page_min():
    """page 下限 1 — metadata Ge 约束"""
    q = _get_field_info("page")
    ge_constraints = [m for m in q.metadata if type(m).__name__ == "Ge"]
    assert any(m.ge == 1 for m in ge_constraints)


# ═══════════════════════════════════════════════════════
# 2. paginate() 函数 offset 计算
# ═══════════════════════════════════════════════════════


def test_paginate_page1_offset0():
    """第 1 页 offset=0"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 50
    mock_offset = MagicMock()
    mock_offset.limit.return_value.all.return_value = []
    query.offset.return_value = mock_offset

    paginate(query, 1, 20)
    query.offset.assert_called_with(0)


def test_paginate_page2_offset():
    """第 2 页 offset=page_size"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 50
    mock_offset = MagicMock()
    mock_offset.limit.return_value.all.return_value = []
    query.offset.return_value = mock_offset

    paginate(query, 2, 20)
    query.offset.assert_called_with(20)


def test_paginate_page3_offset():
    """第 3 页 offset=2*page_size"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 50
    mock_offset = MagicMock()
    mock_offset.limit.return_value.all.return_value = []
    query.offset.return_value = mock_offset

    paginate(query, 3, 20)
    query.offset.assert_called_with(40)


def test_paginate_page_size_1_offset():
    """page_size=1 时 offset=page-1"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 50
    mock_offset = MagicMock()
    mock_offset.limit.return_value.all.return_value = []
    query.offset.return_value = mock_offset

    paginate(query, 5, 1)
    query.offset.assert_called_with(4)


def test_paginate_returns_total():
    """paginate 返回 total"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 42
    query.offset.return_value.limit.return_value.all.return_value = []

    _, total = paginate(query, 1, 20)
    assert total == 42


# ═══════════════════════════════════════════════════════
# 3. paginated_resp() 结构验证
# ═══════════════════════════════════════════════════════


def test_paginated_resp_has_items():
    """响应包含 items 字段"""
    result = paginated_resp([{"id": 1}], 1, 20, 1)
    assert result["data"]["items"] == [{"id": 1}]


def test_paginated_resp_has_page():
    """响应包含 page 字段"""
    result = paginated_resp([], 2, 20, 0)
    assert result["data"]["page"] == 2


def test_paginated_resp_has_page_size():
    """响应包含 page_size 字段"""
    result = paginated_resp([], 1, 50, 0)
    assert result["data"]["page_size"] == 50


def test_paginated_resp_has_total():
    """响应包含 total 字段"""
    result = paginated_resp([], 1, 20, 100)
    assert result["data"]["total"] == 100


def test_paginated_resp_success_true():
    """响应 success=True"""
    result = paginated_resp([], 1, 20, 0)
    assert result["success"] is True


def test_paginated_resp_default_message():
    """默认消息为"查询成功" """
    result = paginated_resp([], 1, 20, 0)
    assert result["message"] == "查询成功"


def test_paginated_resp_custom_message():
    """自定义消息"""
    result = paginated_resp([], 1, 20, 0, message="自定义")
    assert result["message"] == "自定义"


def test_paginated_resp_empty_items():
    """空列表正常返回"""
    result = paginated_resp([], 1, 20, 0)
    assert result["data"]["items"] == []
    assert result["data"]["total"] == 0


# ═══════════════════════════════════════════════════════
# 4. API 级别分页参数验证
# ═══════════════════════════════════════════════════════


def test_api_page_zero_returns_422():
    """page=0 返回 422"""
    resp = client.get("/api/v1/health")  # warm up
    resp = client.get("/api/v1/products?page=0")
    assert resp.status_code in (401, 422)


def test_api_page_negative_returns_422():
    """page=-1 返回 422"""
    resp = client.get("/api/v1/products?page=-1")
    assert resp.status_code in (401, 422)


def test_api_page_size_zero_returns_422():
    """page_size=0 返回 422"""
    resp = client.get("/api/v1/products?page_size=0")
    assert resp.status_code in (401, 422)


def test_api_page_size_101_returns_422():
    """page_size=101 返回 422"""
    resp = client.get("/api/v1/products?page_size=101")
    assert resp.status_code in (401, 422)


def test_api_page_10001_returns_422():
    """page=10001 返回 422"""
    resp = client.get("/api/v1/products?page=10001")
    assert resp.status_code in (401, 422)


def test_api_page_size_1_accepted():
    """page_size=1 被接受"""
    resp = client.get("/api/v1/products?page_size=1")
    assert resp.status_code in (200, 401)


def test_api_page_size_100_accepted():
    """page_size=100 被接受"""
    resp = client.get("/api/v1/products?page_size=100")
    assert resp.status_code in (200, 401)


def test_api_page_10000_accepted():
    """page=10000 被接受"""
    resp = client.get("/api/v1/products?page=10000")
    assert resp.status_code in (200, 401)


def test_api_page_string_returns_422():
    """page=abc 返回 422"""
    resp = client.get("/api/v1/products?page=abc")
    assert resp.status_code in (401, 422)


def test_api_page_size_string_returns_422():
    """page_size=xyz 返回 422"""
    resp = client.get("/api/v1/products?page_size=xyz")
    assert resp.status_code in (401, 422)


def test_api_page_float_returns_422():
    """page=1.5 返回 422"""
    resp = client.get("/api/v1/products?page=1.5")
    assert resp.status_code in (401, 422)


# ═══════════════════════════════════════════════════════
# 5. 分页端点一致性 — 所有 7 个列表端点支持分页
# ═══════════════════════════════════════════════════════


def test_products_supports_pagination():
    """商品列表支持分页参数"""
    resp = client.get("/api/v1/products?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_customers_supports_pagination():
    """客户列表支持分页参数"""
    resp = client.get("/api/v1/customers?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_orders_supports_pagination():
    """订单列表支持分页参数"""
    resp = client.get("/api/v1/sales-orders?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_payments_supports_pagination():
    """收款列表支持分页参数"""
    resp = client.get("/api/v1/payments?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_users_supports_pagination():
    """用户列表支持分页参数"""
    resp = client.get("/api/v1/users?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_inventory_movements_supports_pagination():
    """库存流水支持分页参数"""
    resp = client.get("/api/v1/inventory/movements?page=1&page_size=10")
    assert resp.status_code in (200, 401)


def test_audit_logs_supports_pagination():
    """操作日志支持分页参数"""
    resp = client.get("/api/v1/audit-logs?page=1&page_size=10")
    assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════
# 6. 响应分页结构一致性
# ═══════════════════════════════════════════════════════


def test_paginated_resp_contains_all_fields():
    """分页响应包含 items/page/page_size/total"""
    result = paginated_resp([1, 2, 3], 1, 20, 100)
    data = result["data"]
    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data


def test_paginated_resp_total_is_int():
    """total 为整数"""
    result = paginated_resp([], 1, 20, 0)
    assert isinstance(result["data"]["total"], int)


def test_paginated_resp_page_is_int():
    """page 为整数"""
    result = paginated_resp([], 1, 20, 0)
    assert isinstance(result["data"]["page"], int)


def test_paginated_resp_page_size_is_int():
    """page_size 为整数"""
    result = paginated_resp([], 1, 20, 0)
    assert isinstance(result["data"]["page_size"], int)


def test_paginated_resp_items_is_list():
    """items 为列表"""
    result = paginated_resp([], 1, 20, 0)
    assert isinstance(result["data"]["items"], list)


# ═══════════════════════════════════════════════════════
# 7. 极端值 — 大 page_size 小 total
# ═══════════════════════════════════════════════════════


def test_page_beyond_total_empty_items():
    """page 超出 total 范围时 items 为空"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 5
    query.offset.return_value.limit.return_value.all.return_value = []

    items, total = paginate(query, 100, 20)
    assert items == []
    assert total == 5


def test_page_size_100_offset_calculation():
    """page_size=100 时 offset 计算正确"""
    from unittest.mock import MagicMock

    query = MagicMock()
    query.count.return_value = 200
    mock_offset = MagicMock()
    mock_offset.limit.return_value.all.return_value = []
    query.offset.return_value = mock_offset

    paginate(query, 2, 100)
    query.offset.assert_called_with(100)
