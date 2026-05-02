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
_category_id: str = ""


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module(module):
    global _original_override, _product_id, _category_id
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
        _category_id = str(cat.id)

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

    # 尝试把第一个商品的 SKU 改成第二个的
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sku": "SPU-DUP-001",
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PRODUCT_SKU_DUPLICATED"


def test_03c2_update_product_sku_success():
    """编辑商品 SKU 更新成功"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "sku": "SPU-NEW-001",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.json()["data"]["sku"] == "SPU-NEW-001"


def test_03d_update_product_cost_price_negative():
    """编辑商品成本价为负"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "cost_price": "-10.00",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "成本价不能为负" in resp.json()["error"]["message"]


def test_03e_list_with_category_filter():
    """按分类筛选商品"""
    resp = client.get("/api/v1/products", params={"category_id": _category_id}, headers=_auth())
    assert resp.status_code == 200
    for item in resp.json()["data"]["items"]:
        assert item["category_id"] == _category_id


def test_03f_list_with_invalid_sort_fallback():
    """无效排序字段回退"""
    resp = client.get("/api/v1/products", params={"sort_by": "nonexistent"}, headers=_auth())
    assert resp.status_code == 200


def test_03g_update_product_cost_price_format_error():
    """编辑商品成本价格式错误"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "cost_price": "abc",
    }, headers=_auth())
    assert resp.status_code == 400
    assert "成本价格式错误" in resp.json()["error"]["message"]


def test_03h_update_product_category():
    """编辑商品分类"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "category_id": _category_id,
    }, headers=_auth())
    assert resp.status_code == 200


