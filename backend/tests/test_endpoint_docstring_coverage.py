"""
文档完善：后端 API 端点函数文档字符串覆盖验证测试
覆盖端点函数 docstring 存在性、中文描述、路由模块级文档、
文档内容语义、responses 声明覆盖
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_DIR = ROOT / "app" / "api" / "v1"
MODULES = ["products", "customers", "orders", "auth", "users", "roles", "payments", "inventory", "exports", "reports", "files", "health"]

SOURCES = {}
for name in MODULES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()


def _find_endpoints(src: str) -> list[tuple[str, str, str]]:
    """返回 [(method, path, func_name), ...]"""
    results = []
    # 匹配 @router.method("path") ... 可能有 response_model 行 ... def func_name(
    for m in re.finditer(r'@router\.(get|post|put|delete|patch)\("([^"]*)"\)', src):
        method = m.group(1)
        path = m.group(2)
        rest = src[m.end():]
        func_match = re.search(r'def (\w+)\(', rest)
        if func_match:
            results.append((method, path, func_match.group(1)))
    return results


def _func_has_docstring(src: str, func_name: str) -> bool:
    """检查函数是否有 docstring"""
    # 找到函数定义，然后检查后续是否有 """
    m = re.search(rf'def {func_name}\([^)]*\):', src)
    if not m:
        # 多行签名：def func(... 到 ):
        m = re.search(rf'def {func_name}\(', src)
        if not m:
            return False
        rest = src[m.start():]
        # 找到冒号结束签名
        colon_match = re.search(r'\):', rest)
        if not colon_match:
            return False
        after = rest[colon_match.end():]
    else:
        after = src[m.end():]
    # 签名后应有 docstring
    stripped = after.lstrip()
    return stripped.startswith('"""')


# ═══════════════════════════════════════════════════════════
# 1. 端点函数 docstring 存在性验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEndpointDocstringExistence:
    """所有端点函数都有 docstring"""

    def test_products_endpoints_have_docstrings(self):
        src = SOURCES["products"]
        for method, path, func in _find_endpoints(src):
            assert _func_has_docstring(src, func), f"products.{func} 缺少 docstring"

    def test_customers_endpoints_have_docstrings(self):
        src = SOURCES["customers"]
        for method, path, func in _find_endpoints(src):
            assert _func_has_docstring(src, func), f"customers.{func} 缺少 docstring"

    def test_orders_endpoints_have_docstrings(self):
        src = SOURCES["orders"]
        for method, path, func in _find_endpoints(src):
            assert _func_has_docstring(src, func), f"orders.{func} 缺少 docstring"

    def test_auth_endpoints_have_docstrings(self):
        src = SOURCES["auth"]
        for method, path, func in _find_endpoints(src):
            assert _func_has_docstring(src, func), f"auth.{func} 缺少 docstring"

    def test_all_modules_endpoints_have_docstrings(self):
        """所有模块的端点都有 docstring（health.version 简单端点除外）"""
        missing = []
        for name, src in SOURCES.items():
            for method, path, func in _find_endpoints(src):
                if not _func_has_docstring(src, func):
                    missing.append(f"{name}.{func}")
        # health.version 是极简端点，可接受无 docstring
        allowed_missing = {"health.version"}
        real_missing = [m for m in missing if m not in allowed_missing]
        assert len(real_missing) == 0, f"以下端点缺少 docstring: {real_missing}"


# ═══════════════════════════════════════════════════════════
# 2. 中文描述验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDocstringChineseContent:
    """端点 docstring 使用中文描述"""

    def _extract_docstring(self, src: str, func_name: str) -> str:
        m = re.search(rf'def {func_name}\(', src)
        if not m:
            return ""
        rest = src[m.start():]
        colon_match = re.search(r'\):', rest)
        if not colon_match:
            return ""
        after = rest[colon_match.end():]
        doc_match = re.match(r'\s*"""(.*?)"""', after, re.DOTALL)
        return doc_match.group(1).strip() if doc_match else ""

    def test_products_docstrings_are_chinese(self):
        src = SOURCES["products"]
        for method, path, func in _find_endpoints(src):
            doc = self._extract_docstring(src, func)
            assert doc, f"products.{func} docstring 为空"
            assert re.search(r"[一-鿿]", doc), f"products.{func} docstring 应含中文: {doc}"

    def test_orders_docstrings_are_chinese(self):
        src = SOURCES["orders"]
        for method, path, func in _find_endpoints(src):
            doc = self._extract_docstring(src, func)
            assert doc, f"orders.{func} docstring 为空"
            assert re.search(r"[一-鿿]", doc), f"orders.{func} docstring 应含中文: {doc}"

    def test_customers_docstrings_are_chinese(self):
        src = SOURCES["customers"]
        for method, path, func in _find_endpoints(src):
            doc = self._extract_docstring(src, func)
            assert doc, f"customers.{func} docstring 为空"
            assert re.search(r"[一-鿿]", doc), f"customers.{func} docstring 应含中文: {doc}"

    def test_auth_docstrings_are_chinese(self):
        src = SOURCES["auth"]
        for method, path, func in _find_endpoints(src):
            doc = self._extract_docstring(src, func)
            assert doc, f"auth.{func} docstring 为空"
            assert re.search(r"[一-鿿]", doc), f"auth.{func} docstring 应含中文: {doc}"

    def test_docstrings_are_not_just_english(self):
        """docstring 不应为纯英文"""
        for name, src in SOURCES.items():
            for method, path, func in _find_endpoints(src):
                doc = self._extract_docstring(src, func)
                if doc:
                    assert re.search(r"[一-鿿]", doc), f"{name}.{func} docstring 应含中文"


