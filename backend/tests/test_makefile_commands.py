"""部署体验：Makefile 命令完整性验证测试
覆盖命令定义完整性、命令引用文件存在性、
命令分类覆盖、help 目标、PHONY 声明"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MAKEFILE = ROOT / "Makefile"


def _read() -> str:
    return MAKEFILE.read_text()


def _get_targets(source: str) -> list[str]:
    """提取所有 Makefile target 名称"""
    targets = []
    for line in source.splitlines():
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*:", line)
        if m:
            targets.append(m.group(1))
    return targets


def _get_documented_targets(source: str) -> list[str]:
    """提取有 ## 注释的 target"""
    targets = []
    for line in source.splitlines():
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*:.*?##\s+(.+)", line)
        if m:
            targets.append((m.group(1), m.group(2).strip()))
    return targets


# ═══════════════════════════════════════════════════════════
# 1. 命令定义完整性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCommandDefinition:
    """验证 Makefile 包含所有必需命令"""

    def test_has_all_essential_targets(self):
        src = _read()
        required = [
            "dev", "dev-backend", "dev-frontend",
            "test", "test-backend", "test-frontend",
            "lint", "lint-backend", "lint-frontend",
            "build", "build-frontend",
            "install", "help", "clean",
        ]
        targets = _get_targets(src)
        for req in required:
            assert req in targets, f"缺少必需 target: {req}"

    def test_has_database_targets(self):
        src = _read()
        targets = _get_targets(src)
        for req in ["db-migrate", "db-check", "db-seed", "db-backup", "db-restore"]:
            assert req in targets, f"缺少数据库 target: {req}"

    def test_has_docker_targets(self):
        src = _read()
        targets = _get_targets(src)
        for req in ["docker-up", "docker-down", "docker-dev", "docker-dev-down", "docker-logs"]:
            assert req in targets, f"缺少 Docker target: {req}"

    def test_has_quality_targets(self):
        src = _read()
        targets = _get_targets(src)
        for req in ["typecheck", "typecheck-backend", "typecheck-frontend", "quality", "ci", "coverage", "coverage-frontend"]:
            assert req in targets, f"缺少质量检查 target: {req}"

    def test_has_deploy_targets(self):
        src = _read()
        targets = _get_targets(src)
        for req in ["deploy-check", "deploy-rollback", "audit"]:
            assert req in targets, f"缺少部署 target: {req}"


# ═══════════════════════════════════════════════════════════
# 2. 命令引用文件存在性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestReferencedFilesExist:
    """验证 Makefile 中引用的文件和脚本实际存在"""

    def test_docker_compose_files_exist(self):
        src = _read()
        compose_refs = re.findall(r"docker-compose\.\S+\.yml", src)
        for ref in compose_refs:
            path = ROOT / "deploy" / ref
            assert path.exists(), f"引用的 compose 文件不存在: deploy/{ref}"

    def test_deploy_scripts_exist(self):
        src = _read()
        script_refs = re.findall(r"bash\s+deploy/(\S+\.sh)", src)
        for ref in script_refs:
            path = ROOT / "deploy" / ref
            assert path.exists(), f"引用的部署脚本不存在: deploy/{ref}"

    def test_python_commands_reference_valid_modules(self):
        src = _read()
        # 验证 $(PYTHON) -m 引用有效
        py_mods = re.findall(r"\$\(PYTHON\)\s+-m\s+(\S+)", src)
        for mod in py_mods:
            parts = mod.split(".")
            if parts[0] == "app":
                mod_path = ROOT / "backend" / Path(*parts)
                # 可能是包（__init__.py）或模块（.py）
                assert mod_path.with_suffix(".py").exists() or (mod_path / "__init__.py").exists(), (
                    f"引用的 Python 模块不存在: backend/{'/'.join(parts)}"
                )

    def test_frontend_npm_commands_are_valid(self):
        src = _read()
        npm_cmds = re.findall(r"npm\s+(run\s+)?(\w+)", src)
        # 读取 package.json scripts
        pkg = (ROOT / "frontend" / "package.json").read_text()
        pkg_scripts = re.findall(r'"(\w+)"\s*:', pkg)
        for _, cmd in npm_cmds:
            if cmd in ("install", "audit"):
                continue
            assert cmd in pkg_scripts, f"npm script '{cmd}' 不在 frontend/package.json 中"

    def test_alembic_command_available(self):
        src = _read()
        assert "alembic" in src
        alembic_ini = ROOT / "backend" / "alembic.ini"
        assert alembic_ini.exists(), "backend/alembic.ini 不存在"


