#!/usr/bin/env bash
# 生产环境健康检查脚本
# 用法: ./scripts/health-check.sh [BASE_URL]
# 退出码: 0=健康 1=异常

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
TIMEOUT=5
PASS=0
FAIL=0

check() {
  local name="$1" url="$2" expect="${3:-200}"
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null) || http_code="000"
  if [ "$http_code" = "$expect" ]; then
    echo "  ✓ $name (HTTP $http_code)"
    ((PASS++))
  else
    echo "  ✗ $name — 期望 $expect, 实际 $http_code ($url)"
    ((FAIL++))
  fi
}

echo "=== 销售管理系统健康检查 ==="
echo "目标: $BASE_URL"
echo ""

echo "后端 API:"
check "健康检查" "$BASE_URL/api/v1/health"

# 检查数据库和版本状态
HEALTH_BODY=$(curl -s --max-time "$TIMEOUT" "$BASE_URL/api/v1/health" 2>/dev/null || echo '{}')
DB_STATUS=$(echo "$HEALTH_BODY" | grep -o '"database":"[^"]*"' | head -1 | cut -d'"' -f4)
VERSION=$(echo "$HEALTH_BODY" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ "$DB_STATUS" = "ok" ]; then
  echo "  ✓ 数据库连接正常"
else
  echo "  ✗ 数据库状态: ${DB_STATUS:-未知}"
  ((FAIL++))
fi
echo "  版本: ${VERSION:-未知}"

echo ""
echo "前端静态资源:"
check "前端首页" "$BASE_URL/" "200"
check "前端 JS 入口" "$BASE_URL/assets/" "200" || true

echo ""
echo "---"
TOTAL=$((PASS + FAIL))
echo "结果: $PASS/$TOTAL 通过"
if [ "$FAIL" -gt 0 ]; then
  echo "状态: 异常"
  exit 1
else
  echo "状态: 健康"
  exit 0
fi
