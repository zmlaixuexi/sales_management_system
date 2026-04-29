"""后端验证和异常路径补充测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.customer import Customer
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_validation.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""
_customer_id: str = ""


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
            username="val_tester",
            hashed_password=hash_password("testpass123"),
            display_name="验证测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        product = Product(
            id=uuid.uuid4(), sku="SPU-VAL-001", name="验证商品",
            sale_price=200, cost_price=100, stock_quantity=10,
            category_id=cat.id, status="active",
            created_by=user.id, updated_by=user.id,
        )
        db.add(product)
        global _product_id
        _product_id = str(product.id)
        customer = Customer(
            id=uuid.uuid4(), name="验证客户", phone="13900001111",
            owner_user_id=user.id, created_by=user.id, updated_by=user.id,
        )
        db.add(customer)
        global _customer_id
        _customer_id = str(customer.id)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_validation.db"):
        os.remove("./test_validation.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    """登录获取 Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "val_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


# ─── 认证补充 ─────────────────────────────────────────────

def test_02_refresh_invalid_token():
    """使用无效 refresh_token"""
    resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401


def test_03_refresh_missing_token():
    """refresh 请求缺少 token（FastAPI 参数校验返回 422）"""
    resp = client.post("/api/v1/auth/refresh", json={})
    assert resp.status_code == 422


# ─── 商品补充 ─────────────────────────────────────────────

def test_04_product_update_negative_price():
    """编辑商品价格为负"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sale_price": "-50",
    }, headers=_auth())
    assert resp.status_code == 400


def test_05_product_update_empty_name():
    """编辑商品名称为空"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "name": "   ",
    }, headers=_auth())
    assert resp.status_code == 400


def test_06_product_update_duplicate_sku():
    """编辑商品 SKU 与其他商品重复"""
    # 先创建第二个商品
    resp = client.post("/api/v1/products", json={
        "name": "第二个商品", "sale_price": "50", "cost_price": "25",
    }, headers=_auth())
    assert resp.status_code == 200
    existing_sku = resp.json()["data"]["sku"]

    # 尝试将第一个商品的 SKU 改成第二个商品的
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sku": existing_sku,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PRODUCT_SKU_DUPLICATED"


def test_07_product_update_invalid_price():
    """编辑商品价格格式错误"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sale_price": "abc",
    }, headers=_auth())
    assert resp.status_code == 400


def test_08_product_disable_not_found():
    """停用不存在的商品"""
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/products/{fake_id}/disable", headers=_auth())
    assert resp.status_code == 404


def test_09_product_price_history():
    """查看价格变更记录"""
    resp = client.get(f"/api/v1/products/{_product_id}/price-history", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "items" in data["data"]


def test_10_product_update_stock_negative():
    """编辑商品库存为负"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "stock_quantity": -5,
    }, headers=_auth())
    assert resp.status_code == 400


# ─── 客户补充 ─────────────────────────────────────────────

def test_11_customer_update_not_found():
    """编辑不存在的客户"""
    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/customers/{fake_id}", json={
        "name": "新名称",
    }, headers=_auth())
    assert resp.status_code == 404


def test_12_customer_delete_not_found():
    """删除不存在的客户"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/customers/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_13_customer_transfer_not_found():
    """转移不存在的客户"""
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/customers/{fake_id}/transfer", json={
        "owner_user_id": str(uuid.uuid4()),
    }, headers=_auth())
    assert resp.status_code == 404


def test_14_customer_create_no_name():
    """创建客户名称为空白"""
    resp = client.post("/api/v1/customers", json={
        "name": "",
    }, headers=_auth())
    assert resp.status_code == 400


# ─── CSV 导入补充 ─────────────────────────────────────────

def test_15_product_import_empty_csv():
    """导入空 CSV（只有表头）"""
    csv_content = "商品名称,销售价,成本价,库存数量"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_16_product_import_no_headers():
    """导入无表头 CSV"""
    csv_content = "测试商品,100,50,10"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    # 无匹配表头时所有行跳过
    assert resp.json()["data"]["created"] == 0


def test_17_customer_import_empty_csv():
    """导入空客户 CSV（只有表头）"""
    csv_content = "客户名称,电话,联系人"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_18_product_import_invalid_price():
    """导入 CSV 中销售价格式错误"""
    csv_content = "商品名称,销售价\n格式错误商品,abc"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


def test_19_product_import_negative_price():
    """导入 CSV 中价格为负"""
    csv_content = "商品名称,销售价\n负价商品,-100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


# ─── 用户管理 ─────────────────────────────────────────────

def test_20_users_list():
    """管理员可以获取用户列表"""
    resp = client.get("/api/v1/users", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1
