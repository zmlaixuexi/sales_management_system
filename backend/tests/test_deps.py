"""deps.py 辅助函数单元测试"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.api.deps import (
    _get_user_permissions,
    check_owner_or_forbid,
    generate_sequential_code,
    get_or_404,
    has_permission,
    paginate,
    paginated_resp,
    parse_uuid_or_400,
    resp,
    safe_commit,
)
from app.db.session import Base
from app.models.user import User


def _make_user(*, superuser=False, perm_codes=None):
    """构造测试用户，直接绑定角色和权限"""
    from app.models.user import Permission, Role

    perms = [Permission(id=uuid.uuid4(), code=c, name=c) for c in (perm_codes or [])]
    role = Role(id=uuid.uuid4(), name="test_role", display_name="测试", permissions=perms)
    user = User(
        id=uuid.uuid4(),
        username="test",
        hashed_password="x",
        is_superuser=superuser,
        roles=[role],
    )
    return user


def test_get_user_permissions_collects_from_roles():
    """应收集所有角色的所有权限码"""
    user = _make_user(perm_codes=["product:view", "order:create", "customer:view"])
    perms = _get_user_permissions(user)
    assert perms == {"product:view", "order:create", "customer:view"}


def test_get_user_permissions_empty_roles():
    """无角色时返回空集"""
    user = _make_user(perm_codes=[])
    perms = _get_user_permissions(user)
    assert perms == set()


def test_get_user_permissions_dedup():
    """不同角色的相同权限码应去重"""
    from app.models.user import Permission, Role

    perm = Permission(id=uuid.uuid4(), code="product:view", name="查看商品")
    role1 = Role(id=uuid.uuid4(), name="r1", display_name="R1", permissions=[perm])
    role2 = Role(id=uuid.uuid4(), name="r2", display_name="R2", permissions=[perm])
    user = User(
        id=uuid.uuid4(),
        username="test",
        hashed_password="x",
        is_superuser=False,
        roles=[role1, role2],
    )
    perms = _get_user_permissions(user)
    assert perms == {"product:view"}


def test_has_permission_superuser():
    """超级用户自动拥有所有权限"""
    user = _make_user(superuser=True, perm_codes=[])
    assert has_permission(user, "anything") is True


def test_has_permission_granted():
    """拥有权限码时返回 True"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "product:view") is True


