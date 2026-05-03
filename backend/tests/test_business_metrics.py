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
