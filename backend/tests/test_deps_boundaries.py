"""代码质量：后端依赖注入（deps.py）边界测试 — 覆盖 parse_uuid_or_400、
get_or_404、check_owner_or_forbid、has_permission、resp、fmt_dt、active_query、
generate_sequential_code、safe_commit 的边界场景"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.api.deps import (
    _get_user_permissions,
    active_query,
    check_owner_or_forbid,
    fmt_dt,
    generate_sequential_code,
    get_or_404,
    has_permission,
    parse_uuid_or_400,
    resp,
    safe_commit,
)
from app.db.session import Base
from app.models.user import User

# ═══════════════════════════════════════════════════════
# 测试基础设施
# ═══════════════════════════════════════════════════════


def _make_user(*, superuser=False, perm_codes=None):
    from app.models.user import Permission, Role

    perms = [Permission(id=uuid.uuid4(), code=c, name=c) for c in (perm_codes or [])]
    role = Role(id=uuid.uuid4(), name="test_role", display_name="测试", permissions=perms)
    return User(
        id=uuid.uuid4(),
        username="test",
        hashed_password="x",
        is_superuser=superuser,
        roles=[role],
    )


_engine = create_engine("sqlite:///:memory:")
_TestSession = sessionmaker(bind=_engine)


class _FakeModel(Base):
    __tablename__ = "_test_deps_boundary"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class _NoDeleteModel(Base):
    __tablename__ = "_test_deps_boundary_nodel"
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


# ═══════════════════════════════════════════════════════
# 1. parse_uuid_or_400 边界
# ═══════════════════════════════════════════════════════


def test_parse_uuid_uppercase():
    """大写 UUID 正常解析"""
    uid = uuid.uuid4()
    assert parse_uuid_or_400(str(uid).upper(), "订单") == uid


def test_parse_uuid_with_braces():
    """带花括号的 UUID 字符串也被 Python UUID 接受"""
    uid = uuid.uuid4()
    # Python uuid.UUID 接受 {uuid} 格式
    result = parse_uuid_or_400("{" + str(uid) + "}", "资源")
    assert result == uid


def test_parse_uuid_empty_string():
    """空字符串失败"""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid_or_400("", "标签")
    assert exc_info.value.status_code == 400
    assert "标签格式无效" in exc_info.value.detail["message"]


def test_parse_uuid_label_in_message():
    """label 出现在错误消息中"""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid_or_400("xxx", "自定义标签")
    assert "自定义标签" in exc_info.value.detail["message"]


def test_parse_uuid_error_code():
    """错误 code 为 VALIDATION_FAILED"""
    with pytest.raises(HTTPException) as exc_info:
        parse_uuid_or_400("bad", "订单")
    assert exc_info.value.detail["code"] == "VALIDATION_FAILED"


def test_parse_uuid_returns_uuid_type():
    """返回 uuid.UUID 类型"""
    uid = uuid.uuid4()
    result = parse_uuid_or_400(str(uid), "订单")
    assert isinstance(result, uuid.UUID)


# ═══════════════════════════════════════════════════════
# 2. get_or_404 边界
# ═══════════════════════════════════════════════════════


def test_get_or_404_string_uuid(db: Session):
    """字符串 UUID 正常查询"""
    obj = _FakeModel(name="str-uuid")
    db.add(obj)
    db.commit()
    result = get_or_404(db, _FakeModel, str(obj.id), "商品")
    assert result.id == obj.id


def test_get_or_404_uuid_object(db: Session):
    """UUID 对象正常查询"""
    obj = _FakeModel(name="obj-uuid")
    db.add(obj)
    db.commit()
    result = get_or_404(db, _FakeModel, obj.id, "商品")
    assert result.id == obj.id


def test_get_or_404_label_in_message(db: Session):
    """label 出现在 404 消息中"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, uuid.uuid4(), "客户")
    assert "客户不存在" in exc_info.value.detail["message"]


def test_get_or_404_error_code(db: Session):
    """404 错误 code 为 RESOURCE_NOT_FOUND"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, uuid.uuid4(), "资源")
    assert exc_info.value.detail["code"] == "RESOURCE_NOT_FOUND"


def test_get_or_404_invalid_string_uuid(db: Session):
    """无效字符串 UUID 返回 404（不是 500）"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _FakeModel, "not-uuid", "资源")
    assert exc_info.value.status_code == 404


def test_get_or_404_not_deleted_found(db: Session):
    """未删除记录正常找到"""
    obj = _FakeModel(name="active", deleted_at=None)
    db.add(obj)
    db.commit()
    result = get_or_404(db, _FakeModel, obj.id, "商品")
    assert result.name == "active"


def test_get_or_404_no_delete_model_not_found(db: Session):
    """无 deleted_at 模型不存在返回 404"""
    with pytest.raises(HTTPException) as exc_info:
        get_or_404(db, _NoDeleteModel, uuid.uuid4(), "分类")
    assert exc_info.value.status_code == 404


# ═══════════════════════════════════════════════════════
# 3. check_owner_or_forbid 边界
# ═══════════════════════════════════════════════════════


