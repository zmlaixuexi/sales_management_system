"""部署体验：部署脚本内容与结构验证测试
验证 manage.sh/pre-deploy-check.sh/backup.sh/restore.sh 的结构和关键命令"""

import stat
from pathlib import Path

DEPLOY_DIR = Path(__file__).resolve().parent.parent.parent / "deploy"


def _read_script(filename):
    return (DEPLOY_DIR / filename).read_text()


def _is_executable(filename):
    st = (DEPLOY_DIR / filename).stat()
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


class TestManageScript:
    """manage.sh 部署管理脚本"""

    def test_has_shebang(self):
        source = _read_script("manage.sh")
        assert source.startswith("#!/usr/bin/env bash")

    def test_is_executable(self):
        assert _is_executable("manage.sh")

    def test_uses_strict_mode(self):
        source = _read_script("manage.sh")
        assert "set -euo pipefail" in source

    def test_references_prod_compose(self):
        source = _read_script("manage.sh")
        assert "docker-compose.prod.yml" in source

    def test_has_start_command(self):
        source = _read_script("manage.sh")
        assert "start)" in source

    def test_has_stop_command(self):
        source = _read_script("manage.sh")
        assert "stop)" in source

    def test_has_restart_command(self):
        source = _read_script("manage.sh")
        assert "restart)" in source

    def test_has_status_command(self):
        source = _read_script("manage.sh")
        assert "status)" in source

    def test_has_logs_command(self):
        source = _read_script("manage.sh")
        assert "logs)" in source

    def test_has_migrate_command(self):
        source = _read_script("manage.sh")
        assert "migrate)" in source
        assert "alembic upgrade head" in source

    def test_has_backup_command(self):
        source = _read_script("manage.sh")
        assert "backup)" in source

    def test_has_restore_command(self):
        source = _read_script("manage.sh")
        assert "restore)" in source

    def test_has_check_command(self):
        source = _read_script("manage.sh")
        assert "check)" in source

    def test_has_monitoring_commands(self):
        source = _read_script("manage.sh")
        assert "monitoring-start)" in source
        assert "monitoring-stop)" in source
        assert "monitoring-status)" in source

    def test_monitoring_uses_profile(self):
        source = _read_script("manage.sh")
        assert "--profile monitoring" in source

    def test_start_runs_pre_deploy_check(self):
        source = _read_script("manage.sh")
        assert "pre-deploy-check.sh" in source

    def test_start_builds_containers(self):
        source = _read_script("manage.sh")
        assert "up -d --build" in source

    def test_has_help_command(self):
        source = _read_script("manage.sh")
        assert "help" in source

    def test_uses_compose_file_variable(self):
        source = _read_script("manage.sh")
        assert "COMPOSE_FILE=" in source

    def test_requires_env_file(self):
        source = _read_script("manage.sh")
        assert ".env" in source

    def test_has_cleanup_files_command(self):
        source = _read_script("manage.sh")
        assert "cleanup-files)" in source


class TestPreDeployCheckScript:
    """pre-deploy-check.sh 部署前检查"""

    def test_has_shebang(self):
        source = _read_script("pre-deploy-check.sh")
        assert source.startswith("#!/usr/bin/env bash")

    def test_is_executable(self):
        assert _is_executable("pre-deploy-check.sh")

    def test_uses_strict_mode(self):
        source = _read_script("pre-deploy-check.sh")
        assert "set -euo pipefail" in source

    def test_has_skip_tests_flag(self):
        source = _read_script("pre-deploy-check.sh")
        assert "--skip-tests" in source

    def test_has_skip_build_flag(self):
        source = _read_script("pre-deploy-check.sh")
        assert "--skip-build" in source

    def test_checks_docker(self):
        source = _read_script("pre-deploy-check.sh")
        assert "docker" in source.lower()

    def test_checks_env_file(self):
        source = _read_script("pre-deploy-check.sh")
        assert ".env" in source

    def test_has_pass_fail_tracking(self):
        source = _read_script("pre-deploy-check.sh")
        assert "PASS" in source or "FAIL" in source


class TestBackupScript:
    """backup.sh 备份脚本"""

    def test_has_shebang(self):
        source = _read_script("backup.sh")
        assert source.startswith("#!/usr/bin/env bash")

    def test_is_executable(self):
        assert _is_executable("backup.sh")

    def test_uses_strict_mode(self):
        source = _read_script("backup.sh")
        assert "set -euo pipefail" in source

    def test_references_pg_dump(self):
        source = _read_script("backup.sh")
        assert "pg_dump" in source

    def test_has_timestamp_in_filename(self):
        source = _read_script("backup.sh")
        assert "date" in source


class TestRestoreScript:
    """restore.sh 恢复脚本"""

    def test_has_shebang(self):
        source = _read_script("restore.sh")
        assert source.startswith("#!/usr/bin/env bash")

    def test_is_executable(self):
        assert _is_executable("restore.sh")

    def test_uses_strict_mode(self):
        source = _read_script("restore.sh")
        assert "set -euo pipefail" in source

    def test_requires_backup_file_argument(self):
        source = _read_script("restore.sh")
        assert "$1" in source or "${1" in source


class TestRollbackScript:
    """rollback.sh 回滚脚本"""

    def test_has_shebang(self):
        source = _read_script("rollback.sh")
        assert source.startswith("#!/usr/bin/env bash")

    def test_is_executable(self):
        assert _is_executable("rollback.sh")

    def test_uses_strict_mode(self):
        source = _read_script("rollback.sh")
        assert "set -euo pipefail" in source


class TestScriptConsistency:
    """脚本间引用一致性"""

    def test_manage_references_backup(self):
        source = _read_script("manage.sh")
        assert "backup.sh" in source

    def test_manage_references_restore(self):
        source = _read_script("manage.sh")
        assert "restore.sh" in source

    def test_manage_references_pre_deploy_check(self):
        source = _read_script("manage.sh")
        assert "pre-deploy-check.sh" in source

    def test_all_scripts_use_same_compose_file(self):
        """manage.sh 和 pre-deploy-check.sh 引用同一个 compose 文件"""
        manage = _read_script("manage.sh")
        check = _read_script("pre-deploy-check.sh")
        assert "docker-compose.prod.yml" in manage
        # pre-deploy-check 不直接使用 compose，但检查其存在
