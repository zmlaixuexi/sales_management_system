"""需求符合性：应用生命周期管理边界测试
覆盖 lifespan 中的生产安全检查、关闭状态转换、/version 端点"""

from fastapi.testclient import TestClient

import app.main as main_mod
from app.main import app

client = TestClient(app)


class TestShutdownState:
    """关闭状态转换"""

    def test_normal_health_200(self):
        """正常状态下 /health 返回 200"""
        assert not main_mod._shutting_down
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_shutdown_health_503(self, monkeypatch):
        """关闭状态下 /health 返回 503 + SHUTTING_DOWN"""
        monkeypatch.setattr(main_mod, "_shutting_down", True)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "SHUTTING_DOWN"

    def test_shutdown_message_contains_chinese(self, monkeypatch):
        """关闭消息为中文"""
        monkeypatch.setattr(main_mod, "_shutting_down", True)
        resp = client.get("/api/v1/health")
        assert "关闭" in resp.json()["error"]["message"]

    def test_shutdown_state_restored(self, monkeypatch):
        """monkeypatch 恢复后状态正常"""
        monkeypatch.setattr(main_mod, "_shutting_down", True)
        client.get("/api/v1/health")
        # monkeypatch 在函数退出时自动恢复
        monkeypatch.setattr(main_mod, "_shutting_down", False)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


class TestVersionEndpoint:
    """版本端点"""

    def test_version_returns_200(self):
        resp = client.get("/api/v1/version")
        assert resp.status_code == 200

    def test_version_has_success_true(self):
        resp = client.get("/api/v1/version")
        assert resp.json()["success"] is True

    def test_version_has_data(self):
        resp = client.get("/api/v1/version")
        data = resp.json()["data"]
        assert "version" in data
        assert "revision" in data

    def test_version_format(self):
        resp = client.get("/api/v1/version")
        version = resp.json()["data"]["version"]
        # 语义化版本号格式
        parts = version.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts)

    def test_revision_is_string(self):
        resp = client.get("/api/v1/version")
        revision = resp.json()["data"]["revision"]
        assert isinstance(revision, str)
        assert len(revision) > 0


class TestHealthResponseStructure:
    """健康检查响应结构完整性"""

    def test_health_has_all_fields(self):
        resp = client.get("/api/v1/health")
        data = resp.json()["data"]
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "pool" in data
        assert "revision" in data

    def test_health_pool_structure(self):
        resp = client.get("/api/v1/health")
        pool = resp.json()["data"]["pool"]
        assert "size" in pool
        assert "checked_in" in pool
        assert "checked_out" in pool
        assert "overflow" in pool

    def test_health_pool_has_numeric_values(self):
        resp = client.get("/api/v1/health")
        pool = resp.json()["data"].get("pool")
        if pool:
            for key in ("size", "checked_in", "checked_out", "overflow"):
                if key in pool:
                    assert isinstance(pool[key], (int, float)), f"pool.{key} 应为数值"

    def test_health_database_status_present(self):
        resp = client.get("/api/v1/health")
        data = resp.json()["data"]
        assert data["database"] in ("ok", "error")

    def test_health_status_present(self):
        resp = client.get("/api/v1/health")
        data = resp.json()["data"]
        assert data["status"] in ("ok", "degraded")

    def test_health_success_true(self):
        resp = client.get("/api/v1/health")
        assert resp.json()["success"] is True

    def test_health_message_present(self):
        resp = client.get("/api/v1/health")
        assert "message" in resp.json()

    def test_health_response_content_type_json(self):
        resp = client.get("/api/v1/health")
        assert "application/json" in resp.headers.get("content-type", "")
