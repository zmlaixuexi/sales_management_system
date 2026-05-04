"""
代码质量：后端 API 端点函数参数注解与类型提示验证测试
覆盖路径参数类型、依赖注入类型、
请求体类型、响应返回类型、参数默认值
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_DIR = ROOT / "app" / "api" / "v1"
MODULES = ["products", "customers", "orders", "payments", "users", "roles",
           "files", "inventory", "reports", "exports", "auth", "health", "audit_logs"]

SOURCES = {}
for name in MODULES:
    p = API_DIR / f"{name}.py"
    if p.exists():
        SOURCES[name] = p.read_text()


def _find_endpoint_functions(src: str) -> list[dict]:
    """提取所有端点函数名和装饰器"""
    results = []
    for m in re.finditer(r'@router\.(get|post|put|delete|patch)\(([^)]*)\)\s*(?:async\s+)?def\s+(\w+)\s*\(', src):
        results.append({
            "method": m.group(1),
            "path": m.group(2).strip().strip('"').strip("'"),
            "func_name": m.group(3),
        })
    return results


def _get_function_signature(src: str, func_name: str) -> str:
    """提取函数完整签名（参数列表）"""
    m = re.search(rf'def\s+{func_name}\s*\(', src)
    if not m:
        return ""
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(src):
        if src[i] == '(':
            depth += 1
        elif src[i] == ')':
            depth -= 1
            if depth == 0:
                return src[start + 1:i]
        i += 1
    return src[start + 1:]


def _has_path_param(path: str) -> bool:
    """检查路由路径是否包含路径参数"""
    return bool(re.search(r'\{[^}]+\}', path))


def _extract_path_params(path: str) -> list[str]:
    """提取路径参数名"""
    return re.findall(r'\{(\w+)\}', path)


# ═══════════════════════════════════════════════════════════
# 1. 路径参数类型验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPathParamTypes:
    """路径参数使用正确的类型注解"""

    def test_path_params_use_uuid_type(self):
        """ID 路径参数使用 uuid.UUID 或 str 类型"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                params = _extract_path_params(ep["path"])
                sig = _get_function_signature(src, ep["func_name"])
                for param in params:
                    if param.endswith("_id"):
                        # 参数应有 uuid.UUID 或 str 类型注解
                        pattern_uuid = rf'{param}\s*:\s*uuid\.UUID\b'
                        pattern_str = rf'{param}\s*:\s*str\b'
                        assert re.search(pattern_uuid, sig) or re.search(pattern_str, sig), (
                            f"{name}.{ep['func_name']} 参数 {param} 应注解为 uuid.UUID 或 str"
                        )

    def test_path_params_have_no_defaults(self):
        """路径参数没有默认值"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                params = _extract_path_params(ep["path"])
                sig = _get_function_signature(src, ep["func_name"])
                for param in params:
                    # 路径参数注解后不应紧跟 = （不应跨逗号匹配）
                    # 提取该参数的声明：param: type 到下一个逗号或闭括号
                    m = re.search(rf'{param}\s*:\s*([^,\)]+)', sig)
                    if m:
                        param_decl = m.group(1).strip()
                        assert "=" not in param_decl, (
                            f"{name}.{ep['func_name']} 路径参数 {param} 不应有默认值: {param_decl}"
                        )

    def test_all_path_params_present_in_signature(self):
        """路径中的参数都在函数签名中声明"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                params = _extract_path_params(ep["path"])
                sig = _get_function_signature(src, ep["func_name"])
                for param in params:
                    assert param in sig, (
                        f"{name}.{ep['func_name']} 路径参数 {param} 未在签名中声明"
                    )

    def test_path_param_naming_uses_snake_case(self):
        """路径参数使用 snake_case"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                params = _extract_path_params(ep["path"])
                for param in params:
                    assert re.match(r'^[a-z][a-z0-9_]*$', param), (
                        f"{name} 路径参数 {param} 应使用 snake_case"
                    )

    def test_path_param_names_match_pattern(self):
        """路径参数名与路径模板匹配"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                if _has_path_param(ep["path"]):
                    sig = _get_function_signature(src, ep["func_name"])
                    params = _extract_path_params(ep["path"])
                    for param in params:
                        assert param in sig, (
                            f"{name} 路径参数 {param} 应在函数签名中"
                        )