def test_has_permission_denied():
    """无权限码时返回 False"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "product:delete") is False


def test_check_owner_or_forbid_superuser():
    """超级用户直接通过"""
    user = _make_user(superuser=True)
    other_id = uuid.uuid4()
    check_owner_or_forbid(user, other_id, "order:view_all", "订单")


def test_check_owner_or_forbid_view_all():
    """有 view_all 权限的用户通过"""
    user = _make_user(perm_codes=["order:view_all"])
    check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")


def test_check_owner_or_forbid_owner():
    """资源所有者通过"""
    user = _make_user(perm_codes=[])
    check_owner_or_forbid(user, user.id, "order:view_all", "订单")


def test_check_owner_or_forbid_forbidden():
    """非所有者且无 view_all 权限 → 403"""
    user = _make_user(perm_codes=[])
    other_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, other_id, "order:view_all", "订单")
    assert exc_info.value.status_code == 403
    assert "无权访问此订单" in exc_info.value.detail["message"]


# ---- parse_uuid_or_400 ----


def test_parse_uuid_valid():
    """有效 UUID 正常返回"""
    uid = uuid.uuid4()
    assert parse_uuid_or_400(str(uid), "订单") == uid


def test_parse_uuid_invalid():
    """无效 UUID 抛 400"""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid_or_400("not-a-uuid", "订单")
    assert exc_info.value.status_code == 400
    assert "订单格式无效" in exc_info.value.detail["message"]


# ---- resp ----


def test_resp_default():
    """默认消息为 操作成功"""
    result = resp()
    assert result == {"success": True, "data": None, "message": "操作成功"}


def test_resp_with_data_and_message():
    """传入 data 和 message 正确返回"""
    result = resp(data={"id": 1}, message="创建成功")
    assert result["success"] is True
    assert result["data"] == {"id": 1}
    assert result["message"] == "创建成功"


# ---- paginated_resp ----


def test_paginated_resp():
    """分页响应结构正确"""
    items = [{"id": 1}, {"id": 2}]
    result = paginated_resp(items, page=2, page_size=10, total=25)
    data = result["data"]
    assert data["items"] == items
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert data["total"] == 25
    assert result["message"] == "查询成功"


def test_paginated_resp_custom_message():
    """自定义分页消息"""
    result = paginated_resp([], page=1, page_size=20, total=0, message="无数据")
    assert result["message"] == "无数据"


# ---- DB 依赖函数 ----
# 使用内存 SQLite 测试 get_or_404 / generate_sequential_code / paginate

_engine = create_engine("sqlite:///:memory:")
_TestSession = sessionmaker(bind=_engine)


class _FakeModel(Base):
    """带 deleted_at 的测试模型"""
    __tablename__ = "_test_fake"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class _NoDeleteModel(Base):
    """不带 deleted_at 的测试模型"""
    __tablename__ = "_test_no_delete"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))


Base.metadata.create_all(_engine)


@pytest.fixture()
def db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.query(_FakeModel).delete()
        session.query(_NoDeleteModel).delete()
        session.commit()
        session.close()


# ---- get_or_404 ----


def test_get_or_404_found(db: Session):
    """存在记录正常返回"""
    obj = _FakeModel(name="测试")
    db.add(obj)
    db.commit()
    result = get_or_404(db, _FakeModel, obj.id, "商品")
    assert result.id == obj.id


def test_get_or_404_not_found(db: Session):
    """不存在记录抛 404"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, uuid.uuid4(), "商品")
    assert exc_info.value.status_code == 404
    assert "商品不存在" in exc_info.value.detail["message"]