def test_check_owner_custom_label():
    """自定义 label 出现在错误消息中"""
    user = _make_user(perm_codes=[])
    other_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, other_id, "payment:view_all", "收款记录")
    assert "无权访问此收款记录" in exc_info.value.detail["message"]


def test_check_owner_error_code():
    """403 错误 code 为 AUTH_FORBIDDEN"""
    user = _make_user(perm_codes=[])
    with pytest.raises(HTTPException) as exc_info:
        check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")
    assert exc_info.value.detail["code"] == "AUTH_FORBIDDEN"


def test_check_owner_same_user_passes():
    """owner_id 等于 user.id 通过"""
    user = _make_user(perm_codes=[])
    check_owner_or_forbid(user, user.id, "order:view_all", "订单")


def test_check_owner_view_all_passes():
    """有 view_all 权限通过（非 owner）"""
    user = _make_user(perm_codes=["order:view_all"])
    check_owner_or_forbid(user, uuid.uuid4(), "order:view_all", "订单")


def test_check_owner_superuser_before_view_all():
    """超级用户优先于 view_all 检查"""
    user = _make_user(superuser=True, perm_codes=[])
    check_owner_or_forbid(user, uuid.uuid4(), "nonexistent:perm", "资源")


def test_check_owner_no_exception_returns_none():
    """检查通过时返回 None"""
    user = _make_user(superuser=True)
    result = check_owner_or_forbid(user, uuid.uuid4(), "x:view_all", "资源")
    assert result is None


# ═══════════════════════════════════════════════════════
# 4. has_permission 边界
# ═══════════════════════════════════════════════════════


