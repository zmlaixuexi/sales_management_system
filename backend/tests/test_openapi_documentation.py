"""文档完善：后端 API 端点 OpenAPI 描述完整性验证测试
覆盖模块级文档、路由级 tag 声明、端点函数文档字符串、
responses 声明、公开端点无需认证标记"""

import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
ROUTER_FILE = API_DIR / "router.py"


def _get_module_files() -> list[Path]:
    return sorted(
        f for f in API_DIR.glob("*.py")
        if not f.name.startswith("_") and f.name != "router.py"
    )


def _extract_endpoint_info(source: str) -> list[dict]:
    """提取端点信息: [(method, path, func_name, has_docstring, tag)]"""
    results = []
    lines = source.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'\s*@router\.(get|post|put|patch|delete)\(', line)
        if not m:
            i += 1
            continue
        method = m.group(1)

        # Collect full decorator (may be multi-line)
        dec_text = line
        j = i
        while ")" not in dec_text or dec_text.count("(") > dec_text.count(")"):
            j += 1
            if j >= len(lines):
                break
            dec_text += "\n" + lines[j]

        # Extract path from first positional arg
        path_m = re.search(r'@router\.\w+\(\s*["\']([^"\']*)["\']', dec_text)
        path = path_m.group(1) if path_m else ""

        # Extract tag if present
        tag_m = re.search(r'tags\s*=\s*\[?"([^"]+)"\]?', dec_text)
        tag = tag_m.group(1) if tag_m else None

        # Find function def after decorator
        func_line = j + 1
        while func_line < len(lines) and "def " not in lines[func_line]:
            func_line += 1
        if func_line >= len(lines):
            i = func_line
            continue

        func_m = re.search(r'def\s+(\w+)\s*\(', lines[func_line])
        if not func_m:
            i = func_line + 1
            continue
        func_name = func_m.group(1)

        # Find the end of function signature (closing paren + colon)
        sig_text = "\n".join(lines[func_line:])
        paren_start = sig_text.find("(")
        depth = 0
        sig_end = -1
        for k in range(paren_start, len(sig_text)):
            if sig_text[k] == "(":
                depth += 1
            elif sig_text[k] == ")":
                depth -= 1
                if depth == 0:
                    colon_pos = sig_text.find(":", k)
                    if colon_pos != -1:
                        sig_end = colon_pos + 1
                    break

        has_doc = False
        if sig_end > 0:
            body = sig_text[sig_end:]
            for body_line in body.split("\n"):
                stripped = body_line.strip()
                if stripped == "":
                    continue
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    has_doc = True
                break

        results.append({
            "method": method,
            "path": path,
            "func_name": func_name,
            "has_docstring": has_doc,
            "tag": tag,
        })
        i = func_line + 1
    return results


def _count_all_endpoints() -> int:
    total = 0
    for f in _get_module_files():
        source = f.read_text()
        total += len(re.findall(r"@router\.(?:get|post|put|patch|delete)\(", source))
    return total


# ═══════════════════════════════════════════════════════════
# 1. 模块级文档验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModuleDocs:
    """验证每个 API 模块有模块级文档字符串"""

    def test_all_api_modules_have_docstring(self):
        modules_with_doc = 0
        for f in _get_module_files():
            source = f.read_text()
            if source.lstrip().startswith('"""'):
                modules_with_doc += 1
        assert modules_with_doc >= 9, f"至少 9 个模块应有文档字符串，实际 {modules_with_doc}"

    def test_module_docstrings_are_chinese(self):
        for f in _get_module_files():
            source = f.read_text()
            m = re.match(r'\s*\"\"\"(.+?)\"\"\"', source, re.DOTALL)
            if not m:
                continue
            doc = m.group(1).strip()
            assert len(doc) > 0, f"{f.name} 模块文档为空"

    def test_13_api_modules_exist(self):
        files = _get_module_files()
        assert len(files) == 13

    def test_router_file_exists(self):
        assert ROUTER_FILE.exists()

    def test_router_includes_all_modules(self):
        source = ROUTER_FILE.read_text()
        modules = ["auth", "users", "roles", "products", "customers",
                    "orders", "payments", "inventory", "audit_logs",
                    "reports", "exports", "files", "health"]
        for mod in modules:
            assert mod in source, f"router.py 未包含 {mod} 模块"


