# 阶段测试报告

**项目**：销售管理系统
**测试日期**：2026-04-30（第六轮更新）
**测试环境**：Python 3.13.11 + SQLite + FastAPI TestClient / Vitest 4.x + jsdom
**测试执行人**：Claude（自动）

## 总览

| 指标 | 后端 | 前端 | 合计 |
|---|---|---|---|
| 总测试数 | 213 | 90 | 303 |
| 通过 | 213 | 90 | 303 |
| 失败 | 0 | 0 | 0 |
| 通过率 | 100% | 100% | 100% |

## 后端按模块统计

| 测试文件 | 通过 | 说明 |
|---|---|---|
| test_health.py | 5/5 | 健康检查、版本信息、安全响应头、请求日志记录 |
| test_auth.py | 8/8 | 登录成功/失败、Token 刷新、权限拒绝、禁用用户刷新被拒 |
| test_integration.py | 24/24 | 完整业务流程端到端测试 |
| test_audit_log.py | 9/9 | 全操作类型审计日志 + 筛选 |
| test_export.py | 18/18 | 四模块 CSV 导出 + 筛选 + 空数据 + 认证 + 审计日志 + BOM/表头/字段数/状态映射验证 |
| test_file_upload.py | 9/9 | 上传成功、类型/大小校验、获取/删除、认证 |
| test_permissions.py | 9/9 | 数据范围、敏感字段、权限码拦截、导出过滤 |
| test_edge_cases.py | 27/27 | 6 个业务模块异常路径覆盖 |
| test_validation.py | 20/20 | refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表 |
| test_boundary.py | 36/36 | 认证边界、订单状态机、收款边界、用户管理、库存调整 |
| test_reports_audit.py | 22/22 | 销售汇总（6 种 period）、趋势、排行、预警、审计日志查询/筛选/权限 |
| test_product_import.py | 8/8 | CSV 成功/带 SKU/重复 SKU/空名称/非 CSV/认证 |
| test_customer_import.py | 8/8 | CSV 成功/带详情/手机号重复/批量内重复/非 CSV/认证 |
| test_ratelimit.py | 3/3 | 响应头验证、429 触发 |
| test_sanitize.py | 6/6 | escape_like 特殊字符转义 |

## 前端按模块统计

| 测试文件 | 通过 | 说明 |
|---|---|---|
| utils.test.ts | 8/8 | formatAmount / formatPercent 纯函数 |
| ErrorBoundary.test.tsx | 2/2 | 正常渲染 + 错误捕获 |
| client.test.ts | 3/3 | baseURL、token 附加、无 token |
| request.test.ts | 5/5 | get/post/put/del/upload 调用验证 |
| statusMaps.test.ts | 6/6 | 商品/客户/订单状态映射完整性 |
| products-api.test.ts | 8/8 | 商品 CRUD + 上传图片 + 价格历史 API |
| customers-api.test.ts | 7/7 | 客户 CRUD + 转移 + 导入 API |
| orders-api.test.ts | 6/6 | 订单 CRUD + 确认/取消 API |
| payments-api.test.ts | 5/5 | 收款查询/登记/冲正 API |
| reports-api.test.ts | 6/6 | 报表四个查询 API |
| auditLogs-api.test.ts | 5/5 | 审计日志查询/筛选/操作类型 API |
| auth-api.test.ts | 4/4 | login/refresh/logout/getMe 路径验证 |
| auth-store.test.ts | 11/11 | login/logout/fetchUser/hasPermission/loading |
| downloadCsv.test.ts | 6/6 | 成功下载、查询参数、过滤、错误、文件名 |
| usePaginatedList.test.ts | 8/8 | 初始加载、错误处理、筛选、分页切换、刷新 |

## 功能覆盖率

| 模块 | API 端点数 | 后端测试 | 前端测试 |
|---|---|---|---|
| 认证 | 4 | 8 | 4+11（api+store） |
| 商品 | 7 | 7+27+20 | 8 |
| 客户 | 6 | 6+27+20 | 7 |
| 订单 | 6 | 6+24+36 | 6 |
| 收款 | 3 | 3+36 | 5 |
| 库存 | 2 | 2+36 | — |
| 报表 | 4 | 22 | 6 |
| 审计日志 | 2 | 22 | 5 |
| 导出 | 4 | 18 | 6（downloadCsv） |
| 用户管理 | 3 | 36 | — |
| 文件上传 | 3 | 9 | — |

## 安全特性验证

| 特性 | 状态 | 说明 |
|---|---|---|
| JWT 认证 | ✅ | Token 验证、过期、无 Token、伪造 Token、已删除用户 Token、禁用用户 Token |
| 权限码校验 | ✅ | report:sales、audit:view 等 403 测试 |
| 数据范围过滤 | ✅ | test_permissions.py 销售员 vs 管理员 |
| 敏感字段过滤 | ✅ | 无 view_cost 权限时隐藏成本价 |
| 库存行锁 | ✅ | with_for_update() 防超卖 |
| 软删除 | ✅ | deleted_at 过滤 |
| 审计日志 | ✅ | 全操作类型记录，含 IP/user_agent/request_id |
| 速率限制 | ✅ | 滑动窗口 IP 级限制，429 + 响应头 |
| 安全响应头 | ✅ | CSP、X-Frame-Options、X-Content-Type-Options、Permissions-Policy |
| SQL 注入防护 | ✅ | escape_like 转义 %、_、\\ |
| 订单状态机 | ✅ | draft→confirmed→completed、draft→cancelled、confirmed→cancelled |
| 收款冲正回退 | ✅ | 冲正后订单状态回退到 confirmed |
| Token 刷新安全 | ✅ | 禁用/已删除用户无法刷新 Token |
| 权限码全量审计 | ✅ | API 权限码与种子数据完全一致，无遗漏 |

## 测试运行命令

```bash
# 后端
cd backend
pytest tests/ -v

# 前端
cd frontend
npx vitest run
```
