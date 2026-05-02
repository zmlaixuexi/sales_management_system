"""导出 API 辅助函数单元测试 — _csv_filename"""

from datetime import datetime
from unittest.mock import patch

from app.api.v1.exports import _csv_filename


def test_csv_filename_format():
    """文件名包含前缀、时间戳和 .csv 后缀"""
    with patch("app.api.v1.exports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 5, 2, 14, 30, 5)
        result = _csv_filename("products")
    assert result == "products_20260502_143005.csv"


def test_csv_filename_different_prefixes():
    """不同前缀生成不同文件名"""
    with patch("app.api.v1.exports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 1, 0, 0, 0)
        assert _csv_filename("orders") == "orders_20260101_000000.csv"
        assert _csv_filename("customers") == "customers_20260101_000000.csv"
        assert _csv_filename("payments") == "payments_20260101_000000.csv"


def test_csv_filename_always_ends_csv():
    """文件名始终以 .csv 结尾"""
    with patch("app.api.v1.exports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 12, 31, 23, 59, 59)
        result = _csv_filename("test")
    assert result.endswith(".csv")
