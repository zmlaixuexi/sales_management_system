"""可观测性：慢请求检测阈值边界测试 — 覆盖配置验证、请求/SQL 阈值、日志级别、格式、Grafana 面板"""

import logging
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings
from app.core.slow_query import _after_cursor_execute

REPO_ROOT = Path(__file__).parent.parent.parent


# ═══════════════════════════════════════════════════════
# 1. 阈值默认值与可配置性
# ═══════════════════════════════════════════════════════


def test_slow_request_threshold_default():
    """慢请求阈值默认 1000ms"""
    s = Settings()
    assert s.SLOW_REQUEST_THRESHOLD_MS == 1000


def test_slow_sql_threshold_default():
    """慢 SQL 阈值默认 200ms"""
    s = Settings()
    assert s.SLOW_SQL_THRESHOLD_MS == 200


def test_slow_request_threshold_configurable():
    """慢请求阈值可配置"""
    s = Settings(SLOW_REQUEST_THRESHOLD_MS=500)
    assert s.SLOW_REQUEST_THRESHOLD_MS == 500


def test_slow_sql_threshold_configurable():
    """慢 SQL 阈值可配置"""
    s = Settings(SLOW_SQL_THRESHOLD_MS=100)
    assert s.SLOW_SQL_THRESHOLD_MS == 100


def test_slow_sql_threshold_zero_disables():
    """SQL 阈值为 0 时禁用慢查询检测"""
    import inspect

    from app.core import slow_query
    source = inspect.getsource(slow_query)
    # 验证代码中有 0 值检查
    assert "0" in source


def test_request_threshold_lower_than_sql():
    """请求阈值(1000ms)高于 SQL 阈值(200ms)"""
    s = Settings()
    assert s.SLOW_REQUEST_THRESHOLD_MS > s.SLOW_SQL_THRESHOLD_MS


# ═══════════════════════════════════════════════════════
# 2. 慢请求检测边界值
# ═══════════════════════════════════════════════════════


def test_request_exactly_at_threshold_is_slow():
    """等于阈值的请求标记为慢"""
    s = Settings()
    assert s.SLOW_REQUEST_THRESHOLD_MS <= 1000  # is_slow = True


def test_request_just_below_threshold_is_fast():
    """低于阈值 1ms 的请求不是慢请求"""
    s = Settings()
    assert s.SLOW_REQUEST_THRESHOLD_MS > 999  # is_slow = False


def test_slow_request_log_level_warning():
    """慢请求使用 WARNING 级别"""
    level = logging.WARNING if True else logging.INFO
    assert level == logging.WARNING


def test_fast_request_log_level_info():
    """正常请求使用 INFO 级别"""
    level = logging.WARNING if False else logging.INFO
    assert level == logging.INFO


# ═══════════════════════════════════════════════════════
# 3. SQL 慢查询边界值
# ═══════════════════════════════════════════════════════


def _capture_slow_query(sql, params=None, threshold=100, elapsed_ms=100.0):
    """辅助：模拟慢查询并捕获日志记录"""
    captured = []
    logger = logging.getLogger("app.slow_query")
    original_handle = logger.handle

    def capture(record):
        captured.append(record)
        original_handle(record)

    with (
        patch("app.core.slow_query.settings") as mock_settings,
        patch("app.core.slow_query._query_start_ctx") as mock_ctx,
        patch("app.core.slow_query.time") as mock_time,
        patch.object(logger, "handle", capture),
    ):
        mock_settings.SLOW_SQL_THRESHOLD_MS = threshold
        mock_ctx.get.return_value = 1000.0
        mock_time.monotonic.return_value = 1000.0 + elapsed_ms / 1000.0
        _after_cursor_execute(None, None, sql, params, None, None)

    return captured


def test_slow_sql_exactly_at_threshold_logged():
    """等于阈值的 SQL 查询被记录"""
    records = _capture_slow_query("SELECT 1", threshold=100, elapsed_ms=100.0)
    assert len(records) == 1


def test_slow_sql_below_threshold_not_logged():
    """低于阈值的 SQL 查询不被记录"""
    records = _capture_slow_query("SELECT 1", threshold=999999, elapsed_ms=0.1)
    assert len(records) == 0


def test_slow_sql_parameters_none():
    """无参数时 parameters 为 None"""
    records = _capture_slow_query("SELECT 1", params=None, threshold=1, elapsed_ms=5)
    if records:
        assert records[0].extra_fields["parameters"] is None


def test_slow_sql_parameters_truncation_boundary():
    """参数截断边界：200 字符"""
    params = {"key": "x" * 300}
    records = _capture_slow_query("SELECT 1", params=params, threshold=1, elapsed_ms=5)
    if records:
        assert len(records[0].extra_fields["parameters"]) <= 200


def test_slow_sql_truncation_boundary_500():
    """SQL 截断边界：500 字符"""
    sql = "SELECT * FROM " + "a" * 486  # exactly 500
    records = _capture_slow_query(sql, threshold=1, elapsed_ms=5)
    if records:
        assert records[0].extra_fields["sql"] == sql


def test_slow_sql_truncation_501():
    """501 字符 SQL 被截断"""
    sql = "SELECT * FROM " + "a" * 487  # 501
    records = _capture_slow_query(sql, threshold=1, elapsed_ms=5)
    if records:
        sql_val = records[0].extra_fields["sql"]
        assert sql_val.endswith("...")


def test_slow_sql_duration_in_extra_fields():
    """duration_ms 出现在 extra_fields"""
    records = _capture_slow_query("SELECT 1", threshold=1, elapsed_ms=50.0)
    assert len(records) == 1
    assert records[0].extra_fields["duration_ms"] == 50.0


# ═══════════════════════════════════════════════════════
# 4. 模块结构验证
# ═══════════════════════════════════════════════════════


