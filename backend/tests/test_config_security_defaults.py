"""安全加固：后端配置安全默认值回归测试
验证所有安全关键配置项的默认值和值域约束不变"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


class TestJWTSecurityDefaults:
    """JWT 安全配置默认值"""

    def test_jwt_algorithm_hs256(self):
        assert settings.JWT_ALGORITHM == "HS256"

    def test_jwt_issuer_non_empty(self):
        assert len(settings.JWT_ISSUER) > 0

    def test_jwt_audience_non_empty(self):
        assert len(settings.JWT_AUDIENCE) > 0

    def test_jwt_access_expire_positive(self):
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_jwt_access_expire_default_30(self):
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_jwt_refresh_expire_positive(self):
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_jwt_refresh_expire_default_7(self):
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_jwt_secret_key_min_length_8(self):
        assert len(settings.JWT_SECRET_KEY) >= 8

    def test_jwt_secret_rejects_empty(self):
        with pytest.raises(ValidationError, match="不能为空"):
            Settings(JWT_SECRET_KEY="")

    def test_jwt_secret_rejects_whitespace_only(self):
        with pytest.raises(ValidationError, match="不能为空"):
            Settings(JWT_SECRET_KEY="   ")

    def test_jwt_secret_rejects_short(self):
        with pytest.raises(ValidationError, match="不能少于 8"):
            Settings(JWT_SECRET_KEY="short")


class TestCORSSecurityDefaults:
    """CORS 安全配置默认值"""

    def test_cors_not_wildcard(self):
        assert "*" not in settings.CORS_ORIGINS.split(",")

    def test_cors_starts_with_protocol(self):
        for origin in settings.CORS_ORIGINS.split(","):
            origin = origin.strip()
            assert origin.startswith("http://") or origin.startswith("https://")

    def test_cors_non_empty(self):
        assert len(settings.CORS_ORIGINS.strip()) > 0

    def test_cors_rejects_wildcard(self):
        with pytest.raises(ValidationError, match="通配符"):
            Settings(CORS_ORIGINS="*")

    def test_cors_rejects_no_protocol(self):
        with pytest.raises(ValidationError, match="http"):
            Settings(CORS_ORIGINS="example.com")

    def test_cors_rejects_empty(self):
        with pytest.raises(ValidationError, match="不能为空"):
            Settings(CORS_ORIGINS="  ")

    def test_cors_accepts_multiple(self):
        s = Settings(CORS_ORIGINS="http://a.com,https://b.com")
        assert "http://a.com" in s.CORS_ORIGINS
        assert "https://b.com" in s.CORS_ORIGINS


class TestRateLimitDefaults:
    """速率限制配置默认值"""

    def test_rate_limit_max_positive(self):
        assert settings.RATE_LIMIT_MAX > 0

    def test_rate_limit_max_default_1000(self):
        assert settings.RATE_LIMIT_MAX == 1000

    def test_rate_limit_window_positive(self):
        assert settings.RATE_LIMIT_WINDOW > 0

    def test_rate_limit_window_default_60(self):
        assert settings.RATE_LIMIT_WINDOW == 60

    def test_rate_limit_max_rejects_negative(self):
        with pytest.raises(ValidationError, match="负数"):
            Settings(RATE_LIMIT_MAX=-1)

    def test_rate_limit_max_accepts_zero(self):
        s = Settings(RATE_LIMIT_MAX=0)
        assert s.RATE_LIMIT_MAX == 0

    def test_rate_limit_max_accepts_positive(self):
        s = Settings(RATE_LIMIT_MAX=500)
        assert s.RATE_LIMIT_MAX == 500


class TestBodyLimitDefaults:
    """请求体大小限制默认值"""

    def test_max_json_body_mb_positive(self):
        assert settings.MAX_JSON_BODY_MB > 0

    def test_max_json_body_mb_default_1(self):
        assert settings.MAX_JSON_BODY_MB == 1


class TestFileUploadDefaults:
    """文件上传安全配置默认值"""

    def test_max_image_size_positive(self):
        assert settings.MAX_IMAGE_SIZE_MB > 0

    def test_max_image_size_default_5(self):
        assert settings.MAX_IMAGE_SIZE_MB == 5

    def test_max_csv_import_size_positive(self):
        assert settings.MAX_CSV_IMPORT_SIZE_MB > 0

    def test_max_csv_import_rows_positive(self):
        assert settings.MAX_CSV_IMPORT_ROWS > 0

    def test_max_csv_import_rows_default_1000(self):
        assert settings.MAX_CSV_IMPORT_ROWS == 1000


class TestDatabasePoolDefaults:
    """数据库连接池配置默认值"""

    def test_pool_size_positive(self):
        assert settings.DB_POOL_SIZE > 0

    def test_pool_size_default_5(self):
        assert settings.DB_POOL_SIZE == 5

    def test_max_overflow_positive(self):
        assert settings.DB_MAX_OVERFLOW > 0

    def test_pool_recycle_positive(self):
        assert settings.DB_POOL_RECYCLE_SECONDS > 0


class TestAccountLockDefaults:
    """账户锁定配置默认值"""

    def test_login_fail_max_positive(self):
        assert settings.LOGIN_FAIL_MAX > 0

    def test_login_fail_window_positive(self):
        assert settings.LOGIN_FAIL_WINDOW_SECONDS > 0

    def test_account_lock_max_failures_positive(self):
        assert settings.ACCOUNT_LOCK_MAX_FAILURES > 0

    def test_account_lock_window_positive(self):
        assert settings.ACCOUNT_LOCK_WINDOW_SECONDS > 0


class TestHSTSDefaults:
    """HSTS 配置默认值"""

    def test_hsts_max_age_positive(self):
        assert settings.HSTS_MAX_AGE > 0

    def test_hsts_max_age_default_1_year(self):
        assert settings.HSTS_MAX_AGE == 31536000


class TestObservabilityDefaults:
    """可观测性配置默认值"""

    def test_slow_request_threshold_positive(self):
        assert settings.SLOW_REQUEST_THRESHOLD_MS > 0

    def test_slow_sql_threshold_positive(self):
        assert settings.SLOW_SQL_THRESHOLD_MS > 0

    def test_slow_request_default_1000(self):
        assert settings.SLOW_REQUEST_THRESHOLD_MS == 1000

    def test_slow_sql_default_200(self):
        assert settings.SLOW_SQL_THRESHOLD_MS == 200


class TestConfigSourceIntegrity:
    """配置源完整性验证"""

    def test_settings_is_singleton(self):
        """settings 模块级实例存在"""
        from app.core.config import settings as s
        assert s is not None

    def test_settings_has_all_expected_fields(self):
        """settings 包含所有预期字段"""
        expected = [
            "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ISSUER", "JWT_AUDIENCE",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
            "CORS_ORIGINS", "RATE_LIMIT_MAX", "RATE_LIMIT_WINDOW",
            "MAX_JSON_BODY_MB", "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_ROWS",
            "DB_POOL_SIZE", "LOGIN_FAIL_MAX", "ACCOUNT_LOCK_MAX_FAILURES",
            "HSTS_MAX_AGE", "SLOW_REQUEST_THRESHOLD_MS",
        ]
        for field in expected:
            assert hasattr(settings, field), f"缺少配置字段: {field}"

    def test_jwt_algorithm_is_known_good(self):
        """JWT 算法必须是已知安全的算法之一"""
        assert settings.JWT_ALGORITHM in {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}

    def test_app_env_default(self):
        """APP_ENV 默认为 development"""
        assert settings.APP_ENV == "development"