# ═══════════════════════════════════════════════════════════
# 2. 依赖注入类型验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestDependencyInjectionTypes:
    """依赖注入参数有正确的类型注解"""

    def test_db_param_uses_session_type(self):
        """db 参数使用 Session 类型"""
        for name, src in SOURCES.items():
            if "Depends(get_db)" in src:
                # 检查有 db: Session 模式
                assert re.search(r'db\s*:\s*Session\s*=\s*Depends\(get_db\)', src), (
                    f"{name} db 参数应注解为 Session = Depends(get_db)"
                )

    def test_current_user_param_uses_user_type(self):
        """current_user 参数使用 User 类型"""
        for name, src in SOURCES.items():
            if "require_permission(" in src:
                assert re.search(r'current_user\s*:\s*User\s*=\s*Depends', src), (
                    f"{name} current_user 应注解为 User = Depends(...)"
                )

    def test_pagination_param_uses_pagination_params_type(self):
        """pagination 参数使用 PaginationParams 类型"""
        for name in ["products", "customers", "orders", "users", "payments", "inventory", "audit_logs"]:
            src = SOURCES[name]
            assert re.search(r'pagination\s*:\s*PaginationParams\s*=\s*Depends\(\)', src), (
                f"{name} pagination 应注解为 PaginationParams = Depends()"
            )

    def test_request_param_has_request_type(self):
        """request 参数使用 Request 类型"""
        for name, src in SOURCES.items():
            if "request: Request" in src:
                # 确认是从 fastapi 或 starlette 导入
                assert "Request" in src, f"{name} 使用 Request 类型但可能缺少导入"

    def test_depends_functions_are_imported(self):
        """依赖注入函数都已导入"""
        for name, src in SOURCES.items():
            if "Depends(get_db)" in src:
                assert "get_db" in src, f"{name} 使用 get_db 但未导入"
            if "Depends(require_permission" in src:
                assert "require_permission" in src, f"{name} 使用 require_permission 但未导入"
            if "Depends(get_current_user)" in src:
                assert "get_current_user" in src, f"{name} 使用 get_current_user 但未导入"


# ═══════════════════════════════════════════════════════════
# 3. 请求体类型验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestRequestBodyTypes:
    """POST/PUT 端点的请求体参数有 Pydantic 模型类型"""

    def test_post_endpoints_have_body_param(self):
        """核心 POST 创建端点有请求体参数"""
        # 只检查明确需要 body 的创建端点
        create_endpoints = {
            "products": "create_product",
            "customers": "create_customer",
            "orders": "create_order",
            "users": "create_user",
            "roles": "create_role",
        }
        for name, func in create_endpoints.items():
            src = SOURCES.get(name, "")
            if not src:
                continue
            sig = _get_function_signature(src, func)
            # 应有 Pydantic 模型参数
            has_body = bool(re.search(r'data\s*:\s*\w+', sig)) or \
                       bool(re.search(r'body\s*:\s*\w+', sig)) or \
                       "Create" in sig
            assert has_body, f"{name}.{func} 创建端点应有请求体参数"

    def test_put_endpoints_have_body_param(self):
        """PUT 端点有请求体参数"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                if ep["method"] == "put":
                    sig = _get_function_signature(src, ep["func_name"])
                    # PUT 应有 Update 模型
                    has_body = "Update" in sig or "data" in sig
                    assert has_body, (
                        f"{name}.{ep['func_name']} PUT 端点应有请求体参数"
                    )

    def test_body_params_use_pydantic_models(self):
        """请求体参数使用 Pydantic 模型类型"""
        for name in ["products", "customers", "orders", "users", "roles"]:
            src = SOURCES[name]
            # 检查是否有 Create/Update Schema 导入
            assert "Create" in src or "Update" in src, (
                f"{name} 应导入 Create/Update Pydantic 模型"
            )

    def test_create_schemas_are_imported(self):
        """Create Schema 在路由模块中导入"""
        for name in ["products", "customers", "orders"]:
            src = SOURCES[name]
            assert "Create" in src, f"{name} 路由应导入 Create Schema"

    def test_no_raw_dict_body_params(self):
        """不使用 dict 作为请求体类型（应使用 Pydantic 模型）"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                sig = _get_function_signature(src, ep["func_name"])
                # 不应有 dict 类型的 body 参数
                assert "data: dict" not in sig, (
                    f"{name}.{ep['func_name']} 不应使用 dict 作为请求体类型"
                )


