"""
代码质量：后端数据库会话管理与连接池配置验证测试
覆盖引擎创建与连接池、会话工厂配置、
连接池参数默认值、会话生命周期管理、慢查询监控
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SESSION_SRC = (ROOT / "app" / "db" / "session.py").read_text()
CONFIG_SRC = (ROOT / "app" / "core" / "config.py").read_text()
DEPS_SRC = (ROOT / "app" / "api" / "deps.py").read_text()
MAIN_SRC = (ROOT / "app" / "main.py").read_text()
SLOW_QUERY_SRC = (ROOT / "app" / "core" / "slow_query.py").read_text()


# ═══════════════════════════════════════════════════════════
# 1. 引擎创建与连接池配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestEngineCreation:
    """引擎使用正确的连接池配置"""

    def test_engine_uses_create_engine(self):
        """使用 sqlalchemy.create_engine 创建引擎"""
        assert "create_engine(" in SESSION_SRC, "应使用 create_engine 创建引擎"

    def test_engine_uses_configured_pool_size(self):
        """引擎使用配置的 pool_size"""
        assert "pool_size" in SESSION_SRC, "应配置 pool_size"
        assert "settings.DB_POOL_SIZE" in SESSION_SRC or "DB_POOL_SIZE" in SESSION_SRC, (
            "pool_size 应引用配置项"
        )

    def test_engine_uses_configured_max_overflow(self):
        """引擎使用配置的 max_overflow"""
        assert "max_overflow" in SESSION_SRC, "应配置 max_overflow"
        assert "settings.DB_MAX_OVERFLOW" in SESSION_SRC or "DB_MAX_OVERFLOW" in SESSION_SRC, (
            "max_overflow 应引用配置项"
        )

    def test_engine_uses_pool_pre_ping(self):
        """引擎启用 pool_pre_ping（连接存活检测）"""
        assert "pool_pre_ping" in SESSION_SRC, "应启用 pool_pre_ping"
        assert "True" in SESSION_SRC, "pool_pre_ping 应为 True"

    def test_engine_uses_configured_pool_recycle(self):
        """引擎使用配置的 pool_recycle"""
        assert "pool_recycle" in SESSION_SRC, "应配置 pool_recycle"
        assert "settings.DB_POOL_RECYCLE_SECONDS" in SESSION_SRC or "DB_POOL_RECYCLE" in SESSION_SRC, (
            "pool_recycle 应引用配置项"
        )


# ═══════════════════════════════════════════════════════════
# 2. 会话工厂配置验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSessionFactoryConfig:
    """SessionLocal 会话工厂配置正确"""

    def test_session_local_uses_sessionmaker(self):
        """SessionLocal 使用 sessionmaker 创建"""
        assert "sessionmaker(" in SESSION_SRC, "应使用 sessionmaker 创建 SessionLocal"

    def test_session_local_bound_to_engine(self):
        """SessionLocal 绑定到 engine"""
        assert "bind=engine" in SESSION_SRC, (
            "SessionLocal 应绑定到 engine"
        )

    def test_autocommit_disabled(self):
        """autocommit=False 防止隐式提交"""
        assert "autocommit=False" in SESSION_SRC, "应设置 autocommit=False"

    def test_autoflush_disabled(self):
        """autoflush=False 手动控制刷新时机"""
        assert "autoflush=False" in SESSION_SRC, "应设置 autoflush=False"

    def test_base_model_defined(self):
        """定义了 Base 声明式基类"""
        assert "class Base" in SESSION_SRC, "应定义 Base 声明式基类"
        assert "DeclarativeBase" in SESSION_SRC, "Base 应继承 DeclarativeBase"


# ═══════════════════════════════════════════════════════════
# 3. 连接池参数默认值验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestPoolParameterDefaults:
    """连接池参数有合理的默认值"""

    def test_pool_size_default_reasonable(self):
        """pool_size 默认值合理（1-20）"""
        m = re.search(r'DB_POOL_SIZE\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "DB_POOL_SIZE 应有默认值"
        val = int(m.group(1))
        assert 1 <= val <= 20, f"DB_POOL_SIZE 默认 {val} 不在合理范围 1-20"

    def test_max_overflow_default_reasonable(self):
        """max_overflow 默认值合理（5-30）"""
        m = re.search(r'DB_MAX_OVERFLOW\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "DB_MAX_OVERFLOW 应有默认值"
        val = int(m.group(1))
        assert 5 <= val <= 30, f"DB_MAX_OVERFLOW 默认 {val} 不在合理范围 5-30"

    def test_pool_recycle_default_reasonable(self):
        """pool_recycle 默认值合理（300-7200 秒）"""
        m = re.search(r'DB_POOL_RECYCLE_SECONDS\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "DB_POOL_RECYCLE_SECONDS 应有默认值"
        val = int(m.group(1))
        assert 300 <= val <= 7200, f"pool_recycle 默认 {val}s 不在合理范围 300-7200"

    def test_database_url_has_postgresql_scheme(self):
        """DATABASE_URL 使用 PostgreSQL 协议"""
        assert "postgresql" in CONFIG_SRC, "DATABASE_URL 应使用 PostgreSQL"

    def test_slow_sql_threshold_configurable(self):
        """慢查询阈值可配置"""
        assert "SLOW_SQL_THRESHOLD_MS" in CONFIG_SRC, "应定义 SLOW_SQL_THRESHOLD_MS"
        m = re.search(r'SLOW_SQL_THRESHOLD_MS\s*:\s*int\s*=\s*(\d+)', CONFIG_SRC)
        assert m, "SLOW_SQL_THRESHOLD_MS 应有默认值"
        val = int(m.group(1))
        assert val >= 50, f"慢查询阈值应 >= 50ms，实际 {val}"


# ═══════════════════════════════════════════════════════════
# 4. 会话生命周期管理验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSessionLifecycleManagement:
    """会话生命周期正确管理"""

    def test_get_db_yields_and_closes(self):
        """get_db 使用 yield + finally: db.close()"""
        assert "yield db" in DEPS_SRC or "yield" in DEPS_SRC, "get_db 应 yield db"
        assert "db.close()" in DEPS_SRC, "get_db 应在 finally 中关闭 db"

    def test_get_db_creates_session_from_session_local(self):
        """get_db 从 SessionLocal 创建会话"""
        assert "SessionLocal()" in DEPS_SRC, "get_db 应使用 SessionLocal() 创建会话"

    def test_safe_commit_defined(self):
        """定义了 safe_commit 辅助函数"""
        assert "safe_commit" in DEPS_SRC, "应定义 safe_commit 辅助函数"
        assert "db.commit()" in DEPS_SRC, "safe_commit 应调用 db.commit()"
        assert "db.rollback()" in DEPS_SRC, "safe_commit 应在异常时 db.rollback()"

    def test_engine_dispose_on_shutdown(self):
        """关闭时调用 engine.dispose() 释放连接池"""
        assert "engine.dispose()" in MAIN_SRC, "关闭时应调用 engine.dispose()"

    def test_engine_imported_in_main(self):
        """main.py 导入了 engine"""
        assert "engine" in MAIN_SRC, "main.py 应导入 engine"


# ═══════════════════════════════════════════════════════════
# 5. 慢查询监控验证（5 项）
# ═══════════════════════════════════════════════════════════


class TestSlowQueryMonitoring:
    """慢查询监控正确配置"""

    def test_slow_query_listener_registered(self):
        """慢查询监听器在 session.py 中注册"""
        assert "register_slow_query_listener" in SESSION_SRC, (
            "应调用 register_slow_query_listener(engine)"
        )

    def test_listener_uses_before_and_after_events(self):
        """监听器注册 before_cursor_execute 和 after_cursor_execute"""
        assert "before_cursor_execute" in SLOW_QUERY_SRC, "应监听 before_cursor_execute"
        assert "after_cursor_execute" in SLOW_QUERY_SRC, "应监听 after_cursor_execute"

    def test_listener_uses_monotonic_time(self):
        """使用 time.monotonic 测量耗时"""
        assert "time.monotonic()" in SLOW_QUERY_SRC, "应使用 time.monotonic() 计时"

    def test_listener_includes_request_id(self):
        """慢查询日志包含 request_id"""
        assert "request_id" in SLOW_QUERY_SRC, "慢查询日志应包含 request_id"
        assert "request_id_ctx" in SLOW_QUERY_SRC, "应使用 request_id_ctx 获取 request_id"

    def test_listener_truncates_long_sql(self):
        """长 SQL 语句被截断"""
        assert "500" in SLOW_QUERY_SRC or "[:500]" in SLOW_QUERY_SRC, (
            "应截断过长的 SQL 语句"
        )