def test_03i_update_product_name():
    """编辑商品名称"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "name": "新名称商品",
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.json()["data"]["name"] == "新名称商品"


def test_03e_price_history_with_cost():
    """价格变更记录（超管可见成本价）"""
    # test_03b 已将 cost_price 从 99→80，存在一条记录
    resp = client.get(f"/api/v1/products/{_product_id}/price-history", headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    first = items[0]
    assert "old_sale_price" in first
    assert "new_sale_price" in first
    # 超管有 view_cost 权限，应包含成本价字段
    assert "old_cost_price" in first
    assert "new_cost_price" in first
    assert first["old_cost_price"] == "99.00"
    assert first["new_cost_price"] == "80.00"


def test_03c_delete_product_with_order_ref():
    """删除被订单引用的商品返回 409"""
    from app.models.customer import Customer
    from app.models.order import SalesOrder, SalesOrderItem

    db = TestSession()
    try:
        admin = db.query(User).filter(User.username == "prod_admin").first()
        product = db.query(Product).filter(Product.id == uuid.UUID(_product_id)).first()
        # 创建客户
        customer = Customer(
            id=uuid.uuid4(),
            name="引用测试客户",
            phone="13900001111",
            owner_user_id=admin.id,
            created_by=admin.id,
        )
        db.add(customer)
        db.flush()
        # 创建订单引用该商品
        order = SalesOrder(
            id=uuid.uuid4(),
            order_no="SO-REF-001",
            customer_id=customer.id,
            sales_user_id=admin.id,
            status="confirmed",
            total_amount="199.00",
            created_by=admin.id,
        )
        db.add(order)
        db.flush()
        item = SalesOrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            product_sku_snapshot=product.sku,
            quantity=1,
            unit_price="199.00",
            subtotal_amount="199.00",
            subtotal_cost="80.00",
            cost_price_snapshot="80.00",
        )
        db.add(item)
        db.commit()
    finally:
        db.close()

    resp = client.delete(f"/api/v1/products/{_product_id}", headers=_auth())
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PRODUCT_IN_USE"


def test_04_delete_product():
    """软删除商品（清除订单引用后）"""
    from app.models.order import SalesOrderItem

    db = TestSession()
    try:
        db.query(SalesOrderItem).filter(
            SalesOrderItem.product_id == uuid.UUID(_product_id)
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

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


def test_10_create_with_category():
    """创建商品指定分类"""
    resp = client.post("/api/v1/products", json={
        "name": "分类商品", "sale_price": "50", "cost_price": "25",
        "stock_quantity": 10, "category_id": _category_id,
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["category_id"] == _category_id


def test_10a_sku_generation_with_nonnumeric_suffix():
    """SKU 生成：已有非数字后缀时回退到 1"""
    from datetime import datetime

    from app.models.product import Product as ProdModel
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"SPU-{today}-"
    # 找到已有的自动生成 SKU 的商品，修改为非数字后缀
    db = TestSession()
    prod = db.query(ProdModel).filter(ProdModel.sku.like(f"{prefix}%")).first()
    if prod:
        prod.sku = f"{prefix}ABCD"
        db.commit()
    db.close()

    # 创建商品不带 SKU，触发自动生成
    resp = client.post("/api/v1/products", json={
        "name": "SKU回退测试", "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["data"]["sku"] == f"{prefix}0001"


def test_10b_create_empty_name_rejected():
    """创建商品名称为空"""
    resp = client.post("/api/v1/products", json={
        "name": "  ", "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_11_create_bad_price_rejected():
    """创建商品价格格式错误"""
    resp = client.post("/api/v1/products", json={
        "name": "测试", "sale_price": "abc", "cost_price": "5", "stock_quantity": 1,
    }, headers=_auth())
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_12_csv_import_success():
    """CSV 导入商品成功"""
    import io
    csv_content = (
        "商品名称,SKU,销售价,成本价,库存数量\n"
        "导入商品A,SPU-IMP-001,99.00,50.00,10\n"
        "导入商品B,SPU-IMP-002,199.00,80.00,5"
    )
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert data["errors"] == []


def test_12b_csv_import_encoding_error():
    """CSV 导入编码错误"""
    import io
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(b"\xff\xfe\x00\x00bad"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "编码" in resp.json()["error"]["message"]


def test_12c_csv_import_empty_header():
    """CSV 导入空文件"""
    import io
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(b""), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "表头" in resp.json()["error"]["message"]


def test_12d_csv_import_row_errors():
    """CSV 导入行级错误（空名称/价格格式/成本价格式/库存格式）"""
    import io
    csv_content = (
        "商品名称,SKU,销售价,成本价,库存数量\n"
        ",SPU-ERR-01,99,50,10\n"
        "测试商品,SPU-ERR-02,abc,50,10\n"
        "测试商品B,SPU-ERR-03,99,xyz,10\n"
        "测试商品C,SPU-ERR-04,99,50,abc"
    )
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 1
    assert len(data["errors"]) == 3


def test_12e_csv_import_sku_duplicate_existing():
    """CSV 导入 SKU 与已有商品重复"""
    import io
    csv_content = "商品名称,SKU,销售价,成本价,库存数量\n重复SKU商品,SPU-DUP-001,99,50,10"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 0
    assert len(data["errors"]) == 1
    assert "SKU" in data["errors"][0]["message"]


def test_12f_csv_import_sku_duplicate_within_file():
    """CSV 导入文件内 SKU 重复"""
    import io
    csv_content = "商品名称,SKU,销售价,成本价,库存数量\n商品X,SPU-INFILE-DUP,99,50,10\n商品Y,SPU-INFILE-DUP,199,80,5"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 1
    assert len(data["errors"]) == 1
    assert "SKU" in data["errors"][0]["message"]


def test_13_csv_import_not_csv():
    """CSV 导入非 CSV 文件"""
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("data.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "CSV" in resp.json()["error"]["message"]


def test_14_get_product_requires_auth():
    """未认证获取商品详情返回 401"""
    resp = client.get(f"/api/v1/products/{_product_id}")
    assert resp.status_code == 401


def test_15_update_product_requires_auth():
    """未认证编辑商品返回 401"""
    resp = client.put(f"/api/v1/products/{_product_id}", json={
        "name": "未认证修改",
    })
    assert resp.status_code == 401


def test_16_delete_product_requires_auth():
    """未认证删除商品返回 401"""
    resp = client.delete(f"/api/v1/products/{_product_id}")
    assert resp.status_code == 401


def test_17_get_product_invalid_uuid():
    """无效 UUID 获取商品详情返回 422"""
    resp = client.get("/api/v1/products/not-a-uuid", headers=_auth())
    assert resp.status_code == 422


def test_18_create_product_requires_auth():
    """未认证创建商品返回 401"""
    resp = client.post("/api/v1/products", json={
        "name": "未认证商品", "sale_price": "10", "cost_price": "5", "stock_quantity": 1,
    })
    assert resp.status_code == 401


def test_19_list_products_requires_auth():
    """未认证商品列表返回 401"""
    resp = client.get("/api/v1/products")
    assert resp.status_code == 401


def test_20_create_product_invalid_status():
    """创建商品无效状态返回 422"""
    resp = client.post("/api/v1/products", json={
        "name": "状态测试", "sale_price": "10", "cost_price": "5",
        "stock_quantity": 1, "status": "invalid_status",
    }, headers=_auth())
    assert resp.status_code == 422


def test_21_update_product_invalid_status():
    """编辑商品无效状态返回 422"""
    resp = client.post("/api/v1/products", json={
        "name": "状态测试商品", "sale_price": "10", "cost_price": "5",
        "stock_quantity": 1, "sku": "SPU-STATUS-TEST",
    }, headers=_auth())
    cid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/products/{cid}", json={
        "status": "bad_status",
    }, headers=_auth())
    assert resp.status_code == 422


def test_22_create_product_stock_creates_movement():
    """创建商品有初始库存时生成库存流水"""
    resp = client.post("/api/v1/products", json={
        "name": "库存流水测试", "sale_price": "10", "cost_price": "5",
        "stock_quantity": 100, "sku": "SPU-MOV-TEST",
    }, headers=_auth())
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    resp = client.get("/api/v1/inventory/movements", params={"product_id": pid}, headers=_auth())
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    m = items[0]
    assert m["movement_type"] == "product_create"
    assert m["quantity_before"] == 0
    assert m["quantity_change"] == 100
    assert m["quantity_after"] == 100


def test_23_update_product_stock_creates_movement():
    """编辑商品库存时生成库存流水"""
    resp = client.post("/api/v1/products", json={
        "name": "编辑库存测试", "sale_price": "10", "cost_price": "5",
        "stock_quantity": 50, "sku": "SPU-MOV-UPD",
    }, headers=_auth())
    pid = resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/products/{pid}", json={
        "stock_quantity": 80,
    }, headers=_auth())
    assert resp.status_code == 200

    resp = client.get("/api/v1/inventory/movements", params={"product_id": pid}, headers=_auth())
    items = resp.json()["data"]["items"]
    # 应有两条：product_create (0→50) 和 product_update (50→80)
    types = [m["movement_type"] for m in items]
    assert "product_update" in types
    update_mov = next(m for m in items if m["movement_type"] == "product_update")
    assert update_mov["quantity_before"] == 50
    assert update_mov["quantity_change"] == 30
    assert update_mov["quantity_after"] == 80


def test_24_update_product_stock_no_change_no_movement():
    """编辑商品库存不变时不生成库存流水"""
    resp = client.post("/api/v1/products", json={
        "name": "不变库存测试", "sale_price": "10", "cost_price": "5",
        "stock_quantity": 20, "sku": "SPU-MOV-NOCHG",
    }, headers=_auth())
    pid = resp.json()["data"]["id"]

    # 获取当前流水数量
    resp = client.get("/api/v1/inventory/movements", params={"product_id": pid}, headers=_auth())
    count_before = len(resp.json()["data"]["items"])

    # 更新但不改库存
    resp = client.put(f"/api/v1/products/{pid}", json={
        "name": "不变库存测试改名",
    }, headers=_auth())
    assert resp.status_code == 200

    # 流水数量不变
    resp = client.get("/api/v1/inventory/movements", params={"product_id": pid}, headers=_auth())
    count_after = len(resp.json()["data"]["items"])
    assert count_after == count_before


def test_25_create_product_name_too_long_422():
    """商品名称超过 max_length 返回 422"""
    resp = client.post("/api/v1/products", json={
        "name": "A" * 201, "sale_price": "10", "cost_price": "5",
    }, headers=_auth())
    assert resp.status_code == 422


def test_26_create_product_remark_too_long_422():
    """备注超过 max_length 返回 422"""
    resp = client.post("/api/v1/products", json={
        "name": "备注超长测试", "sale_price": "10", "cost_price": "5",
        "remark": "R" * 501,
    }, headers=_auth())
    assert resp.status_code == 422


def test_27_product_list_cost_fields_hidden_for_non_privileged():
    """非特权用户查看商品列表时成本字段不返回"""
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, UserRole

    db = TestSession()
    try:
        # 创建非特权用户（有 product:list 但无 product:view_cost）
        viewer = User(
            id=uuid.uuid4(), username="product_viewer",
            hashed_password=hash_password("testpass123"),
            display_name="商品查看者",
            is_active=True, is_superuser=False,
        )
        db.add(viewer)
        db.flush()

        role = Role(id=uuid.uuid4(), name="product_viewer_role", display_name="商品查看角色")
        db.add(role)
        db.flush()
        db.add(UserRole(user_id=viewer.id, role_id=role.id))

        perm = Permission(id=uuid.uuid4(), code="product:list", name="商品列表", module="product")
        db.add(perm)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        db.commit()
        viewer_token = create_access_token(str(viewer.id))
    finally:
        db.close()

    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    resp = client.get("/api/v1/products", headers=viewer_headers)
    assert resp.status_code == 200

    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    for item in items:
        assert "cost_price" not in item
        assert "unit_profit" not in item
        assert "gross_margin" not in item
