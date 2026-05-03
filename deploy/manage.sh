#!/usr/bin/env bash
# 部署管理脚本
# 使用方式：
#   ./deploy/manage.sh start        — 启动生产环境
#   ./deploy/manage.sh stop         — 停止服务
#   ./deploy/manage.sh restart      — 重启服务
#   ./deploy/manage.sh status       — 查看服务状态
#   ./deploy/manage.sh logs [svc]   — 查看日志（可选指定服务）
#   ./deploy/manage.sh migrate      — 仅执行数据库迁移
#   ./deploy/manage.sh check        — 运行部署前检查

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "  ${CYAN}▸${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; }

require_env() {
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        err ".env 文件不存在"
        info "请复制 .env.example 并填写配置：cp .env.example .env"
        exit 1
    fi
}

cd "${PROJECT_DIR}"

case "${1:-help}" in
    start)
        echo ""
        info "启动销售管理系统..."
        require_env

        # 部署前检查（快速模式，跳过测试）
        info "运行部署前检查..."
        if ! "${SCRIPT_DIR}/pre-deploy-check.sh" --skip-tests --skip-build; then
            err "部署前检查未通过，请修复后重试"
            exit 1
        fi
        echo ""

        # 构建并启动
        info "构建并启动容器..."
        docker compose -f "${COMPOSE_FILE}" up -d --build 2>&1

        echo ""
        ok "服务已启动"
        info "等待健康检查..."
        sleep 5

        # 显示状态
        docker compose -f "${COMPOSE_FILE}" ps
        echo ""
        ok "访问地址：http://localhost:${HTTP_PORT:-80}"
        echo ""
        ;;

    stop)
        echo ""
        info "停止服务..."
        docker compose -f "${COMPOSE_FILE}" down 2>&1
        ok "服务已停止"
        echo ""
        ;;

    restart)
        echo ""
        info "重启服务..."
        docker compose -f "${COMPOSE_FILE}" restart 2>&1
        ok "服务已重启"
        echo ""
        ;;

    status)
        echo ""
        docker compose -f "${COMPOSE_FILE}" ps
        echo ""
        # 检查健康状态
        HEALTHY=$(docker compose -f "${COMPOSE_FILE}" ps --format json 2>/dev/null \
            | grep -c '"running"' || true)
        if [ "${HEALTHY}" -ge 3 ]; then
            ok "所有服务运行正常"
        else
            warn "部分服务可能未就绪，请检查日志"
        fi
        echo ""
        ;;

    logs)
        SERVICE="${2:-}"
        if [ -n "${SERVICE}" ]; then
            docker compose -f "${COMPOSE_FILE}" logs -f --tail=100 "${SERVICE}"
        else
            docker compose -f "${COMPOSE_FILE}" logs -f --tail=50
        fi
        ;;

    migrate)
        echo ""
        info "执行数据库迁移..."
        docker compose -f "${COMPOSE_FILE}" exec backend alembic upgrade head 2>&1
        ok "迁移完成"
        echo ""
        ;;

    check)
        "${SCRIPT_DIR}/pre-deploy-check.sh" "${@:2}"
        ;;

    help|*)
        echo ""
        echo "销售管理系统 — 部署管理脚本"
        echo ""
        echo "用法: $0 <命令>"
        echo ""
        echo "命令："
        echo "  start          部署前检查 + 构建并启动生产环境"
        echo "  stop           停止所有服务"
        echo "  restart        重启所有服务"
        echo "  status         查看服务运行状态"
        echo "  logs [服务名]  查看日志（默认全部，可指定 backend/nginx/postgres）"
        echo "  migrate        执行数据库迁移（alembic upgrade head）"
        echo "  check          运行完整部署前检查"
        echo ""
        echo "示例："
        echo "  $0 start"
        echo "  $0 logs backend"
        echo "  $0 check --skip-build"
        echo ""
        ;;
esac