def test_has_permission_empty_string():
    """空字符串权限码返回 False"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "") is False


def test_has_permission_superuser_empty_perms():
    """超级用户空权限仍返回 True"""
    user = _make_user(superuser=True, perm_codes=[])
    assert has_permission(user, "anything:here") is True


def test_has_permission_exact_match():
    """精确匹配权限码"""
    user = _make_user(perm_codes=["product:view"])
    assert has_permission(user, "product:view") is True
    assert has_permission(user, "product:view:detail") is False
    assert has_permission(user, "product") is False


def test_has_permission_no_roles():
    """无角色返回 False"""
    user = _make_user(perm_codes=[])
    assert has_permission(user, "product:view") is False


# ═══════════════════════════════════════════════════════
# 5. _get_user_permissions 边界
# ═══════════════════════════════════════════════════════


def test_get_user_permissions_multiple_roles():
    """多角色权限合并"""
    from app.models.user import Permission, Role

    p1 = Permission(id=uuid.uuid4(), code="a:b", name="ab")
    p2 = Permission(id=uuid.uuid4(), code="c:d", name="cd")
    p3 = Permission(id=uuid.uuid4(), code="e:f", name="ef")
    r1 = Role(id=uuid.uuid4(), name="r1", display_name="R1", permissions=[p1, p2])
    r2 = Role(id=uuid.uuid4(), name="r2", display_name="R2", permissions=[p2, p3])
    user = User(id=uuid.uuid4(), username="multi", hashed_password="x", roles=[r1, r2])
    perms = _get_user_permissions(user)
    assert perms == {"a:b", "c:d", "e:f"}


def test_get_user_permissions_returns_set():
    """返回 set 类型"""
    user = _make_user(perm_codes=["a:b"])
    assert isinstance(_get_user_permissions(user), set)


# ═══════════════════════════════════════════════════════
# 6. resp 边界
# ═══════════════════════════════════════════════════════


def test_resp_none_data():
    """data=None 默认"""
    result = resp()
    assert result["data"] is None


def test_resp_empty_list():
    """data=[] 传递"""
    result = resp(data=[])
    assert result["data"] == []


def test_resp_empty_dict():
    """data={} 传递"""
    result = resp(data={})
    assert result["data"] == {}


def test_resp_string_data():
    """data 为字符串"""
    result = resp(data="hello")
    assert result["data"] == "hello"


def test_resp_success_always_true():
    """success 始终为 True"""
    assert resp()["success"] is True
    assert resp(data="x")["success"] is True
    assert resp(message="y")["success"] is True


def test_resp_default_message():
    """默认消息"""
    assert resp()["message"] == "操作成功"


def test_resp_custom_message():
    """自定义消息"""
    assert resp(message="删除成功")["message"] == "删除成功"


def test_resp_has_three_keys():
    """默认有三键：success, data, message"""
    result = resp()
    assert set(result.keys()) == {"success", "data", "message"}


# ═══════════════════════════════════════════════════════
# 7. fmt_dt 边界
# ═══════════════════════════════════════════════════════


def test_fmt_dt_none():
    """None 返回 None"""
    assert fmt_dt(None) is None


def test_fmt_dt_utc_datetime():
    """UTC datetime 返回 ISO 格式"""
    dt = datetime(2026, 5, 4, 12, 30, 45, tzinfo=UTC)
    result = fmt_dt(dt)
    assert "2026-05-04" in result
    assert "12:30:45" in result


def test_fmt_dt_naive_datetime():
    """无时区 datetime 返回 ISO 格式"""
    dt = datetime(2026, 1, 1, 0, 0, 0)
    result = fmt_dt(dt)
    assert result == "2026-01-01T00:00:00"


def test_fmt_dt_returns_string():
    """返回 str 类型"""
    dt = datetime(2026, 5, 4, tzinfo=UTC)
    assert isinstance(fmt_dt(dt), str)


def test_fmt_dt_with_microseconds():
    """带微秒的 datetime"""
    dt = datetime(2026, 5, 4, 12, 0, 0, 123456, tzinfo=UTC)
    result = fmt_dt(dt)
    assert "123456" in result


# ═══════════════════════════════════════════════════════
# 8. active_query 边界
# ═══════════════════════════════════════════════════════


def test_active_query_filters_deleted(db: Session):
    """active_query 过滤 deleted_at 不为空的记录"""
    db.add(_FakeModel(name="active", deleted_at=None))
    db.add(_FakeModel(name="deleted", deleted_at=datetime.now(UTC)))
    db.commit()

    query = active_query(db, _FakeModel)
    results = query.all()
    assert len(results) == 1
    assert results[0].name == "active"


def test_active_query_no_deleted_field(db: Session):
    """无 deleted_at 字段不做过滤"""
    db.add(_NoDeleteModel(name="item"))
    db.commit()

    query = active_query(db, _NoDeleteModel)
    results = query.all()
    assert len(results) == 1


def test_active_query_returns_query(db: Session):
    """返回 SQLAlchemy Query 对象"""
    query = active_query(db, _FakeModel)
    # Query 对象有 .all(), .count(), .filter() 等方法
    assert hasattr(query, "all")
    assert hasattr(query, "count")
    assert hasattr(query, "filter")


def test_active_query_empty_table(db: Session):
    """空表返回空列表"""
    query = active_query(db, _FakeModel)
    assert query.all() == []


# ═══════════════════════════════════════════════════════
# 9. generate_sequential_code 边界
# ═══════════════════════════════════════════════════════


def test_seq_code_format(db: Session):
    """编码格式为 PREFIXYYYYMMDD-NNNN"""
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "SKU")
    today = datetime.now().strftime("%Y%m%d")
    assert code == f"SKU{today}-0001"


def test_seq_code_different_prefixes(db: Session):
    """不同前缀独立计数"""
    code_a = generate_sequential_code(db, _FakeModel, _FakeModel.code, "AA")
    code_b = generate_sequential_code(db, _FakeModel, _FakeModel.code, "BB")
    assert code_a != code_b
    assert code_a.startswith("AA")
    assert code_b.startswith("BB")


def test_seq_code_increments_from_last(db: Session):
    """从已有最大序号递增"""
    today = datetime.now().strftime("%Y%m%d")
    db.add(_FakeModel(name="last", code=f"ORD{today}-0042"))
    db.commit()
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code == f"ORD{today}-0043"


def test_seq_code_four_digit_padding(db: Session):
    """序号四位补零"""
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "T")
    assert code.endswith("-0001")


def test_seq_code_ignores_different_date(db: Session):
    """不同日期的编码不影响当天序号"""
    db.add(_FakeModel(name="old", code="ORD20250101-0010"))
    db.commit()
    today = datetime.now().strftime("%Y%m%d")
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code == f"ORD{today}-0001"


def test_seq_code_handles_garbage_in_code(db: Session):
    """已有编码格式异常时回退到 0001"""
    today = datetime.now().strftime("%Y%m%d")
    db.add(_FakeModel(name="bad", code=f"ORD{today}-NOTANUM"))
    db.commit()
    code = generate_sequential_code(db, _FakeModel, _FakeModel.code, "ORD")
    assert code == f"ORD{today}-0001"


# ═══════════════════════════════════════════════════════
# 10. safe_commit 边界
# ═══════════════════════════════════════════════════════


def test_safe_commit_normal(db: Session):
    """正常提交"""
    db.add(_FakeModel(name="normal"))
    safe_commit(db)
    assert db.query(_FakeModel).filter(_FakeModel.name == "normal").first() is not None


def test_safe_commit_rollback_called(db: Session):
    """异常时 rollback 被调用"""
    original_commit = db.commit
    original_rollback = db.rollback
    rollback_called = {"count": 0}

    def _fail():
        raise RuntimeError("boom")

    def _count_rollback():
        rollback_called["count"] += 1
        return original_rollback()

    db.commit = _fail
    db.rollback = _count_rollback

    with pytest.raises(RuntimeError):
        safe_commit(db)

    assert rollback_called["count"] == 1
    db.commit = original_commit
    db.rollback = original_rollback


def test_safe_commit_preserves_exception_type(db: Session):
    """保留原始异常类型"""
    from sqlalchemy.exc import IntegrityError

    original_commit = db.commit
    db.commit = lambda: (_ for _ in ()).throw(IntegrityError("", "", Exception()))

    with pytest.raises(IntegrityError):
        safe_commit(db)

    db.commit = original_commit