# ═══════════════════════════════════════════════════════════
# 3. 命令分类覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestCommandCategorization:
    """验证 Makefile 命令按功能分类组织"""

    def test_has_section_markers(self):
        src = _read()
        sections = ["开发", "安装", "测试", "构建", "数据库", "Docker", "安全", "部署", "清理", "代码质量"]
        for section in sections:
            assert section in src, f"缺少分类标记: {section}"

    def test_aggregate_targets_depend_on_correct_prerequisites(self):
        src = _read()
        # test 应依赖 test-backend 和 test-frontend
        test_line = re.search(r"^test:\s+(.+)", src, re.MULTILINE)
        assert test_line, "缺少 test target"
        deps = test_line.group(1)
        assert "test-backend" in deps
        assert "test-frontend" in deps

    def test_quality_target_includes_lint_typecheck_test(self):
        src = _read()
        quality_line = re.search(r"^quality:\s+(.+)", src, re.MULTILINE)
        assert quality_line, "缺少 quality target"
        deps = quality_line.group(1)
        assert "lint" in deps
        assert "typecheck" in deps
        assert "test" in deps

    def test_build_target_includes_lint_test_build_frontend(self):
        src = _read()
        build_line = re.search(r"^build:\s+(.+)", src, re.MULTILINE)
        assert build_line, "缺少 build target"
        deps = build_line.group(1)
        assert "lint" in deps
        assert "test" in deps
        assert "build-frontend" in deps

    def test_ci_target_covers_full_pipeline(self):
        src = _read()
        ci_line = re.search(r"^ci:\s+(.+)", src, re.MULTILINE)
        assert ci_line, "缺少 ci target"
        deps = ci_line.group(1)
        for req in ["lint-backend", "lint-frontend", "typecheck", "coverage", "coverage-frontend", "build-frontend"]:
            assert req in deps, f"ci target 缺少 {req}"


# ═══════════════════════════════════════════════════════════
# 4. help 目标验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestHelpTarget:
    """验证 help 目标和文档注释"""

    def test_help_target_exists(self):
        src = _read()
        targets = _get_targets(src)
        assert "help" in targets

    def test_help_uses_grep_pattern(self):
        src = _read()
        help_body = _find_target_body(src, "help")
        assert "grep" in help_body
        assert "##" in help_body

    def test_all_targets_have_help_comments(self):
        src = _read()
        documented = _get_documented_targets(src)
        all_targets = _get_targets(src)
        doc_names = {name for name, _ in documented}
        for target in all_targets:
            assert target in doc_names, f"target '{target}' 缺少 ## 帮助注释"

    def test_help_comments_are_chinese(self):
        src = _read()
        documented = _get_documented_targets(src)
        for name, desc in documented:
            has_chinese = bool(re.search(r"[一-鿿]", desc))
            assert has_chinese, f"target '{name}' 的帮助注释应包含中文描述: {desc}"

    def test_help_comments_are_descriptive(self):
        src = _read()
        documented = _get_documented_targets(src)
        for name, desc in documented:
            assert len(desc) >= 4, f"target '{name}' 的帮助注释太短: {desc}"


# ═══════════════════════════════════════════════════════════
# 5. PHONY 声明与 Makefile 规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMakefileConventions:
    """验证 Makefile 规范"""

    def test_phony_declaration_exists(self):
        src = _read()
        assert ".PHONY:" in src, "缺少 .PHONY 声明"

    def test_all_targets_are_phony(self):
        src = _read()
        targets = _get_targets(src)
        phony_match = re.search(r"\.PHONY:\s*(.+)", src)
        assert phony_match, "缺少 .PHONY 声明"
        phony_targets = set(phony_match.group(1).split())
        for target in targets:
            assert target in phony_targets, f"target '{target}' 未在 .PHONY 中声明"

    def test_uses_cd_for_subdirectory_commands(self):
        src = _read()
        # 后端命令应 cd backend
        backend_targets = ["test-backend", "lint-backend", "coverage", "db-migrate"]
        for target in backend_targets:
            body = _find_target_body(src, target)
            assert "cd backend" in body, f"{target} 应使用 cd backend"

    def test_uses_python_variable(self):
        src = _read()
        assert "$(PYTHON)" in src, "应使用 $(PYTHON) 变量"
        assert "PYTHON ?=" in src, "应定义 PYTHON 变量"
        # 回退逻辑
        assert ".venv/bin/python" in src, "PYTHON 变量应支持 venv 回退"

    def test_makefile_has_no_tabs_in_recipe_lines(self):
        """验证 recipe 行使用 tab 缩进"""
        src = _read()
        lines = src.splitlines()
        in_recipe = False
        for i, line in enumerate(lines, 1):
            if re.match(r"^[a-zA-Z].*:", line):
                in_recipe = True
                continue
            if in_recipe and line and not line.startswith("\t") and not line.startswith("#"):
                # 允许空行和变量定义
                if not re.match(r"^[A-Z_]+\s*[:?]?=", line):
                    assert False, f"第 {i} 行 recipe 应使用 tab 缩进: {line!r}"
            if in_recipe and not line:
                in_recipe = False


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════


def _find_target_body(source: str, target: str) -> str:
    """提取 target 的 recipe 内容"""
    pattern = re.compile(rf"^{re.escape(target)}\s*:.*$", re.MULTILINE)
    match = pattern.search(source)
    if not match:
        return ""
    lines = source.splitlines()
    start_line = match.start()
    # 找到该行的行号
    pos = 0
    for i, line in enumerate(lines):
        if pos >= start_line:
            start_idx = i
            break
        pos += len(line) + 1
    else:
        return ""
    # 收集 tab 开头的行
    recipe_lines = []
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("\t"):
            recipe_lines.append(lines[j])
        elif lines[j].strip() == "":
            continue
        else:
            break
    return "\n".join(recipe_lines)
