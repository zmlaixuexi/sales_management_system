# 阶段测试报告

**项目**：销售管理系统
**测试日期**：2026-05-03（第十八轮更新）
**测试环境**：Python 3.13.11 + SQLite + FastAPI TestClient / Vitest 4.x + jsdom
**测试执行人**：Claude（自动）

## 总览

| 指标 | 后端 | 前端 | 合计 |
|---|---|---|---|
| 总测试数 | 1304 | 648 | 1952 |
| 通过 | 1304 | 648 | 1952 |
| 失败 | 0 | 0 | 0 |
| 通过率 | 100% | 100% | 100% |
| 代码覆盖率 | 100.00% | 94.47% | — |
| 行覆盖率 | 100% | 96.53% | — |

## 门禁状态

| 门禁 | 结果 |
|---|---|
| 后端测试 | 1304/1304 ✓ |
| 前端测试 | 648/648 ✓ |
| ruff | 0 errors ✓ |
| tsc | 0 errors ✓ |
| eslint | 0 errors ✓ |
| vite build | ✓ 248ms |
| 需求符合 | ✓ 第 7-13 节全部实现 |

## 后端按模块统计

| 测试文件 | 通过 | 说明 |
|---|---|---|
| test_health.py | 27/27 | 健康检查、版本信息、安全响应头（含 COOP/CORP/HSTS）、请求日志、CORS、graceful shutdown 503 |
| test_auth.py | 8/8 | 登录成功/失败、Token 刷新、权限拒绝、禁用用户刷新被拒 |
| test_integration.py | 24/24 | 完整业务流程端到端测试 |
| test_audit_log.py | 9/9 | 全操作类型审计日志 + 筛选 |
| test_export.py | 18/18 | 四模块 CSV 导出 + 筛选 + 空数据 + 认证 + 审计日志 |
| test_file_upload.py | 9/9 | 上传成功、类型/大小校验、获取/删除 |
| test_permissions.py | 9/9 | 数据范围、敏感字段、权限码拦截、导出过滤 |
| test_edge_cases.py | 27/27 | 6 个业务模块异常路径覆盖 |
| test_validation.py | 20/20 | refresh_token 异常、价格/库存/名称校验、CSV 边界 |
| test_boundary.py | 36/36 | 认证边界、订单状态机、收款边界、用户管理、库存调整 |
| test_reports_audit.py | 22/22 | 销售汇总（6 种 period）、趋势、排行、预警、审计日志 |
| test_product_import.py | 8/8 | CSV 成功/带 SKU/重复 SKU/空名称/非 CSV |
| test_customer_import.py | 8/8 | CSV 成功/带详情/手机号重复/批量内重复/非 CSV |
| test_ratelimit.py | 10/10 | 响应头验证、429 触发、非 API 路径绕过、多 IP 独立、clear 重置、空/全过期窗口 |
| test_sanitize.py | 6/6 | escape_like 特殊字符转义 |
| test_security_headers.py | 12/12 | COOP/CORP/条件 HSTS/全安全头存在性验证 |
| test_body_limit.py | 12/12 | JSON 请求体大小限制、PUT/DELETE 受限、multipart/uploads 豁免、无 content-length 放行 |
| test_auth_rate_limit.py | 8/8 | 登录速率限制、IP 独立计数、过期清理、混合时间窗口 |
| test_slow_query.py | 3/3 | 慢查询记录、阈值下不记录、带 request_id |
| test_middleware.py | 10/10 | 请求 ID 生成/传递/日志、响应时间头、请求日志 API/非 API |

## 前端按模块统计

