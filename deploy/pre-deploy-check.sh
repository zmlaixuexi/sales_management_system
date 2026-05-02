#!/usr/bin/env bash
# 部署前检查脚本
# 使用方式：./deploy/pre-deploy-check.sh [--skip-tests] [--skip-build]
#
# 检查项目：
#   1. 必要文件完整性
#   2. 环境变量配置
#   3. Docker 可用性
#   4. 后端代码检查（ruff、mypy、测试）
#   5. 前端构建检查
#   6. 数据库迁移一致性
#   7. 端口可用性
#   8. 磁盘空间

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0
SKIP=0

SKIP_TESTS=false
SKIP_BUILD=false

for arg in "$@"; do
    case "${arg}" in
        --skip-tests) SKIP_TESTS=true ;;
        --skip-build) SKIP_BUILD=true ;;
        -h|--help)
            echo "用法: $0 [--skip-tests] [--skip-build]"
            echo ""
            echo "选项:"
            echo "  --skip-tests   跳过后端测试"
            echo "  --skip-build   跳过前端构建"
            exit 0
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

echo "=========================================="
echo "  部署前检查"
echo "=========================================="
echo "  项目目录: ${PROJECT_DIR}"
echo "  检查时间: $(date)"
echo "=========================================="
echo ""

pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    PASS=$((PASS + 1))
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
    FAIL=$((FAIL + 1))
}

warn() {
    echo -e "  ${YELLOW}!${NC} $1"
    WARN=$((WARN + 1))
}

skip() {
    echo -e "  ${YELLOW}○${NC} $1"
    SKIP=$((SKIP + 1))
}

# ==========================================
# 1. 必要文件完整性
# ==========================================
echo "--- 1/8 文件完整性 ---"

REQUIRED_FILES=(
    "deploy/docker-compose.prod.yml"
    "deploy/nginx.conf"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "backend/alembic.ini"
    "backend/alembic/env.py"
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "${f}" ]; then
        pass "${f} 存在"
    else
        fail "${f} 缺失"
    fi
done

# 检查 alembic 迁移目录有文件
MIGRATION_COUNT=$(find backend/alembic/versions -name "*.py" 2>/dev/null | wc -l)
if [ "${MIGRATION_COUNT}" -gt 0 ]; then
    pass "迁移文件 ${MIGRATION_COUNT} 个"
else
    fail "无迁移文件"
fi

echo ""

# ==========================================
# 2. 环境变量配置
# ==========================================
echo "--- 2/8 环境变量 ---"

if [ -f ".env" ]; then
    pass ".env 文件存在"

    # 检查生产必需变量
    if grep -q "^JWT_SECRET_KEY=change-me" .env 2>/dev/null; then
        fail "JWT_SECRET_KEY 仍为默认值 'change-me'，生产环境必须修改"
    elif grep -q "^JWT_SECRET_KEY=." .env 2>/dev/null; then
        pass "JWT_SECRET_KEY 已设置"
    else
        warn "JWT_SECRET_KEY 未在 .env 中设置（将使用 docker-compose 中的必填校验）"
    fi

    if grep -q "^POSTGRES_PASSWORD=postgres$" .env 2>/dev/null; then
        fail "POSTGRES_PASSWORD 仍为默认值 'postgres'，生产环境必须修改"
    elif grep -q "^POSTGRES_PASSWORD=." .env 2>/dev/null; then
        pass "POSTGRES_PASSWORD 已设置"
    else
        warn "POSTGRES_PASSWORD 未在 .env 中设置（将使用 docker-compose 中的必填校验）"
    fi

    if grep -q "^APP_ENV=production" .env 2>/dev/null; then
        pass "APP_ENV=production"
    else
        warn "APP_ENV 不是 production（当前可能是开发模式）"
    fi
else
    warn ".env 文件不存在（将依赖环境变量或 docker-compose 必填校验）"
fi

echo ""

# ==========================================
# 3. Docker 可用性
# ==========================================
echo "--- 3/8 Docker 环境 ---"

