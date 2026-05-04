"""Alembic 迁移链完整性测试 — 验证迁移版本链连续、无分支、upgrade 可执行"""

import os
import re


def _get_versions_dir():
    return os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")


def _parse_migration_file(filepath: str) -> dict:
    """从迁移文件提取 revision, down_revision, docstring"""
    with open(filepath) as f:
        content = f.read()
    # 匹配 revision = 'xxx' 或 revision: str = 'xxx'
    revision_match = re.search(r"^revision\s*[=:].*?['\"](\w+)['\"]", content, re.MULTILINE)
    # 匹配 down_revision = 'xxx' 或 down_revision: Union[str, None] = 'xxx'
    down_match = re.search(r"^down_revision\s*[=:].*?['\"](\w+)['\"]", content, re.MULTILINE)
    # 如果没有引号包裹的值，检查是否为 None
    down_is_none = bool(re.search(r"^down_revision\s*[=:].*?\bNone\s*$", content, re.MULTILINE))
    doc_match = re.search(r'^"""(.+?)"""', content, re.MULTILINE | re.DOTALL)

    revision = revision_match.group(1) if revision_match else None
    down_revision = None if down_is_none else (down_match.group(1) if down_match else None)
    docstring = doc_match.group(1).strip() if doc_match else ""

    return {
        "file": os.path.basename(filepath),
        "revision": revision,
        "down_revision": down_revision,
        "docstring": docstring,
    }


def _get_all_migrations():
    """获取所有迁移文件信息"""
    versions_dir = _get_versions_dir()
    migrations = []
    for fname in os.listdir(versions_dir):
        if fname.startswith("__") or not fname.endswith(".py"):
            continue
        filepath = os.path.join(versions_dir, fname)
        info = _parse_migration_file(filepath)
        if info["revision"]:
            migrations.append(info)
    return migrations


# ═══════════════════════════════════════════════════════
# 1. 迁移文件基础完整性
# ═══════════════════════════════════════════════════════


class TestMigrationFiles:
    def test_migration_count(self):
        """迁移文件数量为 8"""
        migrations = _get_all_migrations()
        assert len(migrations) == 8

    def test_all_have_revision(self):
        """所有迁移文件都有 revision ID"""
        for m in _get_all_migrations():
            assert m["revision"] is not None, f"{m['file']} 缺少 revision"
            assert len(m["revision"]) == 12, f"{m['file']} revision 长度异常: {m['revision']}"

    def test_all_have_docstring(self):
        """所有迁移文件都有中文描述"""
        for m in _get_all_migrations():
            assert len(m["docstring"]) > 0, f"{m['file']} 缺少 docstring"

    def test_all_have_upgrade_function(self):
        """所有迁移文件包含 upgrade 函数"""
        versions_dir = _get_versions_dir()
        for fname in os.listdir(versions_dir):
            if fname.startswith("__") or not fname.endswith(".py"):
                continue
            with open(os.path.join(versions_dir, fname)) as f:
                content = f.read()
            assert "def upgrade()" in content, f"{fname} 缺少 upgrade()"

    def test_all_have_downgrade_function(self):
        """所有迁移文件包含 downgrade 函数"""
        versions_dir = _get_versions_dir()
        for fname in os.listdir(versions_dir):
            if fname.startswith("__") or not fname.endswith(".py"):
                continue
            with open(os.path.join(versions_dir, fname)) as f:
                content = f.read()
            assert "def downgrade()" in content, f"{fname} 缺少 downgrade()"


# ═══════════════════════════════════════════════════════
# 2. 迁移链连续性
# ═══════════════════════════════════════════════════════


class TestMigrationChain:
    def test_single_root(self):
        """只有一个根迁移（down_revision=None）"""
        roots = [m for m in _get_all_migrations() if m["down_revision"] is None]
        assert len(roots) == 1, f"存在多个根迁移: {[r['revision'] for r in roots]}"
        assert roots[0]["revision"] == "6800eb76fb83"

    def test_single_head(self):
        """只有一个头迁移（不被任何迁移引用）"""
        migrations = _get_all_migrations()
        all_downs = {m["down_revision"] for m in migrations if m["down_revision"]}
        heads = [m for m in migrations if m["revision"] not in all_downs]
        assert len(heads) == 1, f"存在多个头迁移: {[h['revision'] for h in heads]}"
        assert heads[0]["revision"] == "b2c3d4e5f6a7"

    def test_no_orphan_down_revisions(self):
        """所有 down_revision 都指向存在的 revision"""
        migrations = _get_all_migrations()
        revisions = {m["revision"] for m in migrations}
        for m in migrations:
            if m["down_revision"]:
                assert m["down_revision"] in revisions, (
                    f"{m['file']} 的 down_revision {m['down_revision']} 不存在"
                )

    def test_no_duplicate_revisions(self):
        """没有重复的 revision ID"""
        revisions = [m["revision"] for m in _get_all_migrations()]
        assert len(revisions) == len(set(revisions)), "存在重复的 revision ID"

    def test_chain_is_linear(self):
        """迁移链是线性的（每个节点最多一个前驱一个后继）"""
        migrations = _get_all_migrations()
        down_counts: dict[str, int] = {}
        for m in migrations:
            if m["down_revision"]:
                down_counts[m["down_revision"]] = down_counts.get(m["down_revision"], 0) + 1
        for rev, count in down_counts.items():
            assert count == 1, f"revision {rev} 被多个迁移引用（分支）"

    def test_full_chain_length(self):
        """完整链长度为 7（从头到尾遍历）"""
        migrations = _get_all_migrations()
        by_down = {m["down_revision"]: m for m in migrations if m["down_revision"]}
        root = next(m for m in migrations if m["down_revision"] is None)
        chain = [root["revision"]]
        current = root["revision"]
        while current in by_down:
            current = by_down[current]["revision"]
            chain.append(current)
        assert len(chain) == 8, f"链长度 {len(chain)}，预期 8"
        assert chain[-1] == "b2c3d4e5f6a7"

    def test_expected_chain_order(self):
        """迁移链顺序符合预期"""
        expected = [
            "6800eb76fb83",
            "67fdb7b8db27",
            "eb6a1ce2c197",
            "baf204f3ea66",
            "c3f8a1d2e9b4",
            "519c97faaed2",
            "a1b2c3d4e5f6",
            "b2c3d4e5f6a7",
        ]
        migrations = _get_all_migrations()
        by_down = {m["down_revision"]: m for m in migrations if m["down_revision"]}
        root = next(m for m in migrations if m["down_revision"] is None)
        chain = [root["revision"]]
        current = root["revision"]
        while current in by_down:
            current = by_down[current]["revision"]
            chain.append(current)
        assert chain == expected


# ═══════════════════════════════════════════════════════
# 3. alembic.ini 和 env.py 基础检查
# ═══════════════════════════════════════════════════════


class TestAlembicConfig:
    def test_alembic_ini_exists(self):
        """alembic.ini 存在"""
        ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        assert os.path.exists(ini_path)

    def test_env_py_exists(self):
        """alembic/env.py 存在"""
        env_path = os.path.join(os.path.dirname(__file__), "..", "alembic", "env.py")
        assert os.path.exists(env_path)

    def test_versions_dir_exists(self):
        """alembic/versions/ 目录存在"""
        assert os.path.isdir(_get_versions_dir())

    def test_script_py_template_exists(self):
        """alembic/script.py.mako 模板存在"""
        template = os.path.join(os.path.dirname(__file__), "..", "alembic", "script.py.mako")
        assert os.path.exists(template)