| 测试文件 | 通过 | 说明 |
|---|---|---|
| Login.test.tsx | 5/5 | 登录表单、成功导航、失败、redirect 参数 |
| roles-api.test.ts | 7/7 | 角色 CRUD API 调用验证 |
| routes-index.test.tsx | 7/7 | 路由配置：/login、/、/products、404、ProtectedRoute 包裹 |
| ErrorBoundary.test.tsx | 2/2 | 正常渲染 + 错误捕获 |
| client.test.ts | 3/3 | baseURL、token 附加、无 token |
| client-interceptor.test.ts | 16/16 | 401 刷新/重试、429 重试、403/404/500/网络错误、_toastDisplayed、refresh 失败、data.message 兜底 |
| request.test.ts | 5/5 | get/post/put/del/upload 调用验证 |
| statusMaps.test.ts | 6/6 | 商品/客户/订单状态映射完整性 |
| ProtectedRoute.test.tsx | 5/5 | 无 token 重定向、有 token 加载、已认证渲染、fetchUser 失败 |
| AppLayout.test.tsx | 4/4 | 侧边栏菜单、用户信息、退出登录 |
| AuditLogs.test.tsx | 23/23 | 审计日志列表、筛选、分页、资源ID搜索、日期范围、关键词搜索 |
| CustomerDetail.test.tsx | 4/4 | 客户详情、标签页、操作按钮 |
| CustomerForm.test.tsx | 29/29 | 新增/编辑表单、提交创建/更新成功/失败、字段校验 |
| Customers.test.tsx | 19/19 | 客户列表、导航、筛选、删除/CSV 导入 |
| Dashboard.test.tsx | 21/21 | 看板统计、趋势图、排行、库存预警、期间切换、列渲染 |
| Inventory.test.tsx | 21/21 | 库存流水、变动类型/颜色、分页/翻页、重试 |
| OrderDetail.test.tsx | 37/37 | 订单详情、确认/取消/冲正、收款登记成功/失败/弹窗交互、编辑导航、日志分页 |
| OrderForm.test.tsx | 39/39 | 新建/编辑订单、添加商品、提交创建/更新、商品选择器、订单行操作、客户渲染、商品搜索 |
| Orders.test.tsx | 17/17 | 订单列表、导航、状态筛选、搜索、日期格式、分页 |
| Payments.test.tsx | 8/8 | 收款列表、状态筛选、创建/冲正、分页 |
| ProductForm.test.tsx | 35/35 | 新增/编辑商品、图片上传成功/失败、高级设置、提交创建/更新 |
| Products.test.tsx | 18/18 | 商品列表、导航、删除/停用、CSV 导入、图片渲染、导入按钮、分页 |
| ReportsCenter.test.tsx | 6/6 | 报表中心标签页、期间切换 |
| Roles.test.tsx | 20/20 | 角色管理、创建/编辑/删除、权限复选框、保存成功/失败/验证 |
| Users.test.tsx | 18/18 | 用户列表、创建/编辑/保存、搜索、切换活跃状态 |
| utils.test.ts | 8/8 | formatAmount / formatPercent 纯函数 |
| NotFound.test.tsx | 1/1 | 404 页面渲染 |
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
| useSubmit.test.ts | 3/3 | 提交回调、loading 状态、错误处理 |

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
| 速率限制 | ✅ | 滑动窗口 IP 级限制，429 + 响应头 + 多 IP 独立计数 |
| 安全响应头 | ✅ | CSP、X-Frame-Options、X-Content-Type-Options、Permissions-Policy、COOP、CORP、条件 HSTS |
| SQL 注入防护 | ✅ | escape_like 转义 %、_、\\ |
| 订单状态机 | ✅ | draft→confirmed→completed、draft→cancelled、confirmed→cancelled |
| 收款冲正回退 | ✅ | 冲正后订单状态回退到 confirmed |
| Token 刷新安全 | ✅ | 禁用/已删除用户无法刷新 Token，refresh 失败清除 token 并跳转 |
| 权限码全量审计 | ✅ | API 权限码与种子数据完全一致，无遗漏 |
| 请求体大小限制 | ✅ | JSON body 限制 1MB，multipart/uploads 豁免 |
| 登录速率限制 | ✅ | 10 次/15 分钟窗口，IP 独立，过期清理 |
| 慢查询日志 | ✅ | SQL 超过阈值自动记录，含 request_id |
| Graceful shutdown | ✅ | 关闭期间健康检查返回 503，数据库连接池释放 |
| 结构化日志 | ✅ | JSON 格式日志，自动注入 request_id/user_id |

## 测试运行命令

```bash
# 后端
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

# 前端
cd frontend
npx vitest run --coverage

# 代码质量
cd backend && ruff check .
cd frontend && npx tsc --noEmit && npx eslint src
```
