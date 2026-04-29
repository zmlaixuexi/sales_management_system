#!/usr/bin/env bash
# PostgreSQL 备份脚本
# 使用方式：./backup.sh [备份目录]
# 示例：./backup.sh /data/backups

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sales_mgmt_${TIMESTAMP}.sql.gz"

# 从 .env 或环境变量读取配置
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/../.env" ]; then
    source "${SCRIPT_DIR}/../.env"
fi

PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-sales_management}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] 开始备份数据库 ${PG_DB}..."

if docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" ps postgres &>/dev/null; then
    # Docker 环境备份
    docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" exec -T postgres \
        pg_dump -U "${PG_USER}" "${PG_DB}" | gzip > "${BACKUP_FILE}"
else
    # 本地环境备份
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" "${PG_DB}" | gzip > "${BACKUP_FILE}"
fi

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] 备份完成: ${BACKUP_FILE} (${FILE_SIZE})"

# 清理 30 天前的备份
find "${BACKUP_DIR}" -name "sales_mgmt_*.sql.gz" -mtime +30 -delete
echo "[$(date)] 已清理 30 天前的旧备份"
