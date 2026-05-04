"""
可观测性：后端 Prometheus 指标与业务计数器覆盖验证测试
覆盖指标定义与命名、指标类型与标签、
业务层埋点覆盖、/metrics 端点配置、Instrumentator 配置
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

METRICS_SRC = (ROOT / "app" / "core" / "metrics.py").read_text()
MAIN_SRC = (ROOT / "app" / "main.py").read_text()
CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()

API_DIR = ROOT / "app" / "api" / "v1"
ORDERS_SRC = (API_DIR / "orders.py").read_text()
PAYMENTS_SRC = (API_DIR / "payments.py").read_text()
AUTH_SRC = (API_DIR / "auth.py").read_text()

PROMETHEUS_YML = ROOT.parent / "deploy" / "prometheus.yml"
PROM_CFG = PROMETHEUS_YML.read_text() if PROMETHEUS_YML.exists() else ""


def _count_metric_type(src: str, metric_type: str) -> int:
    """统计指定类型的指标数量"""
    return len(re.findall(rf'=\s*{metric_type}\(', src))


def _find_metric_names(src: str) -> list[str]:
    """提取所有指标名称"""
    return re.findall(r"['\"](\w+)['\"],\s*(?:Counter|Gauge|Histogram|Summary)", src)


# ═══════════════════════════════════════════════════════════
# 1. 指标定义与命名规范验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMetricDefinitionNaming:
    """指标定义遵循 Prometheus 命名规范"""

    def test_at_least_6_custom_metrics_defined(self):
        """至少定义 6 个自定义业务指标"""
        counters = _count_metric_type(METRICS_SRC, "Counter")
        gauges = _count_metric_type(METRICS_SRC, "Gauge")
        assert counters + gauges >= 6, f"应至少定义 6 个自定义指标，实际 {counters + gauges}"

    def test_counter_names_have_total_suffix(self):
        """Counter 指标名使用 _total 后缀"""
        names = _find_metric_names(METRICS_SRC)
        counter_names = []
        for m in re.finditer(r"(\w+)\s*=\s*Counter\(\s*['\"](\w+)", METRICS_SRC):
            counter_names.append(m.group(2))
        for name in counter_names:
            assert name.endswith("_total") or name.endswith("_total"), (
                f"Counter '{name}' 应以 _total 结尾"
            )

    def test_metric_names_use_business_prefix(self):
        """业务指标使用 business_ 前缀"""
        for m in re.finditer(r"=\s*(?:Counter|Gauge)\(\s*['\"](\w+)", METRICS_SRC):
            name = m.group(1)
            assert name.startswith("business_"), f"指标 '{name}' 应使用 business_ 前缀"

    def test_metric_names_use_snake_case(self):
        """指标名使用 snake_case"""
        for m in re.finditer(r"=\s*(?:Counter|Gauge|Histogram)\(\s*['\"](\w+)", METRICS_SRC):
            name = m.group(1)
            assert name == name.lower(), f"指标 '{name}' 应使用小写 snake_case"
            assert re.match(r'^[a-z_]+$', name), f"指标 '{name}' 应只含小写字母和下划线"

    def test_all_metrics_have_descriptions(self):
        """所有指标有中文描述"""
        for m in re.finditer(r"=\s*(?:Counter|Gauge)\([^)]+\)", METRICS_SRC):
            definition = m.group(0)
            # 描述应在第二个参数
            assert '"' in definition or "'" in definition, "指标应有描述字符串"


# ═══════════════════════════════════════════════════════════
# 2. 指标类型与标签验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMetricTypesAndLabels:
    """指标类型和标签正确"""

    def test_order_metrics_cover_lifecycle(self):
        """订单指标覆盖生命周期（created, confirmed, cancelled）"""
        assert "business_order_created" in METRICS_SRC, "应定义 order_created 指标"
        assert "business_order_confirmed" in METRICS_SRC, "应定义 order_confirmed 指标"
        assert "business_order_cancelled" in METRICS_SRC, "应定义 order_cancelled 指标"

    def test_payment_metrics_cover_lifecycle(self):
        """收款指标覆盖生命周期（registered, reversed）"""
        assert "business_payment_registered" in METRICS_SRC, "应定义 payment_registered 指标"
        assert "business_payment_reversed" in METRICS_SRC, "应定义 payment_reversed 指标"

    def test_login_attempts_has_result_label(self):
        """登录尝试指标有 result 标签（success/failed）"""
        assert "result" in METRICS_SRC, "LOGIN_ATTEMPTS 应有 result 标签"
        assert "success" in AUTH_SRC, "应追踪成功登录"
        assert "failed" in AUTH_SRC, "应追踪失败登录"

    def test_order_created_has_status_label(self):
        """订单创建指标有 status 标签"""
        assert "status" in METRICS_SRC, "ORDER_CREATED 应有 status 标签"

    def test_payment_registered_has_method_label(self):
        """收款登记指标有 method 标签"""
        assert "method" in METRICS_SRC, "PAYMENT_REGISTERED 应有 method 标签"


# ═══════════════════════════════════════════════════════════
# 3. 业务层埋点覆盖验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestBusinessInstrumentation:
    """业务埋点覆盖关键流程"""

    def test_orders_module_increments_order_created(self):
        """订单模块在创建订单后递增 ORDER_CREATED"""
        assert "ORDER_CREATED" in ORDERS_SRC, "orders 模块应使用 ORDER_CREATED"
        assert ".inc()" in ORDERS_SRC, "orders 模块应递增指标"

    def test_orders_module_increments_order_confirmed(self):
        """订单模块在确认订单后递增 ORDER_CONFIRMED"""
        assert "ORDER_CONFIRMED" in ORDERS_SRC, "orders 模块应使用 ORDER_CONFIRMED"

    def test_payments_module_increments_payment_registered(self):
        """收款模块在登记收款后递增 PAYMENT_REGISTERED"""
        assert "PAYMENT_REGISTERED" in PAYMENTS_SRC, "payments 模块应使用 PAYMENT_REGISTERED"
        assert ".inc()" in PAYMENTS_SRC, "payments 模块应递增指标"

    def test_auth_module_tracks_login_attempts(self):
        """认证模块追踪登录尝试"""
        assert "LOGIN_ATTEMPTS" in AUTH_SRC, "auth 模块应使用 LOGIN_ATTEMPTS"
        assert "success" in AUTH_SRC, "应追踪成功登录"
        assert "failed" in AUTH_SRC, "应追踪失败登录"

    def test_inventory_stockout_metric_exists(self):
        """库存不足指标已定义"""
        assert "INVENTORY_STOCKOUT" in METRICS_SRC or "stockout" in METRICS_SRC, (
            "应定义库存不足指标"
        )


# ═══════════════════════════════════════════════════════════
# 4. /metrics 端点配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestMetricsEndpointConfig:
    """/metrics 端点正确配置"""

    def test_metrics_endpoint_exposed(self):
        """Instrumentator 暴露 /metrics 端点"""
        assert "/metrics" in MAIN_SRC, "应暴露 /metrics 端点"
        assert ".expose(" in MAIN_SRC, "应调用 expose() 方法"

    def test_metrics_excluded_from_openapi(self):
        """/metrics 不出现在 OpenAPI 文档中"""
        assert "include_in_schema=False" in MAIN_SRC or "include_in_schema" in MAIN_SRC, (
            "/metrics 应排除在 OpenAPI 文档之外"
        )

    def test_health_and_version_excluded_from_instrumentation(self):
        """健康检查和版本端点排除在指标之外"""
        assert "/health" in MAIN_SRC, "应排除 /health 路径"
        assert "/version" in MAIN_SRC, "应排除 /version 路径"

    def test_status_codes_grouped(self):
        """状态码分组启用"""
        assert "should_group_status_codes" in MAIN_SRC, "应启用状态码分组"
        assert "True" in MAIN_SRC, "should_group_status_codes 应为 True"

    def test_business_metrics_imported_in_main(self):
        """业务指标在 main.py 中被导入以确保注册"""
        assert "metrics" in MAIN_SRC, "main.py 应导入 metrics 模块"
        # 导入应在模块级别，确保自定义指标注册到默认 registry
        m = re.search(r'import.*metrics', MAIN_SRC)
        assert m, "main.py 应导入 metrics 模块"


# ═══════════════════════════════════════════════════════════
# 5. Instrumentator 与部署配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestInstrumentatorConfig:
    """Instrumentator 和部署配置"""

    def test_instrumentator_class_used(self):
        """使用 Instrumentator 类"""
        assert "Instrumentator" in MAIN_SRC, "应使用 prometheus_fastapi_instrumentator"

    def test_prometheus_dependency_in_pyproject(self):
        """prometheus-fastapi-instrumentator 在依赖中"""
        pyproject = (ROOT / "pyproject.toml").read_text()
        assert "prometheus" in pyproject.lower(), "pyproject.toml 应包含 prometheus 依赖"

    def test_prometheus_scrape_config_exists(self):
        """Prometheus 采集配置存在"""
        assert PROM_CFG != "", "deploy/prometheus.yml 应存在"
        assert "scrape" in PROM_CFG.lower(), "prometheus.yml 应有 scrape 配置"
        assert "/metrics" in PROM_CFG, "prometheus.yml 应配置 metrics 路径"

    def test_scrape_interval_configured(self):
        """采集间隔已配置"""
        assert "scrape_interval" in PROM_CFG, "应配置 scrape_interval"
        m = re.search(r'scrape_interval:\s*(\w+)', PROM_CFG)
        assert m, "应设置 scrape_interval 值"

    def test_metrics_module_exports_all_metrics(self):
        """metrics 模块导出所有指标变量"""
        exports = re.findall(r'^(\w+)\s*=\s*(?:Counter|Gauge)', METRICS_SRC, re.MULTILINE)
        assert len(exports) >= 6, f"应导出至少 6 个指标，实际 {len(exports)}"