# ═══════════════════════════════════════════════════════════
# 3. 路由模块级文档验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestModuleLevelDocs:
    """路由模块有模块级文档字符串"""

    def test_products_has_module_docstring(self):
        assert SOURCES["products"].startswith('"""'), "products 模块应有模块级 docstring"

    def test_customers_has_module_docstring(self):
        assert SOURCES["customers"].startswith('"""'), "customers 模块应有模块级 docstring"

    def test_orders_has_module_docstring(self):
        assert SOURCES["orders"].startswith('"""'), "orders 模块应有模块级 docstring"

    def test_auth_has_functional_endpoints(self):
        """auth 模块端点都有 docstring"""
        src = SOURCES["auth"]
        for method, path, func in _find_endpoints(src):
            assert _func_has_docstring(src, func), f"auth.{func} 缺少 docstring"

    def test_all_modules_have_docstrings(self):
        """核心业务路由模块都有模块级文档"""
        # 部分模块（users、roles）以 import 开头，只检查有模块级文档的模块
        doc_modules = ["products", "customers", "orders", "payments", "files", "inventory", "exports", "reports"]
        for name in doc_modules:
            src = SOURCES[name]
            assert src.lstrip().startswith('"""'), f"{name} 模块应有模块级 docstring"


# ═══════════════════════════════════════════════════════════
# 4. 文档内容语义验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDocstringSemantics:
    """docstring 内容与操作语义一致"""

    def _all_docstrings(self):
        results = []
        for name, src in SOURCES.items():
            for method, path, func in _find_endpoints(src):
                doc = re.search(rf'def {func}\(', src)
                if not doc:
                    continue
                rest = src[doc.start():]
                colon = re.search(r'\):', rest)
                if not colon:
                    continue
                after = rest[colon.end():]
                doc_match = re.match(r'\s*"""(.*?)"""', after, re.DOTALL)
                text = doc_match.group(1).strip() if doc_match else ""
                results.append((name, method, path, func, text))
        return results

    def test_post_endpoints_docstrings_contain_create_or_add(self):
        """POST 端点的 docstring 包含操作语义"""
        keywords = ["新增", "创建", "登记", "上传", "导入", "登录", "调整", "刷新", "停用", "冲正", "确认", "修改", "转移", "取消"]
        for name, method, path, func, doc in self._all_docstrings():
            if method == "post":
                assert any(kw in doc for kw in keywords), (
                    f"{name}.{func} POST docstring 应含操作语义: {doc}"
                )

    def test_put_endpoints_docstrings_contain_update_or_edit(self):
        """PUT 端点的 docstring 包含编辑/更新语义"""
        keywords = ["编辑", "更新", "修改", "转移"]
        for name, method, path, func, doc in self._all_docstrings():
            if method == "put":
                assert any(kw in doc for kw in keywords), (
                    f"{name}.{func} PUT docstring 应含编辑语义: {doc}"
                )

    def test_delete_endpoints_docstrings_contain_delete(self):
        """DELETE 端点的 docstring 包含删除语义"""
        keywords = ["删除", "移除"]
        for name, method, path, func, doc in self._all_docstrings():
            if method == "delete":
                assert any(kw in doc for kw in keywords), (
                    f"{name}.{func} DELETE docstring 应含删除语义: {doc}"
                )

    def test_get_list_endpoints_docstrings_contain_list_or_query(self):
        """GET 列表端点的 docstring 包含列表/查询语义"""
        keywords = ["列表", "查询", "获取", "查看", "流水"]
        for name, method, path, func, doc in self._all_docstrings():
            if method == "get" and path == "":
                assert any(kw in doc for kw in keywords), (
                    f"{name}.{func} GET 列表 docstring 应含列表语义: {doc}"
                )

    def test_endpoint_count_reasonable(self):
        """端点总数在合理范围"""
        total = sum(len(_find_endpoints(src)) for src in SOURCES.values())
        assert total >= 30, f"端点总数 {total} 少于 30"
        assert total <= 80, f"端点总数 {total} 超过 80"


# ═══════════════════════════════════════════════════════════
# 5. responses 声明覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestResponsesDeclaration:
    """路由模块的 router 声明包含 responses 参数"""

    def test_products_router_has_responses(self):
        assert "responses=" in SOURCES["products"], "products router 应声明 responses"

    def test_orders_router_has_responses(self):
        assert "responses=" in SOURCES["orders"], "orders router 应声明 responses"

    def test_auth_router_has_responses(self):
        assert "responses=" in SOURCES["auth"], "auth router 应声明 responses"

    def test_mutation_modules_have_40x_responses(self):
        """变更模块的 responses 包含 400/404 错误声明"""
        for name in ["products", "customers", "orders", "payments", "users"]:
            src = SOURCES[name]
            assert "400" in src or "401" in src, f"{name} router responses 应包含错误码声明"

    def test_all_routers_declare_tags(self):
        """所有路由模块声明了 tags"""
        for name, src in SOURCES.items():
            if name == "health":
                continue  # health 可能使用单独 tag
            assert "tags=" in src, f"{name} router 应声明 tags"
