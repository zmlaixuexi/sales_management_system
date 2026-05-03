"""API 分页格式一致性测试 — 验证所有分页端点返回统一结构"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import PaginationParams, get_db, paginate, paginated_resp
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_pagination.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="page_test_admin",
            hashed_password=hash_password("TestPass123!"),
            display_name="分页测试",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os

    if os.path.exists("./test_pagination.db"):
        os.remove("./test_pagination.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def _assert_paginated_structure(body: dict):
    """验证分页响应的标准结构"""
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "page" in data
    assert isinstance(data["page"], int)
    assert "page_size" in data
    assert isinstance(data["page_size"], int)
    assert "total" in data
    assert isinstance(data["total"], int)


# ═══════════════════════════════════════════════════════
# 0. 登录
# ═══════════════════════════════════════════════════════


def test_01_login():
    resp = client.post("/api/v1/auth/login", json={
        "username": "page_test_admin",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200
    body = resp.json()
    _tokens["access"] = body["data"]["access_token"]


# ═══════════════════════════════════════════════════════
# 1. 分页参数默认值
# ═══════════════════════════════════════════════════════


def test_02_default_pagination_params():
    """默认 page=1, page_size=20"""
    resp = client.get("/api/v1/customers", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    _assert_paginated_structure(body)
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 20


def test_03_custom_page_and_page_size():
    """自定义 page 和 page_size"""
    resp = client.get("/api/v1/customers?page=2&page_size=5", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    _assert_paginated_structure(body)
    assert body["data"]["page"] == 2
    assert body["data"]["page_size"] == 5


# ═══════════════════════════════════════════════════════
# 2. 分页参数边界校验
# ═══════════════════════════════════════════════════════


def test_04_page_zero_rejected():
    """page=0 被 422 拒绝"""
    resp = client.get("/api/v1/customers?page=0", headers=_auth())
    assert resp.status_code == 422


def test_05_page_negative_rejected():
    """page=-1 被 422 拒绝"""
    resp = client.get("/api/v1/customers?page=-1", headers=_auth())
    assert resp.status_code == 422


def test_06_page_size_zero_rejected():
    """page_size=0 被 422 拒绝"""
    resp = client.get("/api/v1/customers?page_size=0", headers=_auth())
    assert resp.status_code == 422


def test_07_page_size_over_100_rejected():
    """page_size=101 被 422 拒绝"""
    resp = client.get("/api/v1/customers?page_size=101", headers=_auth())
    assert resp.status_code == 422


def test_08_page_size_100_accepted():
    """page_size=100 是允许的最大值"""
    resp = client.get("/api/v1/customers?page_size=100", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["page_size"] == 100


def test_09_page_size_1_accepted():
    """page_size=1 是允许的最小值"""
    resp = client.get("/api/v1/customers?page_size=1", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["page_size"] == 1


def test_10_page_exceeds_total_returns_empty():
    """page 超出范围时返回空 items"""
    resp = client.get("/api/v1/customers?page=9999", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    _assert_paginated_structure(body)
    assert body["data"]["items"] == []
    assert body["data"]["total"] >= 0


# ═══════════════════════════════════════════════════════
# 3. 各分页端点结构一致性
# ═══════════════════════════════════════════════════════


def test_11_customers_paginated_structure():
    """客户列表返回分页结构"""
    resp = client.get("/api/v1/customers", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_12_products_paginated_structure():
    """商品列表返回分页结构"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_13_orders_paginated_structure():
    """订单列表返回分页结构"""
    resp = client.get("/api/v1/sales-orders", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_14_payments_paginated_structure():
    """收款列表返回分页结构"""
    resp = client.get("/api/v1/payments", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_15_users_paginated_structure():
    """用户列表返回分页结构"""
    resp = client.get("/api/v1/users", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_16_audit_logs_paginated_structure():
    """审计日志列表返回分页结构"""
    resp = client.get("/api/v1/audit-logs", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


def test_17_inventory_movements_paginated_structure():
    """库存流水列表返回分页结构"""
    resp = client.get("/api/v1/inventory/movements", headers=_auth())
    assert resp.status_code == 200
    _assert_paginated_structure(resp.json())


# ═══════════════════════════════════════════════════════
# 4. 单元测试：paginate / paginated_resp 函数
# ═══════════════════════════════════════════════════════


def test_paginate_function_returns_tuple():
    """paginate 返回 (items, total) 元组"""
    from sqlalchemy import Column, Integer, MetaData, Table, create_engine
    from sqlalchemy.orm import Session

    mem_engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    test_table = Table("test_items", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(mem_engine)

    with Session(mem_engine) as session:
        for i in range(25):
            session.execute(test_table.insert().values(id=i + 1))
        session.commit()

        query = session.query(test_table)
        items, total = paginate(query, 1, 10)
        assert total == 25
        assert len(items) == 10

        items_p2, total_p2 = paginate(query, 2, 10)
        assert total_p2 == 25
        assert len(items_p2) == 10

        items_p3, total_p3 = paginate(query, 3, 10)
        assert total_p3 == 25
        assert len(items_p3) == 5


def test_paginate_empty_query():
    """空查询返回空列表和 total=0"""
    from sqlalchemy import Column, Integer, MetaData, Table, create_engine
    from sqlalchemy.orm import Session

    mem_engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    test_table = Table("test_empty", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(mem_engine)

    with Session(mem_engine) as session:
        query = session.query(test_table)
        items, total = paginate(query, 1, 10)
        assert items == []
        assert total == 0


def test_paginated_resp_structure():
    """paginated_resp 返回标准结构"""
    result = paginated_resp(items=[{"id": 1}], page=1, page_size=20, total=1)
    assert result["success"] is True
    assert result["data"]["items"] == [{"id": 1}]
    assert result["data"]["page"] == 1
    assert result["data"]["page_size"] == 20
    assert result["data"]["total"] == 1
    assert result["message"] == "查询成功"


def test_paginated_resp_custom_message():
    """paginated_resp 支持自定义 message"""
    result = paginated_resp(items=[], page=1, page_size=10, total=0, message="自定义")
    assert result["message"] == "自定义"


def test_pagination_params_defaults():
    """PaginationParams 默认值 page=1, page_size=20"""
    params = PaginationParams(page=1, page_size=20)
    assert params.page == 1
    assert params.page_size == 20


def test_pagination_params_custom():
    """PaginationParams 接受自定义值"""
    params = PaginationParams(page=3, page_size=50)
    assert params.page == 3
    assert params.page_size == 50


# ═══════════════════════════════════════════════════════
# 5. 跨端点一致性：total 与 items 长度关系
# ═══════════════════════════════════════════════════════


def test_total_consistent_with_items_length():
    """total >= len(items) 且 items 长度 <= page_size"""
    resp = client.get("/api/v1/customers?page=1&page_size=5", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["total"] >= len(data["items"])
    assert len(data["items"]) <= data["page_size"]


def test_total_across_pages_is_stable():
    """不同 page 的 total 值相同"""
    resp1 = client.get("/api/v1/customers?page=1&page_size=5", headers=_auth())
    resp2 = client.get("/api/v1/customers?page=2&page_size=5", headers=_auth())
    assert resp1.json()["data"]["total"] == resp2.json()["data"]["total"]
