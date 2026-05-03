"""Prometheus 自定义业务指标"""

from prometheus_client import Counter, Gauge

# ─── 订单指标 ────────────────────────────────────────────────

ORDER_CREATED = Counter(
    "business_order_created_total",
    "创建订单总数",
    ["status"],
)

ORDER_CONFIRMED = Counter(
    "business_order_confirmed_total",
    "确认订单总数",
)

ORDER_CANCELLED = Counter(
    "business_order_cancelled_total",
    "取消订单总数",
)

# ─── 收款指标 ────────────────────────────────────────────────

PAYMENT_REGISTERED = Counter(
    "business_payment_registered_total",
    "登记收款总数",
    ["method"],
)

PAYMENT_REVERSED = Counter(
    "business_payment_reversed_total",
    "撤销收款总数",
)

# ─── 库存指标 ────────────────────────────────────────────────

INVENTORY_STOCKOUT = Counter(
    "business_inventory_stockout_total",
    "库存不足事件总数",
)

LOW_STOCK_PRODUCTS = Gauge(
    "business_low_stock_products",
    "当前低库存商品数量",
)

# ─── 认证指标 ────────────────────────────────────────────────

LOGIN_ATTEMPTS = Counter(
    "business_login_attempts_total",
    "登录尝试总数",
    ["result"],  # success / failed
)
