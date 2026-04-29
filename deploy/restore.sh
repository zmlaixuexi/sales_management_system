#!/usr/bin/env bash
# PostgreSQL 恢复脚本
# 使用方式：./restore.sh <备份文件>
# 示例：./restore.sh ./backups/sales_mgmt_20260430_120000.sql.gz

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "用法: $0 <备份文件.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "错误: 文件 ${BACKUP_FILE} 不存在"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/../.env" ]; then
    source "${SCRIPT_DIR}/../.env"
fi

PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-sales_management}"

echo "[$(date)] 警告: 此操作将清空并恢复数据库 ${PG_DB}！"
read -p "确认继续? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "已取消"
    exit 0
fi

echo "[$(date)] 开始从 ${BACKUP_FILE} 恢复..."

if docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" ps postgres &>/dev/null; then
    # Docker 环境
    docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" exec -T postgres \
        sh -c "psql -U ${PG_USER} -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${PG_DB}';\" 2>/dev/null; \
               dropdb --if-exists -U ${PG_USER} ${PG_DB}; \
               createdb -U ${PG_USER} ${PG_DB}"
    gunzip -c "${BACKUP_FILE}" | docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" exec -T postgres \
        psql -U "${PG_USER}" -d "${PG_DB}"
else
    # 本地环境
    PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST:-localhost}" -U "${PG_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${PG_DB}';" 2>/dev/null
    PGPASSWORD="${POSTGRES_PASSWORD:-}" dropdb --if-exists -h "${PG_HOST:-localhost}" -U "${PG_USER}" "${PG_DB}"
    PGPASSWORD="${POSTGRES_PASSWORD:-}" createdb -h "${PG_HOST:-localhost}" -U "${PG_USER}" "${PG_DB}"
    gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST:-localhost}" -U "${PG_USER}" -d "${PG_DB}"
fi

echo "[$(date)] 恢复完成"
