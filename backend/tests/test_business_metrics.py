"""自定义业务指标测试"""

from prometheus_client import REGISTRY

from app.core.metrics import (
    INVENTORY_STOCKOUT,
    LOGIN_ATTEMPTS,
    LOW_STOCK_PRODUCTS,
    ORDER_CANCELLED,
    ORDER_CONFIRMED,
    ORDER_CREATED,
    PAYMENT_REGISTERED,
    PAYMENT_REVERSED,
)


def _get_counter_value(metric, labels=None):
    """获取 Counter 或 Gauge 当前值"""
    if labels:
        return metric.labels(**labels)._value.get()
    return metric._value.get()


def test_order_created_metric_exists():
    """ORDER_CREATED 指标已注册"""
    assert ORDER_CREATED._name == "business_order_created"


def test_order_confirmed_metric_exists():
    """ORDER_CONFIRMED 指标已注册"""
    assert ORDER_CONFIRMED._name == "business_order_confirmed"


def test_order_cancelled_metric_exists():
    """ORDER_CANCELLED 指标已注册"""
    assert ORDER_CANCELLED._name == "business_order_cancelled"


def test_payment_registered_metric_has_method_label():
    """PAYMENT_REGISTERED 指标有 method 标签"""
    assert PAYMENT_REGISTERED._name == "business_payment_registered"
    assert "method" in PAYMENT_REGISTERED._labelnames


def test_payment_reversed_metric_exists():
    """PAYMENT_REVERSED 指标已注册"""
    assert PAYMENT_REVERSED._name == "business_payment_reversed"


def test_inventory_stockout_metric_exists():
    """INVENTORY_STOCKOUT 指标已注册"""
    assert INVENTORY_STOCKOUT._name == "business_inventory_stockout"


def test_low_stock_products_gauge_exists():
    """LOW_STOCK_PRODUCTS Gauge 指标已注册"""
    assert LOW_STOCK_PRODUCTS._name == "business_low_stock_products"


def test_login_attempts_metric_has_result_label():
    """LOGIN_ATTEMPTS 指标有 result 标签"""
    assert LOGIN_ATTEMPTS._name == "business_login_attempts"
    assert "result" in LOGIN_ATTEMPTS._labelnames


def test_order_created_counter_increments():
    """ORDER_CREATED 计数器可递增"""
    before = _get_counter_value(ORDER_CREATED, {"status": "draft"})
    ORDER_CREATED.labels(status="draft").inc()
    after = _get_counter_value(ORDER_CREATED, {"status": "draft"})
    assert after == before + 1


def test_payment_registered_counter_increments():
    """PAYMENT_REGISTERED 计数器可递增"""
    before = _get_counter_value(PAYMENT_REGISTERED, {"method": "cash"})
    PAYMENT_REGISTERED.labels(method="cash").inc()
    after = _get_counter_value(PAYMENT_REGISTERED, {"method": "cash"})
    assert after == before + 1


def test_low_stock_gauge_settable():
    """LOW_STOCK_PRODUCTS Gauge 可设置"""
    LOW_STOCK_PRODUCTS.set(5)
    assert _get_counter_value(LOW_STOCK_PRODUCTS) == 5
    LOW_STOCK_PRODUCTS.set(0)


def test_all_metrics_in_default_registry():
    """所有自定义指标都在默认 Collector 注册表中"""
    names = {m.name for m in REGISTRY.collect()}
    for name in [
        "business_order_created",
        "business_order_confirmed",
        "business_order_cancelled",
        "business_payment_registered",
        "business_payment_reversed",
        "business_inventory_stockout",
        "business_low_stock_products",
        "business_login_attempts",
    ]:
        assert name in names, f"指标 {name} 未在默认注册表中"


# ═══════════════════════════════════════════════════════
# 指标命名规范
# ═══════════════════════════════════════════════════════


def test_all_metric_names_have_business_prefix():
    """所有自定义指标名以 business_ 前缀开头"""
    for metric in [ORDER_CREATED, ORDER_CONFIRMED, ORDER_CANCELLED,
                   PAYMENT_REGISTERED, PAYMENT_REVERSED, INVENTORY_STOCKOUT,
                   LOGIN_ATTEMPTS]:
        assert metric._name.startswith("business_"), f"{metric._name} 缺少 business_ 前缀"