if command -v docker &>/dev/null; then
    pass "docker 已安装 ($(docker --version 2>/dev/null | grep -oP 'Docker version \K[\d.]+'))"

    if docker info &>/dev/null; then
        pass "Docker 守护进程运行中"
    else
        fail "Docker 守护进程未运行"
    fi
else
    fail "docker 未安装"
fi

if docker compose version &>/dev/null; then
    pass "docker compose 可用 ($(docker compose version --short 2>/dev/null))"
else
    fail "docker compose 不可用"
fi

echo ""

# ==========================================
# 4. 后端代码质量
# ==========================================
echo "--- 4/8 后端代码检查 ---"

if command -v ruff &>/dev/null; then
    RUFF_OUTPUT=$(cd backend && ruff check . 2>&1) && RUFF_RC=0 || RUFF_RC=$?
    if [ "${RUFF_RC}" -eq 0 ]; then
        pass "ruff 检查通过"
    else
        fail "ruff 检查失败"
        echo "  ${RUFF_OUTPUT}" | head -5
    fi
else
    warn "ruff 未安装，跳过 lint 检查"
fi

if command -v mypy &>/dev/null; then
    MYPY_OUTPUT=$(cd backend && mypy app/ 2>&1) && MYPY_RC=0 || MYPY_RC=$?
    if [ "${MYPY_RC}" -eq 0 ]; then
        pass "mypy 类型检查通过"
    else
        fail "mypy 类型检查失败"
        echo "  ${MYPY_OUTPUT}" | tail -5
    fi
else
    warn "mypy 未安装，跳过类型检查"
fi

if [ "${SKIP_TESTS}" = "true" ]; then
    skip "后端测试（已跳过）"
else
    echo -n "  运行后端测试..."
    TEST_OUTPUT=$(cd backend && python -m pytest --tb=short -q 2>&1) && TEST_RC=0 || TEST_RC=$?
    if [ "${TEST_RC}" -eq 0 ]; then
        TEST_COUNT=$(echo "${TEST_OUTPUT}" | grep -oP '\d+ passed' | head -1)
        echo -e "\r  ${GREEN}✓${NC} 后端测试通过 (${TEST_COUNT})"
        PASS=$((PASS + 1))
    else
        echo -e "\r  ${RED}✗${NC} 后端测试失败"
        FAIL=$((FAIL + 1))
        echo "${TEST_OUTPUT}" | tail -10 | sed 's/^/    /'
    fi
fi

echo ""

# ==========================================
# 5. 前端构建
# ==========================================
echo "--- 5/8 前端构建 ---"

if [ "${SKIP_BUILD}" = "true" ]; then
    skip "前端构建（已跳过）"
else
    if [ -f "frontend/package.json" ]; then
        if [ -d "frontend/node_modules" ]; then
            pass "node_modules 存在"
        else
            echo -n "  安装前端依赖..."
            (cd frontend && npm install --silent 2>&1) && NPM_RC=0 || NPM_RC=$?
            if [ "${NPM_RC}" -eq 0 ]; then
                echo -e "\r  ${GREEN}✓${NC} 前端依赖安装完成"
                PASS=$((PASS + 1))
            else
                echo -e "\r  ${RED}✗${NC} 前端依赖安装失败"
                FAIL=$((FAIL + 1))
            fi
        fi

        echo -n "  构建前端..."
        BUILD_OUTPUT=$(cd frontend && npx vite build 2>&1) && BUILD_RC=0 || BUILD_RC=$?
        if [ "${BUILD_RC}" -eq 0 ]; then
            BUILD_TIME=$(echo "${BUILD_OUTPUT}" | grep -oP 'built in \K[\dms]+')
            echo -e "\r  ${GREEN}✓${NC} 前端构建成功 (${BUILD_TIME:-ok})"
            PASS=$((PASS + 1))
        else
            echo -e "\r  ${RED}✗${NC} 前端构建失败"
            FAIL=$((FAIL + 1))
            echo "${BUILD_OUTPUT}" | tail -5 | sed 's/^/    /'
        fi
    else
        fail "frontend/package.json 不存在"
    fi