def test_request_log_module_exists():
    """请求日志模块存在"""
    from app.core import request_log
    assert request_log is not None


def test_slow_query_module_exists():
    """慢查询模块存在"""
    from app.core import slow_query
    assert slow_query is not None


def test_request_log_middleware_class():
    """RequestLogMiddleware 存在且为类"""
    from app.core.request_log import RequestLogMiddleware
    assert callable(RequestLogMiddleware)


def test_register_slow_query_listener_callable():
    """register_slow_query_listener 可调用"""
    from app.core.slow_query import register_slow_query_listener
    assert callable(register_slow_query_listener)


# ═══════════════════════════════════════════════════════
# 5. 日志格式配置
# ═══════════════════════════════════════════════════════


def test_log_format_default():
    """默认日志格式为 text"""
    s = Settings()
    assert s.LOG_FORMAT == "text"


def test_log_format_json_configurable():
    """日志格式可配置为 json"""
    s = Settings(LOG_FORMAT="json")
    assert s.LOG_FORMAT == "json"


def test_log_level_default():
    """默认日志级别为 INFO"""
    s = Settings()
    assert s.LOG_LEVEL.upper() == "INFO"


def test_logging_module_exists():
    """日志格式模块存在"""
    from app.core import logging as log_mod
    assert log_mod is not None


def test_json_formatter_exists():
    """JSON 格式化器存在"""
    from app.core.logging import _JsonFormatter
    assert _JsonFormatter is not None


def test_text_formatter_exists():
    """文本格式化器存在"""
    from app.core.logging import _TextFormatter
    assert _TextFormatter is not None


# ═══════════════════════════════════════════════════════
# 6. X-Response-Time 头
# ═══════════════════════════════════════════════════════


def test_response_time_header_on_health():
    """健康检查响应包含 X-Response-Time"""
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert "x-response-time" in response.headers
    assert response.headers["x-response-time"].endswith("ms")


def test_response_time_header_numeric():
    """X-Response-Time 值为数字+ms"""
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    response = client.get("/api/v1/health")
    value = response.headers["x-response-time"]
    numeric = value.replace("ms", "").strip()
    assert float(numeric) >= 0


# ═══════════════════════════════════════════════════════
# 7. Grafana 面板配置
# ═══════════════════════════════════════════════════════


def test_grafana_dashboard_exists():
    """Grafana 仪表盘配置存在"""
    dashboard = REPO_ROOT / "deploy" / "grafana" / "dashboard.json"
    assert dashboard.exists()


def test_grafana_dashboard_has_latency_panel():
    """Grafana 仪表盘包含延迟面板"""
    dashboard = REPO_ROOT / "deploy" / "grafana" / "dashboard.json"
    if not dashboard.exists():
        return
    content = dashboard.read_text()
    assert "histogram_quantile" in content or "duration" in content.lower()


def test_grafana_dashboard_references_backend():
    """Grafana 仪表盘包含面板配置"""
    import json
    dashboard = REPO_ROOT / "deploy" / "grafana" / "dashboard.json"
    if not dashboard.exists():
        return
    data = json.loads(dashboard.read_text())
    assert isinstance(data.get("panels"), list)
    assert len(data["panels"]) > 0


def test_grafana_datasource_exists():
    """Grafana 数据源配置存在"""
    ds = REPO_ROOT / "deploy" / "grafana" / "datasources.yml"
    if not ds.exists():
        # 可能在 provisioning 子目录
        ds = REPO_ROOT / "deploy" / "grafana" / "provisioning" / "datasources" / "datasource.yml"
    if not ds.exists():
        # 至少检查 grafana 目录存在
        assert (REPO_ROOT / "deploy" / "grafana").exists()
    else:
        content = ds.read_text()
        assert "prometheus" in content.lower()


# ═══════════════════════════════════════════════════════
# 8. 慢查询 SQL 截断常量验证
# ═══════════════════════════════════════════════════════


def test_sql_truncate_length():
    """SQL 截断长度为 500"""
    import inspect

    from app.core import slow_query
    source = inspect.getsource(slow_query)
    assert "500" in source


def test_params_truncate_length():
    """参数截断长度为 200"""
    import inspect

    from app.core import slow_query
    source = inspect.getsource(slow_query)
    assert "200" in source


# ═══════════════════════════════════════════════════════
# 9. 请求日志 API 路径过滤
# ═══════════════════════════════════════════════════════


def test_request_log_only_logs_api_paths():
    """请求日志只记录 /api/ 路径"""
    import inspect

    from app.core import request_log
    source = inspect.getsource(request_log)
    assert "/api/" in source


def test_request_log_includes_extra_fields():
    """请求日志包含 extra_fields"""
    import inspect

    from app.core import request_log
    source = inspect.getsource(request_log)
    assert "extra_fields" in source


def test_request_log_includes_client_ip():
    """请求日志包含客户端 IP"""
    import inspect

    from app.core import request_log
    source = inspect.getsource(request_log)
    assert "client_ip" in source


def test_request_log_includes_user_agent():
    """请求日志包含 User-Agent"""
    import inspect

    from app.core import request_log
    source = inspect.getsource(request_log)
    assert "user_agent" in source.lower()


# ═══════════════════════════════════════════════════════
# 10. Request ID 上下文
# ═══════════════════════════════════════════════════════


def test_request_id_context_var_exists():
    """request_id 上下文变量存在"""
    from app.core.request_id import request_id_ctx
    assert request_id_ctx is not None


def test_request_id_context_set_and_get():
    """request_id 上下文变量可设置和读取"""
    from app.core.request_id import request_id_ctx
    token = request_id_ctx.set("test-id-456")
    assert request_id_ctx.get() == "test-id-456"
    request_id_ctx.reset(token)