def test_get_or_404_invalid_uuid(db: Session):
    """无效 UUID 抛 404"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, "bad-uuid", "商品")
    assert exc_info.value.status_code == 404


def test_get_or_404_soft_deleted(db: Session):
    """软删除记录返回 404"""
    obj = _FakeModel(name="已删除", deleted_at=datetime.now(UTC))
    db.add(obj)
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, obj.id, "商品")
    assert exc_info.value.status_code == 404


def test_get_or_404_no_deleted_at(db: Session):
    """无 deleted_at 字段的模型正常查找"""
    obj = _NoDeleteModel(name="无删除字段")
    db.add(obj)
    db.commit()
    result = get_or_404(db, _NoDeleteModel, obj.id, "分类")
    assert result.name == "无删除字段"


# ---- generate_sequential_code ----


def test_generate_sequential_first(db: Session):
    """无历史记录时从 0001 开始"""
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code.endswith("-0001")
    assert code.startswith("ORD")


def test_generate_sequential_increments(db: Session):
    """有历史记录时序号递增"""
    today = datetime.now().strftime("%Y%m%d")
    prev_code = f"ORD{today}-0003"
    db.add(_FakeModel(name="a", code=prev_code))
    db.commit()
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code == f"ORD{today}-0004"


def test_generate_sequential_beyond_9(db: Session):
    """序号超过 9 时正确递增（字符串排序 0009 > 0010 问题验证）"""
    today = datetime.now().strftime("%Y%m%d")
    for i in range(1, 12):
        db.add(_FakeModel(name=f"seq-{i}", code=f"ORD{today}-{i:04d}"))
    db.commit()
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code == f"ORD{today}-0012"


# ---- paginate ----


def test_paginate_first_page(db: Session):
    """分页第一页"""
    for i in range(5):
        db.add(_FakeModel(name=f"item-{i}"))
    db.commit()
    query = db.query(_FakeModel)
    items, total = paginate(query, page=1, page_size=3)
    assert total == 5
    assert len(items) == 3


def test_paginate_last_page(db: Session):
    """分页最后一页不足 page_size"""
    for i in range(5):
        db.add(_FakeModel(name=f"item-{i}"))
    db.commit()
    query = db.query(_FakeModel)
    items, total = paginate(query, page=2, page_size=3)
    assert total == 5
    assert len(items) == 2


def test_paginate_empty(db: Session):
    """空表返回空"""
    query = db.query(_FakeModel)
    items, total = paginate(query, page=1, page_size=10)
    assert total == 0
    assert items == []


# ---- PaginationParams 约束 ----


def test_pagination_params_page_max_ok():
    """page = 10000 正常通过 Query 校验"""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from app.api.deps import PaginationParams

    test_app = FastAPI()

    @test_app.get("/test")
    def test_endpoint(p: PaginationParams = Depends()):
        return {"page": p.page, "page_size": p.page_size}

    client = TestClient(test_app)
    resp = client.get("/test?page=10000&page_size=20")
    assert resp.status_code == 200
    assert resp.json()["page"] == 10000


def test_pagination_params_page_over_max_rejected():
    """page = 10001 被 Query 校验拒绝为 422"""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from app.api.deps import PaginationParams

    test_app = FastAPI()

    @test_app.get("/test")
    def test_endpoint(p: PaginationParams = Depends()):
        return {"page": p.page, "page_size": p.page_size}

    client = TestClient(test_app)
    resp = client.get("/test?page=10001&page_size=20")
    assert resp.status_code == 422


def test_pagination_params_page_zero_rejected():
    """page = 0 被拒绝"""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from app.api.deps import PaginationParams

    test_app = FastAPI()

    @test_app.get("/test")
    def test_endpoint(p: PaginationParams = Depends()):
        return {"page": p.page, "page_size": p.page_size}

    client = TestClient(test_app)
    resp = client.get("/test?page=0&page_size=20")
    assert resp.status_code == 422


# ---- safe_commit ----


def test_safe_commit_success(db: Session):
    """正常提交不抛异常"""
    obj = _FakeModel(name="safe_commit_test")
    db.add(obj)
    safe_commit(db)
    assert db.query(_FakeModel).filter(_FakeModel.name == "safe_commit_test").first() is not None


def test_safe_commit_rollback_on_failure(db: Session):
    """commit 失败时自动 rollback，session 保持可用"""
    obj = _FakeModel(name="rollback_test")
    db.add(obj)
    safe_commit(db)

    # 制造唯一约束冲突：code 列无唯一约束，用 name 重复 + 手动异常模拟
    # 更直接的方式：让 commit 抛异常，验证 rollback 被调用

    original_commit = db.commit
    call_count = {"rollback": 0}
    original_rollback = db.rollback

    def _failing_commit():
        raise RuntimeError("simulated commit failure")

    def _counting_rollback():
        call_count["rollback"] += 1
        return original_rollback()

    db.commit = _failing_commit
    db.rollback = _counting_rollback

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        safe_commit(db)

    assert call_count["rollback"] == 1

    # 恢复 session 方法，验证 session 仍可用
    db.commit = original_commit
    db.rollback = original_rollback
    db.add(_FakeModel(name="after_recovery"))
    safe_commit(db)
    assert db.query(_FakeModel).filter(_FakeModel.name == "after_recovery").first() is not None


def test_safe_commit_reraises_original_exception(db: Session):
    """重新抛出原始异常类型（不只是 Exception）"""
    from sqlalchemy.exc import IntegrityError
    from unittest.mock import MagicMock

    original_commit = db.commit
    original_rollback = db.rollback

    def _integrity_error():
        raise IntegrityError("", "", Exception())

    db.commit = _integrity_error
    db.rollback = MagicMock()

    with pytest.raises(IntegrityError):
        safe_commit(db)

    assert db.rollback.call_count == 1

    # 恢复 session 方法避免影响 teardown
    db.commit = original_commit
    db.rollback = original_rollback
