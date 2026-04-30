"""导出服务辅助函数单元测试 — _dec / _str / _dt"""

from datetime import datetime
from decimal import Decimal

from app.services.export_service import _dec, _dt, _str

# ─── _dec ──────────────────────────────────────────────────


def test_dec_none():
    assert _dec(None) == ""


def test_dec_value():
    assert _dec(Decimal("123.45")) == "123.45"


def test_dec_zero():
    assert _dec(Decimal("0")) == "0"


def test_dec_negative():
    assert _dec(Decimal("-10.50")) == "-10.50"


# ─── _str ──────────────────────────────────────────────────


def test_str_none():
    assert _str(None) == ""


def test_str_value():
    assert _str("hello") == "hello"


def test_str_number():
    assert _str(42) == "42"


def test_str_empty():
    assert _str("") == ""


# ─── _dt ───────────────────────────────────────────────────


def test_dt_none():
    assert _dt(None) == ""


def test_dt_iso_format():
    result = _dt("2026-04-30T12:34:56.789")
    assert result == "2026-04-30 12:34:56"


def test_dt_datetime_object():
    result = _dt(datetime(2026, 4, 30, 12, 34, 56))
    assert result == "2026-04-30 12:34:56"


def test_dt_already_formatted():
    result = _dt("2026-04-30 12:34:56")
    assert result == "2026-04-30 12:34:56"


def test_dt_short_string():
    result = _dt("2026-04-30")
    assert result == "2026-04-30"
