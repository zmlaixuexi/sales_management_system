#!/usr/bin/env bash
# 部署回滚脚本
# 使用方式：./rollback.sh <git-commit-or-tag> [备份目录]
# 示例：./rollback.sh v1.2.0 /data/backups
#
# 回滚流程：
#   1. 自动备份当前数据库
#   2. 回退代码到指定版本
#   3. 重建并重启容器
#   4. 运行数据库迁移

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "用法: $0 <git-commit|tag> [备份目录]"
    echo "示例: $0 v1.2.0"
    echo "      $0 abc1234 ./backups"
    exit 1
fi

TARGET="$1"
BACKUP_DIR="${2:-./backups}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

# 检查目标版本是否存在
if ! git rev-parse "${TARGET}" &>/dev/null; then
    echo "错误: Git 版本 ${TARGET} 不存在"
    exit 1
fi

TARGET_SHORT=$(git rev-parse --short "${TARGET}")
CURRENT_SHORT=$(git rev-parse --short HEAD)

echo "=========================================="
echo "  部署回滚"
echo "=========================================="
echo "  当前版本: ${CURRENT_SHORT} ($(git log -1 --format='%s' HEAD))"
echo "  目标版本: ${TARGET_SHORT} (${TARGET})"
echo "=========================================="
echo ""
echo "警告: 此操作将回滚代码并重建容器！"
echo "       数据库将自动备份，但不会自动回滚。"
read -p "确认继续? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# 步骤 1：自动备份当前数据库
echo ""
echo "[$(date)] 步骤 1/4: 备份当前数据库..."
bash "${SCRIPT_DIR}/backup.sh" "${BACKUP_DIR}"
echo "[$(date)] 备份完成"

# 步骤 2：回退代码
echo ""
echo "[$(date)] 步骤 2/4: 回退代码到 ${TARGET_SHORT}..."
git checkout "${TARGET}"
echo "[$(date)] 代码已切换到 ${TARGET_SHORT}"

# 步骤 3：重建容器
echo ""
echo "[$(date)] 步骤 3/4: 重建并重启容器..."
docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" build --no-cache
docker compose -f "${SCRIPT_DIR}/docker-compose.prod.yml" up -d
echo "[$(date)] 容器已重建并启动"

# 步骤 4：等待后端就绪并运行迁移
echo ""
echo "[$(date)] 步骤 4/4: 等待后端就绪并运行数据库迁移..."
MAX_WAIT=60
WAITED=0
while [ ${WAITED} -lt ${MAX_WAIT} ]; do
    if curl -sf http://localhost:80/health >/dev/null 2>&1; then
        echo "[$(date)] 后端已就绪"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  等待后端启动... (${WAITED}s/${MAX_WAIT}s)"
done

if [ ${WAITED} -ge ${MAX_WAIT} ]; then
    echo "[$(date)] 警告: 后端未在 ${MAX_WAIT}s 内就绪，请手动检查"
fi

echo ""
echo "=========================================="
echo "  回滚完成"
echo "=========================================="
echo "  当前版本: ${TARGET_SHORT} (${TARGET})"
echo "  数据库备份: ${BACKUP_DIR}"
echo ""
echo "  如需回滚数据库，请运行:"
echo "  ./restore.sh ${BACKUP_DIR}/sales_mgmt_*.sql.gz"
echo "=========================================="
