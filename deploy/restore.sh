#!/usr/bin/env bash
# PostgreSQL + 上传文件恢复脚本
# 使用方式：./restore.sh <备份文件> [上传文件备份]
# 示例：./restore.sh ./backups/sales_mgmt_20260430_120000.sql.gz ./backups/uploads_20260430_120000.tar.gz

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "用法: $0 <备份文件.sql.gz> [上传文件.tar.gz]"
    exit 1
fi

BACKUP_FILE="$1"
UPLOADS_BACKUP="${2:-}"
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
UPLOAD_DIR="${UPLOAD_DIR:-/app/uploads}"

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

echo "[$(date)] 数据库恢复完成"

# 恢复上传文件
if [ -n "${UPLOADS_BACKUP}" ]; then
    if [ -f "${UPLOADS_BACKUP}" ]; then
        echo "[$(date)] 开始恢复上传文件..."
        UPLOADS_PARENT="$(dirname "${UPLOAD_DIR}")"
        mkdir -p "${UPLOADS_PARENT}"
        tar -xzf "${UPLOADS_BACKUP}" -C "${UPLOADS_PARENT}"
        echo "[$(date)] 上传文件恢复完成: ${UPLOAD_DIR}"
    else
        echo "[$(date)] 警告: 上传文件备份不存在: ${UPLOADS_BACKUP}"
    fi
fi
