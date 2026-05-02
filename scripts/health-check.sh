#!/usr/bin/env bash
# 生产环境健康检查脚本
# 用法: ./scripts/health-check.sh [BASE_URL] [--quiet]
# 退出码: 0=健康 1=异常

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
QUIET=false
[[ "${2:-}" == "--quiet" ]] && QUIET=true
TIMEOUT=5
PASS=0
FAIL=0

check() {
  local name="$1" url="$2" expect="${3:-200}"
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null) || http_code="000"
  if [ "$http_code" = "$expect" ]; then
    $QUIET || echo "  ✓ $name (HTTP $http_code)"
    ((PASS++))
  else
    $QUIET || echo "  ✗ $name — 期望 $expect, 实际 $http_code ($url)"
    ((FAIL++))
  fi
}

$QUIET || echo "=== 销售管理系统健康检查 ==="
$QUIET || echo "目标: $BASE_URL"

$QUIET || echo ""
$QUIET || echo "后端 API:"
check "健康检查" "$BASE_URL/api/v1/health"

# 检查数据库、版本、连接池状态
HEALTH_BODY=$(curl -s --max-time "$TIMEOUT" "$BASE_URL/api/v1/health" 2>/dev/null || echo '{}')
DB_STATUS=$(echo "$HEALTH_BODY" | grep -o '"database":"[^"]*"' | head -1 | cut -d'"' -f4)
VERSION=$(echo "$HEALTH_BODY" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
POOL_SIZE=$(echo "$HEALTH_BODY" | grep -o '"size":[0-9]*' | head -1 | cut -d':' -f2)
POOL_CHECKED_IN=$(echo "$HEALTH_BODY" | grep -o '"checked_in":[0-9]*' | head -1 | cut -d':' -f2)
POOL_OVERFLOW=$(echo "$HEALTH_BODY" | grep -o '"overflow":[0-9]*' | head -1 | cut -d':' -f2)

if [ "$DB_STATUS" = "ok" ]; then
  $QUIET || echo "  ✓ 数据库连接正常"
else
  $QUIET || echo "  ✗ 数据库状态: ${DB_STATUS:-未知}"
  ((FAIL++))
fi
$QUIET || echo "  版本: ${VERSION:-未知}"
if [ -n "${POOL_SIZE:-}" ]; then
  $QUIET || echo "  连接池: ${POOL_CHECKED_IN:-?}/${POOL_SIZE} 在线, 溢出 ${POOL_OVERFLOW:-0}"
fi

$QUIET || echo ""
$QUIET || echo "前端静态资源:"
check "前端首页" "$BASE_URL/" "200"
check "前端 JS 入口" "$BASE_URL/assets/" "200" || true

$QUIET || echo ""
$QUIET || echo "---"
TOTAL=$((PASS + FAIL))
$QUIET || echo "结果: $PASS/$TOTAL 通过"
if [ "$FAIL" -gt 0 ]; then
  $QUIET || echo "状态: 异常"
  exit 1
else
  $QUIET || echo "状态: 健康"
  exit 0
fi