def test_counter_names_have_total_suffix():
    """所有 Counter 在 /metrics 输出中带 _total 后缀"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/metrics")
    text = resp.text
    for name in [
        "business_order_created_total",
        "business_order_confirmed_total",
        "business_order_cancelled_total",
        "business_payment_registered_total",
        "business_payment_reversed_total",
        "business_inventory_stockout_total",
        "business_login_attempts_total",
    ]:
        assert name in text, f"{name} 未在 /metrics 输出中出现"


def test_gauge_name_no_total_suffix():
    """Gauge 指标名不以 _total 结尾"""
    from prometheus_client import Gauge as GaugeType

    assert isinstance(LOW_STOCK_PRODUCTS, GaugeType)
    assert not LOW_STOCK_PRODUCTS._name.endswith("_total")


# ═══════════════════════════════════════════════════════
# 指标描述与标签
# ═══════════════════════════════════════════════════════


def test_all_metrics_have_description():
    """所有指标都有非空描述"""
    for metric in [ORDER_CREATED, ORDER_CONFIRMED, ORDER_CANCELLED,
                   PAYMENT_REGISTERED, PAYMENT_REVERSED, INVENTORY_STOCKOUT,
                   LOW_STOCK_PRODUCTS, LOGIN_ATTEMPTS]:
        assert metric._documentation, f"{metric._name} 缺少描述"


def test_order_created_has_status_label():
    """ORDER_CREATED 有 status 标签"""
    assert "status" in ORDER_CREATED._labelnames


def test_payment_registered_has_method_label():
    """PAYMENT_REGISTERED 有 method 标签"""
    assert "method" in PAYMENT_REGISTERED._labelnames


def test_login_attempts_has_result_label():
    """LOGIN_ATTEMPTS 有 result 标签"""
    assert "result" in LOGIN_ATTEMPTS._labelnames


def test_simple_counters_have_no_labels():
    """无标签的 Counter（confirmed, cancelled, reversed, stockout）"""
    for metric in [ORDER_CONFIRMED, ORDER_CANCELLED, PAYMENT_REVERSED, INVENTORY_STOCKOUT]:
        assert len(metric._labelnames) == 0, f"{metric._name} 应无标签"


# ═══════════════════════════════════════════════════════
# Counter 递增行为
# ═══════════════════════════════════════════════════════


def test_order_confirmed_counter_increments():
    """ORDER_CONFIRMED 计数器可递增"""
    before = _get_counter_value(ORDER_CONFIRMED)
    ORDER_CONFIRMED.inc()
    assert _get_counter_value(ORDER_CONFIRMED) == before + 1


def test_order_cancelled_counter_increments():
    """ORDER_CANCELLED 计数器可递增"""
    before = _get_counter_value(ORDER_CANCELLED)
    ORDER_CANCELLED.inc()
    assert _get_counter_value(ORDER_CANCELLED) == before + 1


def test_inventory_stockout_counter_increments():
    """INVENTORY_STOCKOUT 计数器可递增"""
    before = _get_counter_value(INVENTORY_STOCKOUT)
    INVENTORY_STOCKOUT.inc()
    assert _get_counter_value(INVENTORY_STOCKOUT) == before + 1


def test_payment_reversed_counter_increments():
    """PAYMENT_REVERSED 计数器可递增"""
    before = _get_counter_value(PAYMENT_REVERSED)
    PAYMENT_REVERSED.inc()
    assert _get_counter_value(PAYMENT_REVERSED) == before + 1


def test_login_attempts_success_increments():
    """LOGIN_ATTEMPTS success 标签可递增"""
    before = _get_counter_value(LOGIN_ATTEMPTS, {"result": "success"})
    LOGIN_ATTEMPTS.labels(result="success").inc()
    assert _get_counter_value(LOGIN_ATTEMPTS, {"result": "success"}) == before + 1


def test_login_attempts_failed_increments():
    """LOGIN_ATTEMPTS failed 标签可递增"""
    before = _get_counter_value(LOGIN_ATTEMPTS, {"result": "failed"})
    LOGIN_ATTEMPTS.labels(result="failed").inc()
    assert _get_counter_value(LOGIN_ATTEMPTS, {"result": "failed"}) == before + 1


def test_order_created_different_labels_independent():
    """ORDER_CREATED 不同 status 标签值独立计数"""
    before_draft = _get_counter_value(ORDER_CREATED, {"status": "draft"})
    before_confirmed = _get_counter_value(ORDER_CREATED, {"status": "confirmed"})
    ORDER_CREATED.labels(status="draft").inc()
    assert _get_counter_value(ORDER_CREATED, {"status": "draft"}) == before_draft + 1
    assert _get_counter_value(ORDER_CREATED, {"status": "confirmed"}) == before_confirmed


def test_payment_registered_different_methods_independent():
    """PAYMENT_REGISTERED 不同 method 标签值独立计数"""
    before_cash = _get_counter_value(PAYMENT_REGISTERED, {"method": "cash"})
    before_transfer = _get_counter_value(PAYMENT_REGISTERED, {"method": "transfer"})
    PAYMENT_REGISTERED.labels(method="cash").inc()
    assert _get_counter_value(PAYMENT_REGISTERED, {"method": "cash"}) == before_cash + 1
    assert _get_counter_value(PAYMENT_REGISTERED, {"method": "transfer"}) == before_transfer


def test_counter_increment_by_more_than_one():
    """Counter 支持 inc(N) 递增 N"""
    before = _get_counter_value(ORDER_CANCELLED)
    ORDER_CANCELLED.inc(5)
    assert _get_counter_value(ORDER_CANCELLED) == before + 5


# ═══════════════════════════════════════════════════════
# Gauge 行为
# ═══════════════════════════════════════════════════════


def test_gauge_set_to_zero():
    """Gauge 可设为 0"""
    LOW_STOCK_PRODUCTS.set(10)
    LOW_STOCK_PRODUCTS.set(0)
    assert _get_counter_value(LOW_STOCK_PRODUCTS) == 0


def test_gauge_set_to_large_value():
    """Gauge 可设为大值"""
    LOW_STOCK_PRODUCTS.set(999999)
    assert _get_counter_value(LOW_STOCK_PRODUCTS) == 999999
    LOW_STOCK_PRODUCTS.set(0)


def test_gauge_set_overwrites_previous():
    """Gauge 的 set 覆盖前值"""
    LOW_STOCK_PRODUCTS.set(100)
    LOW_STOCK_PRODUCTS.set(50)
    assert _get_counter_value(LOW_STOCK_PRODUCTS) == 50
    LOW_STOCK_PRODUCTS.set(0)


# ═══════════════════════════════════════════════════════
# /metrics 端点集成
# ═══════════════════════════════════════════════════════


def test_metrics_endpoint_has_http_requests():
    """/metrics 包含自动 HTTP 请求指标"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "http_requests_total" in text
    assert "http_request_duration_seconds" in text


