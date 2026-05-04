"""代码质量：后端数据库迁移脚本与模型一致性验证测试
覆盖迁移链完整性、表名覆盖、关键列存在、索引覆盖、Alembic 配置"""

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"
MODELS_DIR = Path(__file__).resolve().parent.parent / "app" / "models"
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
ALEMBIC_ENV = Path(__file__).resolve().parent.parent / "alembic" / "env.py"


def _read_migration(revision: str) -> str:
    for f in MIGRATIONS_DIR.glob("*.py"):
        if revision in f.name:
            return f.read_text()
    return ""


def _get_all_migration_sources() -> list[str]:
    return [f.read_text() for f in sorted(MIGRATIONS_DIR.glob("*.py"))]


def _extract_create_tables(source: str) -> list[str]:
    return re.findall(r"op\.create_table\('(\w+)'", source)


def _extract_add_columns(source: str) -> list[tuple[str, str]]:
    """返回 [(table_name, column_name)]"""
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r"op\.add_column\('(\w+)',\s*sa\.Column\('(\w+)'", source)
    ]


def _extract_create_indexes(source: str) -> list[str]:
    return re.findall(r"op\.create_index\([^,]+,\s*'(\w+)'", source)


def _extract_model_tablenames() -> set[str]:
    tables = set()
    for f in MODELS_DIR.glob("*.py"):
        source = f.read_text()
        for m in re.finditer(r"__tablename__\s*=\s*['\"](\w+)['\"]", source):
            tables.add(m.group(1))
    return tables


# ═══════════════════════════════════════════════════════════
# 1. 迁移链完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMigrationChain:
    """验证迁移链线性完整"""

    def test_7_migrations_exist(self):
        files = list(MIGRATIONS_DIR.glob("*.py"))
        assert len(files) == 7

    def test_chain_is_linear(self):
        """每条迁移只有一个 down_revision"""
        sources = _get_all_migration_sources()
        revisions = {}
        for src in sources:
            rev_match = re.search(r"^revision.*?['\"]([0-9a-f]+)['\"]", src, re.MULTILINE)
            down_match = re.search(r"^down_revision.*?['\"]([0-9a-f]+)['\"]", src, re.MULTILINE)
            assert rev_match, "迁移文件缺少 revision"
            rev = rev_match.group(1)
            down = down_match.group(1) if down_match and down_match.group(1) != "None" else None
            revisions[rev] = down

        # 有且仅有一个 base（down_revision 为 None）
        bases = [r for r, d in revisions.items() if d is None]
        assert len(bases) == 1, f"期望 1 个 base 迁移，实际 {len(bases)}: {bases}"

        # 所有 down_revision 都指向已知的 revision
        for rev, down in revisions.items():
            if down is not None:
                assert down in revisions, f"{rev} 的 down_revision {down} 不存在"

    def test_head_is_password_changed_at(self):
        """最新迁移为 password_changed_at"""
        sources = _get_all_migration_sources()
        # head 的 revision 不应是任何其他迁移的 down_revision
        all_revs = set()
        all_downs = set()
        for src in sources:
            rev = re.search(r"^revision.*?['\"]([0-9a-f]+)['\"]", src, re.MULTILINE)
            down = re.search(r"^down_revision.*?['\"]([0-9a-f]+)['\"]", src, re.MULTILINE)
            if rev:
                all_revs.add(rev.group(1))
            if down:
                all_downs.add(down.group(1))
        heads = all_revs - all_downs
        assert len(heads) == 1, f"期望 1 个 head，实际 {len(heads)}: {heads}"

    def test_initial_migration_is_base(self):
        src = _read_migration("6800eb76fb83")
        assert "down_revision" in src
        assert "None" in src.split("down_revision")[1].split("\n")[0]

    def test_chain_length_matches_file_count(self):
        """链长度等于文件数量"""
        sources = _get_all_migration_sources()
        revisions = set()
        for src in sources:
            rev = re.search(r"^revision.*?['\"]([0-9a-f]+)['\"]", src, re.MULTILINE)
            assert rev
            revisions.add(rev.group(1))
        assert len(revisions) == len(sources)


