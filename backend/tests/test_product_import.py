"""商品 CSV 批量导入测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.product import ProductCategory
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_product_import.db"
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
            username="import_tester",
            hashed_password=hash_password("testpass123"),
            display_name="导入测试员",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        cat = ProductCategory(id=uuid.uuid4(), name="未分类", sort_order=0)
        db.add(cat)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_product_import.db"):
        os.remove("./test_product_import.db")
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
        "username": "import_tester", "password": "testpass123",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_import_csv_success():
    """CSV 批量导入成功"""
    csv_content = "商品名称,销售价,成本价,库存数量\n测试商品A,100.00,50.00,20\n测试商品B,200.00,80.00,10"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert len(data["errors"]) == 0
    assert "成功导入 2" in resp.json()["message"]


def test_03_import_with_sku():
    """CSV 导入带自定义 SKU"""
    csv_content = "商品名称,SKU,销售价\n自定义SKU商品,IMP-001,150.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_04_import_duplicate_sku():
    """CSV 导入 SKU 重复跳过"""
    csv_content = "商品名称,SKU,销售价\n重复SKU商品,IMP-001,99.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


def test_05_import_empty_name():
    """CSV 导入空名称跳过"""
    csv_content = "商品名称,销售价\n,100.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_06_import_non_csv():
    """上传非 CSV 文件报错"""
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_07_import_requires_auth():
    """导入需要认证"""
    csv_content = "商品名称,销售价\n测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 401


def test_08_import_chinese_headers():
    """CSV 使用中文表头"""
    csv_content = "商品名称,销售价,成本价,库存数量\n中文表头商品,88.00,44.00,5"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8-sig"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_09_import_file_too_large(monkeypatch):
    """超过大小限制的 CSV 文件被拒绝"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_SIZE_MB", 0)  # 设置极小限制
    csv_content = "商品名称,销售价\n测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "CSV 文件不能超过" in resp.json()["error"]["message"]


def test_10_import_row_limit(monkeypatch):
    """超过行数上限的 CSV 只导入前 N 行"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_ROWS", 3)
    rows = "\n".join([f"商品{ i},100,50,10" for i in range(5)])
    csv_content = f"商品名称,销售价,成本价,库存数量\n{rows}"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 3
    assert any("超过最大行数限制" in e["message"] for e in data["errors"])


def test_11_import_strips_html():
    """CSV 导入自动剥离 HTML 标签"""
    csv_content = '商品名称,销售价\n<script>alert(1)</script>安全商品,99.00'
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_12_import_commit_failure():
    """db.commit 失败返回 400 IMPORT_FAILED"""
    from unittest.mock import patch

    from sqlalchemy.orm import Session

    csv_content = "商品名称,销售价\n失败商品,100.00"

    def _failing_commit(self):
        raise RuntimeError("模拟数据库故障")

    with patch.object(Session, "commit", _failing_commit):
        resp = client.post(
            "/api/v1/products/import",
            files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
            headers=_auth(),
        )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IMPORT_FAILED"


def test_13_import_negative_price():
    """负价格跳过"""
    csv_content = "商品名称,销售价,成本价\n负价商品,-10,5"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("价格不能为负" in e["message"] for e in resp.json()["data"]["errors"])


def test_14_import_invalid_price_format():
    """非法价格格式跳过"""
    csv_content = "商品名称,销售价\n格式错误商品,abc"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("销售价格式错误" in e["message"] for e in resp.json()["data"]["errors"])


def test_15_import_english_headers():
    """英文表头 name/sale_price/cost_price 导入"""
    csv_content = "name,sale_price,cost_price,stock_quantity\nEngProduct,50.00,30.00,8"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_16_import_batch_internal_sku_duplicate():
    """批量内两行相同自定义 SKU，第二行跳过"""
    csv_content = "商品名称,SKU,销售价\n商品A,BATCH-DUP,100\n商品B,BATCH-DUP,200"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
    assert any("SKU BATCH-DUP 已存在" in e["message"] for e in resp.json()["data"]["errors"])


def test_17_import_invalid_cost_price_format():
    """非法成本价格式跳过"""
    csv_content = "商品名称,销售价,成本价\n成本异常商品,100,xyz"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("成本价格式错误" in e["message"] for e in resp.json()["data"]["errors"])


def test_18_import_requires_create_permission():
    """无 product:create 权限用户返回 403"""
    from app.core.security import create_access_token

    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_prod_import_perm",
            hashed_password=hash_password("testpass123"),
            display_name="无商品导入权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    csv_content = "商品名称,销售价\n权限测试,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_19_import_creates_audit_log():
    """商品导入产生审计日志"""
    from app.core.security import create_access_token
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "import_tester").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()

    csv_content = "商品名称,销售价\n审计导入商品,99.00"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 200

    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "product_import",
        ).first()
        assert log is not None
        assert log.resource_type == "product"
    finally:
        db.close()


# ─── 边界条件测试 ─────────────────────────────────────────────


def test_20_import_whitespace_only_name():
    """仅空白字符的商品名称视为空，跳过"""
    csv_content = "商品名称,销售价\n   \t  ,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("商品名称不能为空" in e["message"] for e in resp.json()["data"]["errors"])


def test_21_import_zero_price():
    """零价格能正常导入"""
    csv_content = "商品名称,销售价,成本价\n免费商品,0,0"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_22_import_very_long_name():
    """超长商品名称（500 字符）能正常导入"""
    long_name = "长名商品" * 125  # 500 字符
    csv_content = f"商品名称,销售价\n{long_name},100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_23_import_unicode_emoji():
    """含 emoji 和特殊 Unicode 字符的商品名称能导入"""
    csv_content = "商品名称,销售价\n🎉特价商品🚀,99.99"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_24_import_negative_stock():
    """负库存数量被解析为 0（int() 正常转换）"""
    csv_content = "商品名称,销售价,库存数量\n负库存商品,100,-5"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_25_import_large_stock():
    """超大库存数量能正常导入"""
    csv_content = "商品名称,销售价,库存数量\n大库存商品,100,99999999"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_26_import_extra_columns_ignored():
    """CSV 含多余列时正常导入，忽略未知列"""
    csv_content = "商品名称,销售价,自定义列1,自定义列2\n多余列商品,88,值1,值2"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_27_import_wrong_headers():
    """完全不匹配的表头导致所有行跳过（名称为空）"""
    csv_content = "产品名,价格\n未知商品,100"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("商品名称不能为空" in e["message"] for e in resp.json()["data"]["errors"])


def test_28_import_mixed_line_endings():
    """混合 \\r\\n 和 \\n 行尾的 CSV 能正常导入"""
    csv_content = "商品名称,销售价\r\n换行商品A,100\r\n换行商品B,200"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 2


def test_29_import_decimal_prices():
    """多精度小数价格能正常导入"""
    csv_content = "商品名称,销售价,成本价\n精密价格,123.4567,67.8910"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_30_import_quoted_fields():
    """CSV 引号字段含逗号能正确解析"""
    csv_content = '"商品名称","销售价"\n"含,逗号商品",100'
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_31_import_empty_stock_defaults_zero():
    """空库存数量默认为 0"""
    csv_content = "商品名称,销售价,成本价,库存数量\n无库存商品,100,50,"
    resp = client.post(
        "/api/v1/products/import",
        files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