fi

echo ""

# ==========================================
# 6. 数据库迁移一致性
# ==========================================
echo "--- 6/8 数据库迁移 ---"

if [ -f "backend/alembic.ini" ]; then
    # 检查迁移文件链完整性（离线）
    ALEMBIC_OUTPUT=$(cd backend && python -m alembic heads 2>&1) && ALEMBIC_RC=0 || ALEMBIC_RC=$?
    if [ "${ALEMBIC_RC}" -eq 0 ]; then
        HEAD_COUNT=$(echo "${ALEMBIC_OUTPUT}" | grep -c ":" || true)
        if [ "${HEAD_COUNT}" -le 1 ]; then
            pass "迁移链线性无分叉"
        else
            fail "迁移链存在 ${HEAD_COUNT} 个头（分叉），需要合并"
        fi
    else
        fail "alembic heads 检查失败"
    fi

    # 检查模型与迁移是否一致（需要数据库连接）
    CHECK_OUTPUT=$(cd backend && python -m alembic check 2>&1) && CHECK_RC=0 || CHECK_RC=$?
    if [ "${CHECK_RC}" -eq 0 ]; then
        pass "模型与迁移一致（alembic check）"
    else
        # alembic check 需要数据库连接，离线时跳过
        if echo "${CHECK_OUTPUT}" | grep -qi "connect\|connection\|could not connect"; then
            skip "alembic check（数据库未连接，跳过在线检查）"
        else
            fail "模型与迁移不一致"
            echo "  ${CHECK_OUTPUT}" | head -5
        fi
    fi
else
    fail "alembic.ini 不存在"
fi

echo ""

# ==========================================
# 7. 端口可用性
# ==========================================
echo "--- 7/8 端口检查 ---"

HTTP_PORT="${HTTP_PORT:-80}"

if command -v ss &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":${HTTP_PORT} "; then
        warn "端口 ${HTTP_PORT} 已被占用（部署时可能冲突）"
    else
        pass "端口 ${HTTP_PORT} 可用"
    fi
elif command -v lsof &>/dev/null; then
    if lsof -i ":${HTTP_PORT}" &>/dev/null 2>&1; then
        warn "端口 ${HTTP_PORT} 已被占用（部署时可能冲突）"
    else
        pass "端口 ${HTTP_PORT} 可用"
    fi
else
    skip "端口检查（ss/lsof 不可用）"
fi

echo ""

# ==========================================
# 8. 磁盘空间
# ==========================================
echo "--- 8/8 磁盘空间 ---"

AVAILABLE_GB=$(df -BG "${PROJECT_DIR}" | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "${AVAILABLE_GB}" -ge 5 ]; then
    pass "磁盘剩余 ${AVAILABLE_GB}GB（建议 >= 5GB）"
else
    warn "磁盘剩余 ${AVAILABLE_GB}GB（建议 >= 5GB，可能影响 Docker 构建）"
fi

echo ""

# ==========================================
# 汇总
# ==========================================
echo "=========================================="
echo "  检查结果汇总"
echo "=========================================="
echo -e "  通过: ${GREEN}${PASS}${NC}  失败: ${RED}${FAIL}${NC}  警告: ${YELLOW}${WARN}${NC}  跳过: ${YELLOW}${SKIP}${NC}"
echo ""

if [ "${FAIL}" -gt 0 ]; then
    echo -e "  ${RED}存在 ${FAIL} 项失败，建议修复后再部署。${NC}"
    echo "=========================================="
    exit 1
else
    echo -e "  ${GREEN}所有检查通过，可以安全部署！${NC}"
    echo ""
    echo "  部署命令："
    echo "    cd ${PROJECT_DIR}"
    echo "    docker compose -f deploy/docker-compose.prod.yml up -d"
    echo "=========================================="
    exit 0
fi
