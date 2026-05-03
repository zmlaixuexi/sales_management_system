"""客户 CSV 批量导入测试"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.db.session import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_customer_import.db"
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
            username="customer_importer",
            hashed_password=hash_password("TestPass123!"),
            display_name="客户导入员",
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
    if os.path.exists("./test_customer_import.db"):
        os.remove("./test_customer_import.db")
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
        "username": "customer_importer", "password": "TestPass123!",
    })
    assert resp.status_code == 200
    _tokens["access"] = resp.json()["data"]["access_token"]


def test_02_import_csv_success():
    """CSV 批量导入成功"""
    csv_content = (
        "客户名称,电话,联系人,邮箱\n"
        "测试客户A,13800001111,张三,a@test.com\n"
        "测试客户B,13800002222,李四,b@test.com"
    )
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert len(data["errors"]) == 0
    assert "成功导入 2" in resp.json()["message"]


def test_03_import_with_details():
    """CSV 导入带来源和等级"""
    csv_content = "客户名称,电话,来源,等级\nVIP客户,13900001111,online,vip"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_04_import_duplicate_phone():
    """CSV 导入手机号重复跳过"""
    csv_content = "客户名称,电话\n重复手机客户,13800001111"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert len(resp.json()["data"]["errors"]) == 1


def test_05_import_duplicate_in_batch():
    """CSV 批量内手机号重复"""
    csv_content = "客户名称,电话\n客户X,13899991111\n客户Y,13899991111"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
    assert len(resp.json()["data"]["errors"]) == 1


def test_06_import_empty_name():
    """CSV 导入空名称跳过"""
    csv_content = "客户名称,电话\n,13800009999"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0


def test_07_import_non_csv():
    """上传非 CSV 文件报错"""
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_08_import_requires_auth():
    """导入需要认证"""
    csv_content = "客户名称,电话\n测试,13800008888"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 401


def test_09_import_file_too_large(monkeypatch):
    """超过大小限制的 CSV 文件被拒绝"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_SIZE_MB", 0)
    csv_content = "客户名称,电话\n测试,13800008888"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "CSV 文件不能超过" in resp.json()["error"]["message"]


def test_10_import_row_limit(monkeypatch):
    """超过行数上限的 CSV 只导入前 N 行"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_CSV_IMPORT_ROWS", 2)
    rows = "\n".join([f"客户{ i},138000{i:05d}" for i in range(4)])
    csv_content = f"客户名称,电话\n{rows}"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert any("超过最大行数限制" in e["message"] for e in data["errors"])


def test_11_import_strips_html():
    """CSV 导入自动剥离 HTML 标签"""
    csv_content = '客户名称,电话,联系人,邮箱\n<script>x</script>安全客户,13800007777,<b>张</b>,a@b.com'
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_12_import_invalid_source():
    """CSV 导入无效 source 值跳过"""
    csv_content = "客户名称,电话,来源\n无效来源客户,13800008888,invalid_source"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("来源值无效" in e["message"] for e in resp.json()["data"]["errors"])


def test_13_import_invalid_level():
    """CSV 导入无效 level 值跳过"""
    csv_content = "客户名称,电话,等级\n无效等级客户,13800008889,super_vip"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("等级值无效" in e["message"] for e in resp.json()["data"]["errors"])


def test_14_import_commit_failure():
    """db.commit 失败返回 400 IMPORT_FAILED"""
    from unittest.mock import patch

    from sqlalchemy.orm import Session

    csv_content = "客户名称,电话\n失败客户,13800006666"

    def _failing_commit(self):
        raise RuntimeError("模拟数据库故障")

    with patch.object(Session, "commit", _failing_commit):
        resp = client.post(
            "/api/v1/customers/import",
            files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
            headers=_auth(),
        )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IMPORT_FAILED"


def test_15_import_english_headers():
    """英文表头 name/phone/contact_name/email 导入"""
    csv_content = "name,phone,contact_name,email\nEngCustomer,13700001234,Bob,bob@test.com"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_16_import_no_phone():
    """无电话号码可以导入（电话为可选字段）"""
    csv_content = "客户名称\n无电话客户"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_17_import_requires_create_permission():
    """无 customer:create 权限用户返回 403"""
    from app.core.security import create_access_token

    db = TestSession()
    try:
        nop = User(
            id=uuid.uuid4(), username="no_import_perm",
            hashed_password=hash_password("TestPass123!"),
            display_name="无导入权限", is_active=True, is_superuser=False,
        )
        db.add(nop)
        db.commit()
        token = create_access_token(str(nop.id))
    finally:
        db.close()

    csv_content = "客户名称,电话\n权限测试,13800005555"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_18_import_creates_audit_log():
    """客户导入产生审计日志"""
    from app.core.security import create_access_token
    from app.models.audit import AuditLog

    db = TestSession()
    try:
        user = db.query(User).filter(User.username == "customer_importer").first()
        headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        db.close()

    csv_content = "客户名称,电话\n审计导入客户,13800004444"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 200

    db = TestSession()
    try:
        log = db.query(AuditLog).filter(
            AuditLog.action == "customer_import",
        ).first()
        assert log is not None
        assert log.resource_type == "customer"
    finally:
        db.close()


# ─── 边界条件测试 ─────────────────────────────────────────────


def test_19_import_whitespace_only_name():
    """仅空白字符的客户名称视为空，跳过"""
    csv_content = "客户名称,电话\n   \t  ,13800001001"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("客户名称不能为空" in e["message"] for e in resp.json()["data"]["errors"])


def test_20_import_very_long_name():
    """超长客户名称（500 字符）能正常导入"""
    long_name = "长名客户" * 125  # 500 字符
    csv_content = f"客户名称,电话\n{long_name},13800001002"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_21_import_unicode_emoji():
    """含 emoji 和特殊 Unicode 字符的客户名称能导入"""
    csv_content = "客户名称,电话,联系人,邮箱\n🎉VIP客户🚀,13800001003,张👤,emoji@test.com"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_22_import_mixed_line_endings():
    """混合 \\r\\n 和 \\n 行尾的 CSV 能正常导入"""
    csv_content = "客户名称,电话\r\n换行客户A,13800001004\r\n换行客户B,13800001005"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 2


def test_23_import_wrong_headers():
    """完全不匹配的表头导致所有行跳过（名称为空）"""
    csv_content = "姓名,手机号码\n未知客户,13800001006"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 0
    assert any("客户名称不能为空" in e["message"] for e in resp.json()["data"]["errors"])


def test_24_import_extra_columns_ignored():
    """CSV 含多余列时正常导入，忽略未知列"""
    csv_content = "客户名称,电话,自定义列1,自定义列2\n多余列客户,13800001007,值1,值2"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_25_import_quoted_fields():
    """CSV 引号字段含逗号和换行能正确解析"""
    csv_content = '客户名称,电话,备注\n"含,逗号客户",13800001008,"备注\n换行"'
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_26_import_phone_with_spaces():
    """电话号码含空格时被 strip 后处理"""
    csv_content = "客户名称,电话\n空格电话客户, 13800001009 "
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1


def test_27_import_long_remark():
    """超长备注（1000 字符）能正常导入"""
    long_remark = "备注内容" * 125  # 500 字符
    csv_content = f"客户名称,电话,备注\n备注客户,13800001010,{long_remark}"
    resp = client.post(
        "/api/v1/customers/import",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["created"] == 1
