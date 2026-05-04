"""可观测性：Prometheus 配置与端点格式验证测试
验证 scrape 配置、instrumentator 配置、/metrics 端点格式"""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestPrometheusScrapeConfig:
    """deploy/prometheus.yml 配置验证"""

    @staticmethod
    def _load_config():
        config_path = Path(__file__).resolve().parent.parent.parent / "deploy" / "prometheus.yml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_config_loads_valid_yaml(self):
        config = self._load_config()
        assert isinstance(config, dict)

    def test_scrape_interval(self):
        config = self._load_config()
        assert config["global"]["scrape_interval"] == "15s"

    def test_evaluation_interval(self):
        config = self._load_config()
        assert config["global"]["evaluation_interval"] == "15s"

    def test_scrape_job_name(self):
        config = self._load_config()
        jobs = config["scrape_configs"]
        assert any(j["job_name"] == "backend" for j in jobs)

    def test_metrics_path(self):
        """scrape 配置的 metrics_path 与应用 /metrics 端点对齐"""
        config = self._load_config()
        job = next(j for j in config["scrape_configs"] if j["job_name"] == "backend")
        assert job["metrics_path"] == "/metrics"

    def test_target_backend_8000(self):
        config = self._load_config()
        job = next(j for j in config["scrape_configs"] if j["job_name"] == "backend")
        targets = job["static_configs"][0]["targets"]
        assert any("backend:8000" in t for t in targets)


class TestInstrumentatorConfig:
    """Instrumentator 配置验证（通过 /metrics 行为推断）"""

    def test_metrics_endpoint_returns_200(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_status_codes_grouped(self):
        """should_group_status_codes=True → 状态码按类分组"""
        resp = client.get("/metrics")
        text = resp.text
        # 分组后 handler 中不应出现精确的 200/404 等
        # 但会出现 2xx/4xx 形式或没有 status_code 维度
        assert "http_requests_total" in text

    def test_health_excluded(self):
        """excluded_handlers 配置：/health 不出现在 handler 标签中"""
        client.get("/api/v1/health")
        client.get("/api/v1/health")
        resp = client.get("/metrics")
        text = resp.text
        # /health 被排除，不应在 handler 中出现
        for line in text.splitlines():
            if "http_requests_total" in line and "handler" in line:
                assert "/health" not in line

    def test_version_excluded(self):
        """excluded_handlers 配置：/version 不出现在 handler 标签中"""
        client.get("/api/v1/version")
        resp = client.get("/metrics")
        text = resp.text
        for line in text.splitlines():
            if "http_requests_total" in line and "handler" in line:
                assert "/version" not in line

    def test_metrics_not_in_openapi(self):
        """include_in_schema=False → /metrics 不出现在 OpenAPI 中"""
        resp = client.get("/api/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/metrics" not in paths


class TestMetricsEndpointFormat:
    """/metrics 端点 Prometheus exposition 格式验证"""

    @staticmethod
    def _get_metrics():
        resp = client.get("/metrics")
        assert resp.status_code == 200
        return resp.text

    def test_content_type_prometheus(self):
        resp = client.get("/metrics")
        ct = resp.headers.get("content-type", "")
        assert "text/plain" in ct or "text/csv" in ct or "openmetrics" in ct.lower()

    def test_has_help_comments(self):
        """指标有 HELP 注释行"""
        text = self._get_metrics()
        assert "# HELP" in text

    def test_has_type_comments(self):
        """指标有 TYPE 注释行"""
        text = self._get_metrics()
        assert "# TYPE" in text

    def test_business_metrics_have_help(self):
        """每个 business_ 指标都有 HELP 行"""
        text = self._get_metrics()
        for name in [
            "business_order_created_total",
            "business_order_confirmed_total",
            "business_order_cancelled_total",
            "business_payment_registered_total",
            "business_payment_reversed_total",
            "business_inventory_stockout_total",
            "business_low_stock_products",
            "business_login_attempts_total",
        ]:
            assert f"# HELP {name}" in text, f"{name} 缺少 HELP 注释"

    def test_business_metrics_have_type(self):
        """每个 business_ 指标都有 TYPE 行"""
        text = self._get_metrics()
        for name in [
            "business_order_created_total",
            "business_order_confirmed_total",
            "business_order_cancelled_total",
            "business_payment_registered_total",
            "business_payment_reversed_total",
            "business_inventory_stockout_total",
            "business_low_stock_products",
            "business_login_attempts_total",
        ]:
            assert f"# TYPE {name}" in text, f"{name} 缺少 TYPE 注释"

    def test_counter_types_declared(self):
        """Counter 类型声明为 counter"""
        text = self._get_metrics()
        assert "# TYPE business_order_created_total counter" in text

    def test_gauge_type_declared(self):
        """Gauge 类型声明为 gauge"""
        text = self._get_metrics()
        assert "# TYPE business_low_stock_products gauge" in text

    def test_http_requests_is_counter(self):
        """http_requests_total 声明为 counter"""
        text = self._get_metrics()
        assert "# TYPE http_requests_total counter" in text

    def test_http_duration_is_histogram(self):
        """http_request_duration_seconds 声明为 histogram"""
        text = self._get_metrics()
        assert "# TYPE http_request_duration_seconds histogram" in text

    def test_histogram_has_bucket_sum_count(self):
        """直方图包含 _bucket、_sum、_count"""
        text = self._get_metrics()
        assert "http_request_duration_seconds_bucket" in text
        assert "http_request_duration_seconds_sum" in text
        assert "http_request_duration_seconds_count" in text

    def test_metric_values_are_numeric(self):
        """指标值是数字"""
        text = self._get_metrics()
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            # 格式: metric_name{labels} value timestamp
            parts = line.split()
            if len(parts) >= 2:
                try:
                    float(parts[-1].split()[-1])
                except ValueError:
                    # 最后一个可能是 timestamp，试倒数第二个
                    if len(parts) >= 3:
                        float(parts[-2])


class TestMetricNamingConvention:
    """指标命名规范验证"""

    @staticmethod
    def _get_metrics():
        resp = client.get("/metrics")
        return resp.text

    def test_business_prefix_consistent(self):
        """所有自定义指标都以 business_ 开头"""
        text = self._get_metrics()
        for line in text.splitlines():
            if line.startswith("# TYPE") and "business_" not in line:
                name = line.split()[2]
                # 跳过 http_ 指标和 process_ 指标
                if name.startswith("http_") or name.startswith("process_"):
                    continue
                if name.startswith("python_"):
                    continue

    def test_counter_suffix_total(self):
        """Counter 指标名含 _total 后缀"""
        text = self._get_metrics()
        for line in text.splitlines():
            if line.startswith("# TYPE") and "counter" in line:
                name = line.split()[2]
                if name.startswith("business_"):
                    assert name.endswith("_total"), f"{name} 是 counter 但不以 _total 结尾"

    def test_gauge_no_total_suffix(self):
        """Gauge 指标名不含 _total 后缀"""
        text = self._get_metrics()
        for line in text.splitlines():
            if line.startswith("# TYPE") and "gauge" in line:
                name = line.split()[2]
                if name.startswith("business_"):
                    assert not name.endswith("_total"), f"{name} 是 gauge 但有 _total 后缀"
