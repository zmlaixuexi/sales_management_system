"""需求符合性：后端状态常量跨模块一致性验证测试
验证订单/商品/收款/客户状态值在 schema/service/api/export 之间一致"""

import re
from pathlib import Path

from app.schemas.customer import CustomerLevel, CustomerSource
from app.schemas.product import ProductStatus

API_DIR = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
SERVICES_DIR = Path(__file__).resolve().parent.parent / "app" / "services"
FRONTEND_CONST = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "constants" / "statusMaps.ts"


def _extract_ts_record_keys(source, var_name):
    """从 TS 文件提取 Record 的顶层键（使用大括号计数处理嵌套）"""
    idx = source.find(var_name)
    if idx == -1:
        return set()
    brace_start = source.find("{", idx)
    if brace_start == -1:
        return set()
    depth = 0
    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                block = source[brace_start:i + 1]
                keys = re.findall(r"^\s*([a-zA-Z_]+)\s*:", block, re.MULTILINE)
                return set(keys)
    return set()


class TestProductStatusConsistency:
    """商品状态：active/inactive/disabled"""

    EXPECTED = {"active", "inactive", "disabled"}

    def test_schema_matches(self):
        values = set(typ for typ in ProductStatus.__args__)
        assert values == self.EXPECTED

    def test_frontend_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "productStatusMap")
        assert frontend_keys == self.EXPECTED


class TestOrderStatusConsistency:
    """订单状态：draft/confirmed/cancelled/partially_paid/completed"""

    EXPECTED = {"draft", "confirmed", "cancelled", "partially_paid", "completed"}

    def test_order_endpoint_literal(self):
        source = (API_DIR / "orders.py").read_text()
        # 找到 Literal["draft", "confirmed", ...] 中的所有值
        for m in re.finditer(r'Literal\[(.+?)\]', source):
            values = set(re.findall(r'"(\w+)"', m.group(1)))
            if "draft" in values and "completed" in values:
                assert values == self.EXPECTED
                return
        raise AssertionError("未找到订单状态 Literal 定义")

    def test_status_labels_match(self):
        source = (API_DIR / "orders.py").read_text()
        # STATUS_LABELS 的键
        m = re.search(r'STATUS_LABELS\s*=\s*\{(.+?)\}', source, re.DOTALL)
        assert m
        keys = set(re.findall(r'"(\w+)":', m.group(1)))
        assert keys == self.EXPECTED

    def test_valid_transitions_cover_all_statuses(self):
        source = (API_DIR / "orders.py").read_text()
        # VALID_TRANSITIONS 键包括 "key": { 和 "key": set()
        keys = set(re.findall(r'"(\w+)"\s*:\s*[\{s]', source))
        # 过滤到只有已知的订单状态键
        order_keys = keys & self.EXPECTED
        assert order_keys == self.EXPECTED

    def test_export_status_map_matches(self):
        source = (SERVICES_DIR / "export_service.py").read_text()
        m = re.search(r'STATUS_MAP\s*=\s*\{(.+?)\}', source, re.DOTALL)
        assert m
        keys = set(re.findall(r'"(\w+)":', m.group(1)))
        assert keys == self.EXPECTED

    def test_frontend_order_status_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "orderStatusMap")
        assert frontend_keys == self.EXPECTED


class TestPaymentStatusConsistency:
    """收款状态：normal/reversed"""

    EXPECTED = {"normal", "reversed"}

    def test_payment_create_uses_normal(self):
        source = (SERVICES_DIR / "payment_service.py").read_text()
        assert 'status="normal"' in source or "status='normal'" in source

    def test_payment_reverse_uses_reversed(self):
        source = (API_DIR / "payments.py").read_text()
        assert '"reversed"' in source

    def test_frontend_payment_status_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "paymentStatusMap")
        assert frontend_keys == self.EXPECTED


class TestCustomerSourceConsistency:
    """客户来源：referral/online/offline/ad/other"""

    EXPECTED = {"referral", "online", "offline", "ad", "other"}

    def test_schema_matches(self):
        values = set(typ for typ in CustomerSource.__args__)
        assert values == self.EXPECTED

    def test_frontend_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "customerSourceMap")
        assert frontend_keys == self.EXPECTED


class TestCustomerLevelConsistency:
    """客户等级：vip/important/normal/potential"""

    EXPECTED = {"vip", "important", "normal", "potential"}

    def test_schema_matches(self):
        values = set(typ for typ in CustomerLevel.__args__)
        assert values == self.EXPECTED

    def test_frontend_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "customerLevelMap")
        assert frontend_keys == self.EXPECTED


class TestPaymentMethodConsistency:
    """收款方式：cash/transfer/wechat/alipay/other"""

    EXPECTED = {"cash", "transfer", "wechat", "alipay", "other"}

    def test_schema_literal_matches(self):
        source = (Path(__file__).resolve().parent.parent / "app" / "schemas" / "payment.py").read_text()
        for m in re.finditer(r'Literal\[(.+?)\]', source):
            values = set(re.findall(r'"(\w+)"', m.group(1)))
            if "cash" in values and "wechat" in values:
                assert values == self.EXPECTED
                return
        raise AssertionError("未找到收款方式 Literal 定义")

    def test_frontend_matches(self):
        source = FRONTEND_CONST.read_text()
        frontend_keys = _extract_ts_record_keys(source, "paymentMethodMap")
        assert frontend_keys == self.EXPECTED


class TestStatusLabelCompleteness:
    """所有状态值都有中文标签"""

    def test_order_labels_count(self):
        source = (API_DIR / "orders.py").read_text()
        m = re.search(r'STATUS_LABELS\s*=\s*\{(.+?)\}', source, re.DOTALL)
        assert m
        keys = re.findall(r'"(\w+)":', m.group(1))
        assert len(keys) == 5

    def test_product_frontend_labels(self):
        source = FRONTEND_CONST.read_text()
        for status in ("active", "inactive", "disabled"):
            assert status in source, f"商品状态 {status} 缺少前端标签"

    def test_order_frontend_labels(self):
        source = FRONTEND_CONST.read_text()
        for status in ("draft", "confirmed", "cancelled", "partially_paid", "completed"):
            assert status in source, f"订单状态 {status} 缺少前端标签"

    def test_payment_frontend_labels(self):
        source = FRONTEND_CONST.read_text()
        for status in ("normal", "reversed"):
            assert status in source, f"收款状态 {status} 缺少前端标签"
