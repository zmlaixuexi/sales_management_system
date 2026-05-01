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

# 清理旧备份：保留最近 7 天每日备份 + 最近 4 周每周保留一份
# 删除超过 7 天的非周一备份
find "${BACKUP_DIR}" -name "sales_mgmt_*.sql.gz" -mtime +7 ! -name "*_周一*" | while read -r f; do
    # 检查是否为周一（保留周一备份 4 周）
    FILE_DATE=$(echo "$f" | grep -oP '\d{8}' | head -1)
    if [ -n "${FILE_DATE}" ]; then
        DOW=$(date -d "${FILE_DATE:0:4}-${FILE_DATE:4:2}-${FILE_DATE:6:2}" +%u 2>/dev/null || echo "0")
        if [ "${DOW}" != "1" ]; then
            rm -f "$f"
        fi
    fi
done
# 删除超过 28 天的周一备份
find "${BACKUP_DIR}" -name "sales_mgmt_*.sql.gz" -mtime +28 -delete
echo "[$(date)] 已清理旧备份（保留 7 天每日 + 4 周每周）"
