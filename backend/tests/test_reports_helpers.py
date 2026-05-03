"""报表辅助函数单元测试 — _date_range / _order_period_filter / _apply_data_scope"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.reports import (
    _apply_data_scope,
    _date_range,
    _order_period_filter,
)

# ─── _date_range ─────────────────────────────────────────────


@patch("app.api.v1.reports.date")
def test_date_range_today(mock_date):
    """today 返回当天起止"""
    mock_date.today.return_value = date(2026, 5, 2)
    start, end = _date_range("today")
    assert start == date(2026, 5, 2)
    assert end == date(2026, 5, 2)


@patch("app.api.v1.reports.date")
def test_date_range_7d(mock_date):
    """7d 返回最近 7 天"""
    mock_date.today.return_value = date(2026, 5, 2)
    start, end = _date_range("7d")
    assert start == date(2026, 4, 26)
    assert end == date(2026, 5, 2)


@patch("app.api.v1.reports.date")
def test_date_range_30d(mock_date):
    """30d 返回最近 30 天"""
    mock_date.today.return_value = date(2026, 5, 2)
    start, end = _date_range("30d")
    assert start == date(2026, 4, 3)
    assert end == date(2026, 5, 2)


@patch("app.api.v1.reports.date")
def test_date_range_this_month(mock_date):
    """this_month 返回本月 1 号到今天"""
    mock_date.today.return_value = date(2026, 5, 15)
    start, end = _date_range("this_month")
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 15)


@patch("app.api.v1.reports.date")
def test_date_range_last_month(mock_date):
    """last_month 返回上月全月"""
    mock_date.today.return_value = date(2026, 5, 15)
    start, end = _date_range("last_month")
    assert start == date(2026, 4, 1)
    assert end == date(2026, 5, 15)


@patch("app.api.v1.reports.date")
def test_date_range_invalid_period(mock_date):
    """不支持的 period 抛 400"""
    mock_date.today.return_value = date(2026, 5, 2)
    with pytest.raises(HTTPException) as exc_info:
        _date_range("invalid")
    assert exc_info.value.status_code == 400
    assert "不支持的 period" in str(exc_info.value.detail)


@patch("app.api.v1.reports.date")
def test_date_range_7d_boundary(mock_date):
    """7d 跨月边界"""
    mock_date.today.return_value = date(2026, 5, 3)
    start, end = _date_range("7d")
    assert start == date(2026, 4, 27)
    assert end == date(2026, 5, 3)


@patch("app.api.v1.reports.date")
def test_date_range_last_month_year_boundary(mock_date):
    """last_month 跨年边界（1 月查上月=12 月）"""
    mock_date.today.return_value = date(2026, 1, 15)
    start, end = _date_range("last_month")
    assert start == date(2025, 12, 1)
    assert end == date(2026, 1, 15)


@patch("app.api.v1.reports.date")
def test_date_range_this_month_first_day(mock_date):
    """this_month 月初时 start==end"""
    mock_date.today.return_value = date(2026, 5, 1)
    start, end = _date_range("this_month")
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 1)


# ─── _apply_data_scope ──────────────────────────────────────


def test_apply_data_scope_admin_sees_all():
    """有 order:view_all 权限的用户不过滤"""

    query = MagicMock()
    user = MagicMock()
    with patch("app.api.v1.reports.has_permission", return_value=True):
        result = _apply_data_scope(query, user)
    assert result is query


def test_apply_data_scope_sales_only_own():
    """无 view_all 权限的销售只能看自己订单"""
    query = MagicMock()
    user = MagicMock()
    user.id = "user-123"
    with patch("app.api.v1.reports.has_permission", return_value=False):
        _apply_data_scope(query, user)
    query.filter.assert_called_once()


# ─── _order_period_filter ───────────────────────────────────


@patch("app.api.v1.reports._date_range")
def test_order_period_filter_returns_filtered_query(mock_date_range):
    """返回添加了过滤条件的查询"""
    mock_date_range.return_value = (date(2026, 5, 1), date(2026, 5, 3))
    query = MagicMock()
    filtered_query = MagicMock()
    query.filter.return_value = filtered_query
    result, start, end = _order_period_filter(query, "7d")
    assert result is filtered_query
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 3)


@patch("app.api.v1.reports._date_range")
def test_order_period_filter_calls_date_range(mock_date_range):
    """正确传递 period 参数给 _date_range"""
    mock_date_range.return_value = (date(2026, 5, 1), date(2026, 5, 3))
    query = MagicMock()
    query.filter.return_value = query
    _order_period_filter(query, "this_month")
    mock_date_range.assert_called_once_with("this_month")


@patch("app.api.v1.reports._date_range")
def test_order_period_filter_invalid_period_propagates(mock_date_range):
    """不支持的 period 向上传播异常"""
    mock_date_range.side_effect = HTTPException(status_code=400, detail="bad period")
    query = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        _order_period_filter(query, "invalid")
    assert exc_info.value.status_code == 400