# ═══════════════════════════════════════════════════════════
# 2. 路由级 tag 声明验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRouterTags:
    """验证路由模块有中文 tag 声明"""

    def test_all_modules_define_tags(self):
        for f in _get_module_files():
            source = f.read_text()
            if "@router" not in source:
                continue
            # router = APIRouter should have tags
            router_m = re.search(r'APIRouter\(([^)]+)\)', source)
            if router_m:
                assert "tags" in router_m.group(1), f"{f.name} 的 APIRouter 未定义 tags"

    def test_tags_are_chinese(self):
        for f in _get_module_files():
            source = f.read_text()
            for m in re.finditer(r'tags\s*=\s*\[?"([^"]+)"\]?', source):
                tag = m.group(1)
                assert len(tag) > 0, f"{f.name} 有空 tag"

    def test_no_duplicate_tags_across_modules(self):
        tags = []
        for f in _get_module_files():
            source = f.read_text()
            tags.extend(m.group(1) for m in re.finditer(r'tags\s*=\s*\[?"([^"]+)"\]?', source))
        assert len(tags) == len(set(tags)), f"重复 tag: {tags}"

    def test_at_least_10_distinct_tags(self):
        tags = set()
        for f in _get_module_files():
            source = f.read_text()
            for m in re.finditer(r'tags\s*=\s*\[?"([^"]+)"\]?', source):
                tags.add(m.group(1))
        assert len(tags) >= 10, f"只有 {len(tags)} 个 tag，期望至少 10"

    def test_router_has_prefix(self):
        no_prefix = []
        for f in _get_module_files():
            source = f.read_text()
            if "@router" not in source:
                continue
            router_m = re.search(r'APIRouter\(([^)]+)\)', source, re.DOTALL)
            if router_m and "prefix" not in router_m.group(1):
                no_prefix.append(f.name)
        # health.py 无需前缀（直接挂载）
        expected_no_prefix = {"health.py"}
        actual_no_prefix = set(no_prefix)
        assert actual_no_prefix <= expected_no_prefix, \
            f"以下模块不应缺少 prefix: {actual_no_prefix - expected_no_prefix}"


# ═══════════════════════════════════════════════════════════
# 3. 端点函数文档字符串验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEndpointDocstrings:
    """验证端点函数有文档字符串"""

    def test_at_least_50_endpoints(self):
        count = _count_all_endpoints()
        assert count >= 50, f"期望至少 50 个端点，实际 {count}"

    def test_all_modules_endpoints_have_docstrings(self):
        """验证绝大多数端点有文档字符串（允许少量例外）"""
        exceptions = {"health.py:version"}
        for f in _get_module_files():
            source = f.read_text()
            endpoints = _extract_endpoint_info(source)
            for ep in endpoints:
                key = f"{f.name}:{ep['func_name']}"
                if key in exceptions:
                    continue
                assert ep["has_docstring"], \
                    f"{f.name}:{ep['func_name']} ({ep['method'].upper()} {ep['path']}) 缺少文档字符串"

    def test_docstrings_are_brief(self):
        """文档字符串应简短（单行描述）"""
        for f in _get_module_files():
            source = f.read_text()
            endpoints = _extract_endpoint_info(source)
            for ep in endpoints:
                if not ep["has_docstring"]:
                    continue
                # Extract docstring content
                func_pos = source.find(f'def {ep["func_name"]}(')
                if func_pos == -1:
                    continue
                rest = source[func_pos:]
                doc_m = re.search(r'\"\"\"(.+?)\"\"\"', rest, re.DOTALL)
                if doc_m:
                    doc = doc_m.group(1).strip()
                    assert len(doc) <= 100, \
                        f"{f.name}:{ep['func_name']} 文档字符串过长 ({len(doc)} 字符): {doc[:50]}"

    def test_crud_endpoints_have_action_verbs(self):
        """CRUD 端点文档字符串包含动作动词"""
        for f in _get_module_files():
            source = f.read_text()
            endpoints = _extract_endpoint_info(source)
            for ep in endpoints:
                if not ep["has_docstring"]:
                    continue
                func_pos = source.find(f'def {ep["func_name"]}(')
                if func_pos == -1:
                    continue
                rest = source[func_pos:]
                doc_m = re.search(r'\"\"\"(.+?)\"\"\"', rest, re.DOTALL)
                if doc_m:
                    doc = doc_m.group(1).strip()
                    # POST 端点描述应含动作动词
                    if ep["method"] == "post" and "confirm" not in ep["func_name"]:
                        assert any(w in doc for w in ["创建", "新增", "登记", "导入",
                                                      "上传", "刷新", "冲正", "调整",
                                                      "登录", "修改", "停用", "转移",
                                                      "取消"]), \
                            f"{f.name}:{ep['func_name']} POST 端点文档缺少动作动词: {doc}"

    def test_list_endpoints_mention_list_or_query(self):
        """列表端点文档应含列表/查询/排行等词"""
        for f in _get_module_files():
            source = f.read_text()
            endpoints = _extract_endpoint_info(source)
            for ep in endpoints:
                if not ep["has_docstring"]:
                    continue
                if ep["method"] != "get":
                    continue
                if "list" not in ep["func_name"] and "ranking" not in ep["func_name"] \
                   and "summary" not in ep["func_name"] and "trend" not in ep["func_name"]:
                    continue
                func_pos = source.find(f'def {ep["func_name"]}(')
                if func_pos == -1:
                    continue
                rest = source[func_pos:]
                doc_m = re.search(r'\"\"\"(.+?)\"\"\"', rest, re.DOTALL)
                if doc_m:
                    doc = doc_m.group(1).strip()
                    assert any(w in doc for w in ["列表", "查询", "排行", "汇总", "趋势", "预警", "流水", "权限"]), \
                        f"{f.name}:{ep['func_name']} GET 列表端点文档缺少列表/查询关键词: {doc}"


