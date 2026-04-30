"""商品详情和软删除成功路径测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import Product, ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_product_crud.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None
_tokens: dict = {}
_product_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _product_id
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        admin = User(
            id=uuid.uuid4(),
            username="prod_admin",
            hashed_password=hash_password("testpass123"),
            display_name="商品管理员",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)

        cat = ProductCategory(id=uuid.uuid4(), name="电子产品", sort_order=0)
        db.add(cat)

        product = Product(
            id=uuid.uuid4(),
            sku="SPU-CRUD-001",
            name="CRUD测试商品",
            sale_price=199.00,
            cost_price=99.00,
            stock_quantity=50,
            category_id=cat.id,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(product)
        _product_id = str(product.id)

        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_product_crud.db"):
        os.remove("./test_product_crud.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {_tokens.get('access', '')}"}


def test_01_login():
    resp = client.post("/api/v1/auth/login", json={
        "username": "prod_admin", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_get_product_detail():
    """获取商品详情"""
    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "CRUD测试商品"
    assert data["sku"] == "SPU-CRUD-001"
    assert data["sale_price"] == "199.00"
    assert data["cost_price"] == "99.00"
    assert data["stock_quantity"] == 50
    assert data["status"] == "active"


def test_03_get_product_not_found():
    """获取不存在的商品"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/products/{fake_id}", headers=_auth())
    assert resp.status_code == 404


def test_03b_update_product_all_fields():
    """编辑商品多个字段"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "cost_price": "80.00",
        "main_image_url": "https://example.com/img.png",
        "stock_quantity": 200,
        "sort_weight": 10,
        "remark": "更新备注",
    }, headers=_auth())
    assert resp.status_code == 200

    # 验证更新
    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    data = resp.json()["data"]
    assert data["cost_price"] == "80.00"
    assert data["main_image_url"] == "https://example.com/img.png"
    assert data["stock_quantity"] == 200
    assert data["remark"] == "更新备注"


def test_03c_update_product_sku_duplicate():
    """编辑商品 SKU 重复"""
    # 创建第二个商品
    resp = client.post("/api/v1/products", json={
        "name": "SKU测试商品", "sale_price": "50", "cost_price": "25", "stock_quantity": 1,
        "sku": "SPU-DUP-001",
    }, headers=_auth())
    assert resp.status_code == 200
    dup_id = resp.json()["data"]["id"]

    # 尝试把第一个商品的 SKU 改成第二个的
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sku": "SPU-DUP-001",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PRODUCT_SKU_DUPLICATED"


def test_03d_update_product_cost_price_negative():
    """编辑商品成本价为负"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "cost_price": "-10.00",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "成本价不能为负" in resp.json()["detail"]["message"]


def test_04_delete_product():
    """软删除商品"""
    resp = client.delete(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.status_code == 200
    assert "删除成功" in resp.json()["message"]


def test_05_verify_deleted():
    """验证删除后不可见"""
    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.status_code == 404


def test_06_list_excludes_deleted():
    """列表不含已删除商品"""
    resp = client.get("/api/v1/products", headers=_auth())
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()["data"]["items"]]
    assert _product_id not in ids


def test_07_list_with_keyword_filter():
    """关键字筛选"""
    resp = client.get("/api/v1/products", params={"keyword": "不存在的商品"}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


def test_08_list_with_status_filter():
    """状态筛选"""
    resp = client.get("/api/v1/products", params={"status": "active"}, headers=_auth())
    assert resp.status_code == 200
    for item in resp.json()["data"]["items"]:
        assert item["status"] == "active"


def test_09_list_with_sort_asc():
    """升序排序"""
    resp = client.get("/api/v1/products", params={"sort_by": "name", "sort_order": "asc"}, headers=_auth())
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["data"]["items"]]
    assert names == sorted(names)


def test_10_create_empty_name_rejected():
    """创建商品名称为空"""
    resp = client.post("/api/v1/products", json={
        "name": "  ", "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_FAILED"


def test_11_create_bad_price_rejected():
    """创建商品价格格式错误"""
    resp = client.post("/api/v1/products", json={
        "name": "测试", "sale_price": "abc", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "VALIDATION_FAILED"