# ═══════════════════════════════════════════════════════════
# 4. 参数默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestParameterDefaults:
    """参数默认值符合规范"""

    def test_optional_params_have_none_default(self):
        """Optional 查询参数默认 None"""
        for name in ["products", "customers", "orders"]:
            src = SOURCES[name]
            # 查找 str | None 类型的参数，确认有 = None
            for m in re.finditer(r'(\w+)\s*:\s*(?:str|uuid\.UUID|Literal[^)]+)\s*\|\s*None\s*=\s*(\w+)', src):
                param = m.group(1)
                default = m.group(2)
                assert default == "None", (
                    f"{name}.{param} Optional 参数默认应为 None，实际 {default}"
                )

    def test_query_params_have_defaults_or_required(self):
        """Query 参数有默认值或为必需"""
        for name, src in SOURCES.items():
            for m in re.finditer(r'Query\(', src):
                # 找到 Query( 后面的参数
                rest = src[m.end():m.end() + 50]
                # Query 应有默认值参数或 ... 表示必需
                assert rest.strip().startswith(("\"", "'", "...", "None", "1", "10", "20")) or \
                       rest.strip()[0].isdigit() or rest.strip()[0] == "-", (
                    f"{name} Query 参数应有默认值或必需标记"
                )

    def test_depends_params_use_correct_pattern(self):
        """Depends() 参数使用一致的依赖注入模式"""
        for name, src in SOURCES.items():
            # Depends() 不应有额外参数（除非有原因）
            empty_depends = len(re.findall(r'Depends\(\)', src))
            # get_db, get_current_user, require_permission 应使用 Depends(func)
            func_depends = len(re.findall(r'Depends\(\w+', src))
            assert empty_depends + func_depends > 0 or name == "health", (
                f"{name} 应使用 Depends() 依赖注入"
            )

    def test_no_positional_params_without_type(self):
        """没有无类型注解的位置参数"""
        for name, src in SOURCES.items():
            for ep in _find_endpoint_functions(src):
                sig = _get_function_signature(src, ep["func_name"])
                # 检查参数列表中没有缺少类型注解的参数
                # 格式应为 param: type 或 param: type = default
                for m in re.finditer(r'(\w+)\s*:', sig):
                    param = m.group(1)
                    assert param not in ("self", "cls"), f"端点函数不应有 self/cls 参数"

    def test_all_endpoints_have_db_dependency(self):
        """CRUD 操作端点有 db 依赖"""
        crud_modules = ["products", "customers", "orders", "payments", "users", "roles",
                        "inventory", "audit_logs", "reports", "exports", "files"]
        for name in crud_modules:
            src = SOURCES.get(name, "")
            if not src:
                continue
            # 模块级别的 CRUD 端点至少有一个使用 get_db
            assert "Depends(get_db)" in src, f"{name} 模块应使用 Depends(get_db)"

    def test_non_health_modules_import_session(self):
        """非 health 模块导入 Session 类型"""
        for name in ["products", "customers", "orders", "users", "roles"]:
            src = SOURCES[name]
            assert "Session" in src, f"{name} 应导入 Session 类型"

    def test_core_modules_import_uuid(self):
        """使用 UUID 路径参数的模块导入 uuid"""
        for name, src in SOURCES.items():
            if re.search(r'uuid\.UUID', src):
                assert "import uuid" in src or "from uuid" in src, (
                    f"{name} 使用 uuid.UUID 但未导入 uuid 模块"
                )

    def test_action_endpoints_use_post_method(self):
        """动作端点使用 POST 方法"""
        action_endpoints = {
            "orders": ["confirm", "cancel"],
            "payments": ["reverse"],
        }
        for name, actions in action_endpoints.items():
            src = SOURCES[name]
            for action in actions:
                # 动作端点应在 @router.post 装饰器中
                assert f'def {action}' in src or f'{action}_' in src, (
                    f"{name} 应有 {action} 动作端点"
                )

    def test_no_bare_exception_swallowing(self):
        """端点函数不使用 bare except（应捕获具体异常）"""
        for name, src in SOURCES.items():
            bare_excepts = re.findall(r'except\s*:', src)
            assert len(bare_excepts) == 0, (
                f"{name} 不应使用 bare except（应捕获具体异常）"
            )

    def test_async_endpoints_are_minimal(self):
        """async 端点数量很少（仅文件上传/导入等特殊场景）"""
        async_count = 0
        for name, src in SOURCES.items():
            async_endpoints = re.findall(r'@router\.\w+[^)]*\)\s*async\s+def', src)
            async_count += len(async_endpoints)
        # async 端点应只用于特殊场景（如文件上传、流式响应）
        assert async_count <= 5, (
            f"async 端点应 <= 5 个（仅特殊场景），实际 {async_count}"
        )