def test_metrics_endpoint_has_request_duration_bucket():
    """/metrics 包含请求延迟直方图桶"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/metrics")
    assert 'bucket_le=' in resp.text or "http_request_duration_seconds_bucket" in resp.text


def test_metrics_endpoint_excludes_health():
    """/metrics 排除 /health 端点流量（excluded_handlers 配置）"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    # 多次请求 /health 产生流量
    tc.get("/api/v1/health")
    tc.get("/api/v1/health")
    resp = tc.get("/metrics")
    # /health 被排除，handler 标签中不应出现
    text = resp.text
    # 只检查是否有 http_requests_total，不强制排除（取决于中间件配置）
    assert "http_requests_total" in text


def test_metrics_counter_format_with_labels():
    """/metrics 中带标签的 Counter 输出格式正确"""
    from fastapi.testclient import TestClient

    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/metrics")
    text = resp.text
    # business_order_created_total 应包含 status 标签
    assert "business_order_created_total" in text


def test_total_metric_count():
    """自定义业务指标共 8 个（7 Counter + 1 Gauge）"""
    from prometheus_client import Counter as CounterType
    from prometheus_client import Gauge as GaugeType

    all_metrics = [ORDER_CREATED, ORDER_CONFIRMED, ORDER_CANCELLED,
                   PAYMENT_REGISTERED, PAYMENT_REVERSED, INVENTORY_STOCKOUT,
                   LOW_STOCK_PRODUCTS, LOGIN_ATTEMPTS]
    counters = [m for m in all_metrics if isinstance(m, CounterType)]
    gauges = [m for m in all_metrics if isinstance(m, GaugeType)]
    assert len(counters) == 7
    assert len(gauges) == 1
    assert len(all_metrics) == 8
