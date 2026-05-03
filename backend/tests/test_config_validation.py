"""配置校验测试 — 验证关键配置项的值域约束"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestPositiveInt:
    """JWT_ACCESS_TOKEN_EXPIRE_MINUTES / JWT_REFRESH_TOKEN_EXPIRE_DAYS 必须为正整数"""

    def test_access_token_expire_zero_rejected(self):
        with pytest.raises(ValidationError, match="正整数"):
            Settings(JWT_ACCESS_TOKEN_EXPIRE_MINUTES=0)

    def test_access_token_expire_negative_rejected(self):
        with pytest.raises(ValidationError, match="正整数"):
            Settings(JWT_ACCESS_TOKEN_EXPIRE_MINUTES=-1)

    def test_refresh_token_days_zero_rejected(self):
        with pytest.raises(ValidationError, match="正整数"):
            Settings(JWT_REFRESH_TOKEN_EXPIRE_DAYS=0)

    def test_valid_values_accepted(self):
        s = Settings(JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60, JWT_REFRESH_TOKEN_EXPIRE_DAYS=30)
        assert s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60
        assert s.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 30


class TestStrictlyPositive:
    """DB_POOL_SIZE / MAX_IMAGE_SIZE_MB / MAX_CSV_IMPORT_ROWS 必须大于 0"""

    @pytest.mark.parametrize("field", ["DB_POOL_SIZE", "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_ROWS"])
    def test_zero_rejected(self, field: str):
        with pytest.raises(ValidationError, match="大于 0"):
            Settings(**{field: 0})

    @pytest.mark.parametrize("field", ["DB_POOL_SIZE", "MAX_IMAGE_SIZE_MB", "MAX_CSV_IMPORT_ROWS"])
    def test_negative_rejected(self, field: str):
        with pytest.raises(ValidationError, match="大于 0"):
            Settings(**{field: -5})

    @pytest.mark.parametrize("field,value", [
        ("DB_POOL_SIZE", 10),
        ("MAX_IMAGE_SIZE_MB", 5),
        ("MAX_CSV_IMPORT_ROWS", 500),
    ])
    def test_valid_values_accepted(self, field: str, value: int):
        s = Settings(**{field: value})
        assert getattr(s, field) == value


class TestNonNegative:
    """RATE_LIMIT_MAX 不能为负数"""

    def test_negative_rejected(self):
        with pytest.raises(ValidationError, match="负数"):
            Settings(RATE_LIMIT_MAX=-1)

    def test_zero_accepted(self):
        s = Settings(RATE_LIMIT_MAX=0)
        assert s.RATE_LIMIT_MAX == 0

    def test_positive_accepted(self):
        s = Settings(RATE_LIMIT_MAX=100)
        assert s.RATE_LIMIT_MAX == 100