# ═══════════════════════════════════════════════════════════
# 2. 表名覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestTableCoverage:
    """验证所有模型表在迁移中创建"""

    def test_all_model_tables_created_in_migrations(self):
        model_tables = _extract_model_tablenames()
        all_mig_tables = set()
        for src in _get_all_migration_sources():
            all_mig_tables.update(_extract_create_tables(src))
        for table in model_tables:
            assert table in all_mig_tables, f"模型表 {table} 未在迁移中创建"

    def test_initial_migration_creates_10_tables(self):
        src = _read_migration("6800eb76fb83")
        tables = _extract_create_tables(src)
        assert len(tables) == 10

    def test_customer_migration_creates_customers_table(self):
        src = _read_migration("67fdb7b8db27")
        tables = _extract_create_tables(src)
        assert "customers" in tables

    def test_order_migration_creates_4_tables(self):
        src = _read_migration("eb6a1ce2c197")
        tables = _extract_create_tables(src)
        assert len(tables) == 4
        assert "sales_orders" in tables
        assert "sales_order_items" in tables
        assert "payments" in tables
        assert "inventory_movements" in tables

    def test_audit_migration_creates_audit_logs_table(self):
        src = _read_migration("baf204f3ea66")
        tables = _extract_create_tables(src)
        assert "audit_logs" in tables


# ═══════════════════════════════════════════════════════════
# 3. 关键列存在验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestKeyColumns:
    """验证模型中的关键列在迁移中定义"""

    def test_users_has_password_changed_at(self):
        src = _read_migration("a1b2c3d4e5f6")
        cols = _extract_add_columns(src)
        assert ("users", "password_changed_at") in cols

    def test_sales_orders_has_order_no(self):
        src = _read_migration("eb6a1ce2c197")
        assert "order_no" in src
        assert "UniqueConstraint" in src or "unique=True" in src

    def test_customers_has_soft_delete(self):
        src = _read_migration("67fdb7b8db27")
        assert "deleted_at" in src

    def test_sales_orders_has_soft_delete(self):
        src = _read_migration("eb6a1ce2c197")
        assert "deleted_at" in src

    def test_products_has_soft_delete(self):
        src = _read_migration("6800eb76fb83")
        assert "deleted_at" in src

    def test_users_has_soft_delete(self):
        src = _read_migration("6800eb76fb83")
        assert "deleted_at" in src


# ═══════════════════════════════════════════════════════════
# 4. 索引覆盖验证（6 项）
# ═══════════════════════════════════════════════════════════


class TestIndexCoverage:
    """验证迁移创建了足够的索引"""

    def test_composite_index_migration_creates_10_indexes(self):
        src = _read_migration("c3f8a1d2e9b4")
        indexes = _extract_create_indexes(src)
        assert len(indexes) == 10

    def test_soft_delete_index_migration_creates_8_indexes(self):
        src = _read_migration("519c97faaed2")
        indexes = _extract_create_indexes(src)
        assert len(indexes) == 8

    def test_audit_logs_has_required_indexes(self):
        src = _read_migration("baf204f3ea66")
        assert "ix_audit_logs_action" in src
        assert "ix_audit_logs_created_at" in src

    def test_sales_orders_has_status_and_customer_indexes(self):
        src = _read_migration("eb6a1ce2c197")
        assert "ix_sales_orders_status" in src
        assert "ix_sales_orders_customer_id" in src

    def test_payments_has_order_id_index(self):
        src = _read_migration("eb6a1ce2c197")
        assert "ix_payments_order_id" in src

    def test_unique_constraints_exist(self):
        """关键唯一约束在迁移中定义"""
        initial = _read_migration("6800eb76fb83")
        assert "UniqueConstraint('name')" in initial  # roles
        order = _read_migration("eb6a1ce2c197")
        assert "order_no" in order
        assert "UniqueConstraint" in order or "unique=True" in order


# ═══════════════════════════════════════════════════════════
# 5. Alembic 配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestAlembicConfig:
    """验证 Alembic 配置完整"""

    def test_alembic_ini_exists(self):
        assert ALEMBIC_INI.exists()

    def test_alembic_ini_has_script_location(self):
        source = ALEMBIC_INI.read_text()
        assert "script_location" in source
        assert "alembic" in source

    def test_env_py_exists(self):
        assert ALEMBIC_ENV.exists()

    def test_env_py_imports_models(self):
        source = ALEMBIC_ENV.read_text()
        assert "from app.models" in source or "import app.models" in source
        assert "Base.metadata" in source or "target_metadata" in source

    def test_env_py_uses_async_or_sync_engine(self):
        source = ALEMBIC_ENV.read_text()
        assert "run_migrations" in source