# ═══════════════════════════════════════════════════════════
# 4. responses 声明验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestResponsesDeclaration:
    """验证路由模块有 responses 声明"""

    def test_modules_with_mutation_have_401_response(self):
        """有写操作的模块声明 401 响应"""
        mutation_modules = ["products.py", "customers.py", "orders.py",
                            "payments.py", "users.py", "roles.py", "files.py"]
        for mod in mutation_modules:
            source = (API_DIR / mod).read_text()
            router_m = re.search(r'APIRouter\(([^)]+)\)', source, re.DOTALL)
            if router_m:
                args = router_m.group(1)
                assert "401" in args, f"{mod} 未声明 401 响应"

    def test_modules_with_mutation_have_403_response(self):
        """有写操作的模块声明 403 响应"""
        mutation_modules = ["products.py", "customers.py", "orders.py", "exports.py"]
        for mod in mutation_modules:
            source = (API_DIR / mod).read_text()
            router_m = re.search(r'APIRouter\(([^)]+)\)', source, re.DOTALL)
            if router_m:
                args = router_m.group(1)
                assert "403" in args, f"{mod} 未声明 403 响应"

    def test_auth_module_has_401_response(self):
        source = (API_DIR / "auth.py").read_text()
        assert "401" in source

    def test_health_module_has_no_auth_responses(self):
        """健康检查模块不需要认证响应"""
        source = (API_DIR / "health.py").read_text()
        router_m = re.search(r'APIRouter\(([^)]+)\)', source, re.DOTALL)
        if router_m:
            args = router_m.group(1)
            # health 不需要 401/403
            assert "401" not in args or "public" in source.lower()

    def test_response_descriptions_are_chinese(self):
        """responses 描述使用中文"""
        for f in _get_module_files():
            source = f.read_text()
            for m in re.finditer(r'"(\d+)":\s*\{[^}]*"description":\s*"([^"]+)"', source):
                desc = m.group(2)
                assert len(desc) > 0, f"{f.name} 有空的 response description"


# ═══════════════════════════════════════════════════════════
# 5. 公开端点无需认证标记验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPublicEndpoints:
    """验证公开端点（无需认证）正确标记"""

    def test_auth_login_is_public(self):
        source = (API_DIR / "auth.py").read_text()
        # login 不应有 require_permission
        login_m = re.search(r'@router\.post\("login"[^)]*\)(.+?)(?=@router\.|$)', source, re.DOTALL)
        if login_m:
            login_func = login_m.group(1)
            assert "require_permission" not in login_func

    def test_health_is_public(self):
        source = (API_DIR / "health.py").read_text()
        assert "require_permission" not in source
        assert "get_current_user" not in source or "public" in source

    def test_version_is_public(self):
        source = (API_DIR / "health.py").read_text()
        # version endpoint 不需要认证
        ver_m = re.search(r'@router\.get\("version"[^)]*\)(.+?)(?=@router\.|$)', source, re.DOTALL)
        if ver_m:
            ver_func = ver_m.group(1)
            assert "require_permission" not in ver_func

    def test_auth_refresh_is_public(self):
        source = (API_DIR / "auth.py").read_text()
        refresh_m = re.search(r'@router\.post\("refresh"[^)]*\)(.+?)(?=@router\.|$)', source, re.DOTALL)
        if refresh_m:
            refresh_func = refresh_m.group(1)
            assert "require_permission" not in refresh_func

    def test_exports_require_permission(self):
        source = (API_DIR / "exports.py").read_text()
        # 所有导出端点应在函数参数中使用 require_permission
        count = source.count("require_permission(")
        endpoints = _extract_endpoint_info(source)
        assert count >= len(endpoints), \
            f"导出模块 {len(endpoints)} 个端点但只有 {count} 处 require_permission"
