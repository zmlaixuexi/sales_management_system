# Changelog

## 2026-04-30（第六轮）

### 审计日志：记录请求元数据

- **AUDIT-REQ-001** 审计日志补充 IP、user_agent、request_id：
  - audit_service.py 新增 `get_request_meta(request)` 辅助函数
  - 6 个 API 模块共 17 个 log_action 调用全部传入请求元数据
  - request_id 优先从 `x-request-id` 请求头获取，否则自动生成短 UUID
- 后端 51/51 测试通过。

## 2026-04-30（第五轮）

### 安全加固：数据范围权限

- **SEC-002** 实现客户/订单数据范围权限：
  - 客户列表 API：无 `customer:view_all` 权限时只返回本人客户
  - 订单列表 API：无 `order:view_all` 权限时只返回本人订单
  - 客户导出 CSV：同样应用 owner_user_id 过滤
  - 订单导出 CSV：同样应用 sales_user_id 过滤
- 后端 51/51 测试通过。

## 2026-04-30（第四轮）

### 安全加固：统一权限校验

- **SEC-001** 实现统一权限依赖系统：
  - deps.py 新增 `require_permission(code)` 依赖和 `has_permission(user, code)` 辅助函数
  - superuser 自动通过所有权限校验
  - 8 个 API 模块共 25 个端点添加权限码校验
  - 商品列表 API 实现敏感字段过滤：无 `product:view_cost` 权限时不返回成本价/毛利/毛利率
  - 审计日志查询限制为 `audit:view` 权限
- 后端 51/51 测试通过，前端构建通过。

## 2026-04-30（第三轮）

### 测试补强：审计日志和数据导出集成测试

- **QA-002** 创建 test_audit_log.py（9 个测试）：登录成功/失败、商品/客户/订单/收款/库存审计日志、筛选、操作类型列表。
- **QA-002** 创建 test_export.py（8 个测试）：商品/客户/订单/收款 CSV 导出、筛选条件、空数据、认证要求。
- 修复登录失败时审计日志未提交 bug（log_action 后需 commit 再抛异常）。
- 全量测试 51/51 通过（从 34 增至 51）。

## 2026-04-30（第二轮）

### 状态校准

- 修正 `.agent_workspace/README.md`、`tasks/backlog.md` 和 `handoff/active-session.md`：明确现状是“主流程可运行 + 现有测试通过”，不是严格 DoD 全部完成。
- 登记 P0 问题：权限码校验、数据范围、敏感字段控制、阶段 6 交付物和必需文档/测试报告仍未完成。
- 修正根 README 的种子数据命令：`python -m app.seed` 改为 `python -m app.db.seed`。

### MVP 后续扩展：数据导出功能

- **EXT-002** 实现 CSV 数据导出功能：
  - 后端 export_service.py：商品/客户/订单/收款 CSV 流式导出（BOM 头，Excel 兼容）
  - GET /api/v1/exports/products|customers|orders|payments 四个导出端点
  - 前端 downloadCsv 工具函数（fetch + blob 触发浏览器下载）
  - 商品/客户/订单列表页添加"导出"按钮，携带当前筛选条件
- 后端 34/34 测试通过，前端构建通过。

### MVP 后续扩展：操作日志系统

- **EXT-001** 实现操作日志（Audit Log）系统：
  - 后端 AuditLog 模型、迁移（baf204f3ea66）、日志服务（audit_service.py）
  - GET /api/v1/audit-logs 查询接口（支持操作类型/资源类型/日期/关键词筛选）
  - GET /api/v1/audit-logs/actions 获取筛选选项
  - 集成到所有业务 API：认证、商品、客户、订单、收款、库存
  - 前端审计日志页面（AuditLogs.tsx）、侧边栏菜单、路由
  - 日志自动脱敏敏感字段（password/token 等）
- 后端 34/34 测试通过，前端构建通过。

## 2026-04-30

### 阶段 6：交付加固

- **DOC-001** 创建 README.md：项目简介、技术栈、功能模块、快速启动（Docker + 本地开发）、项目结构、测试说明、API 概览、环境变量。
- **首批 MVP Backlog 全部完成（阶段 0-6）。**

### 阶段 5：QA-001 MVP 端到端测试

- **QA-001** 创建 24 个端到端集成测试，覆盖完整业务流程：认证→商品→客户→订单→库存→收款→报表。
- 修复 test_auth.py 与 test_integration.py 的依赖覆盖冲突（改为 setup_module/teardown_module 管理）。
- 全部 34 个测试通过。
- **阶段 5 全部完成。**

### 阶段 5：报表与审计

- **BE-REPORT-001** 实现报表 API：销售汇总（总额/成本/毛利/毛利率/订单数）、按日销售趋势（填充空缺日期）、商品销售排行（按销售额排序 Top N）、库存预警（低于阈值的活跃商品）。
- **FE-REPORT-001** 重写首页看板：四个汇总卡片、销售趋势条形图（纯 CSS）、库存预警表格、商品排行表格、时间段切换。
- 创建 reports.ts 前端 API 调用层。
- 前端构建通过，后端测试 10/10 通过。

### 阶段 4：订单、库存、收款（前端页面）

- **FE-ORDER-001** 实现订单列表页：搜索订单号、状态筛选、分页、金额/毛利/毛利率展示。
- **FE-ORDER-001** 实现订单创建/编辑页：选择客户、添加商品明细（内嵌商品选择器）、编辑数量和单价、实时小计。
- **FE-ORDER-001** 实现订单详情页：明细展示、订单确认（扣减库存）、取消订单（回滚库存）、收款登记/冲正弹窗。
- 创建 orders.ts 和 payments.ts API 调用层。
- 更新路由配置：/orders、/orders/new、/orders/:id、/orders/:id/edit。
- 修复侧边栏菜单 key（/sales-orders → /orders）和子路径高亮。
- 前端构建通过，后端测试 10/10 通过。
- **阶段 4 全部完成。**

### 阶段 3：商品与客户（前端页面）

- **FE-PRODUCT-001** 实现商品列表页：Ant Design Table + 搜索/状态筛选/分页 + 图片缩略图 + 利润/毛利率展示 + 停用/删除。
- **FE-PRODUCT-001** 实现商品新增/编辑页：4 必填字段 + 折叠高级设置 + 图片上传交互。
- **FE-CUSTOMER-001** 实现客户列表页：搜索/来源筛选/分页 + 等级/跟进状态标签 + 删除。
- **FE-CUSTOMER-001** 实现客户新增/编辑页：完整字段表单。
- **FE-FILE-001** 实现商品图片上传、预览交互（集成在商品表单页中）。
- 创建 products.ts 和 customers.ts API 调用层。
- 更新路由：添加商品和客户的新增/编辑路由。
- 前端构建通过，后端测试 10/10 通过。
- **阶段 3 全部完成。**

### 阶段 3：商品与客户（后端 API）

- **DB-PRODUCT-001 / DB-FILE-001** 创建商品、分类、文件、商品图片、价格历史表模型和迁移。
- **DB-CUSTOMER-001** 创建客户表模型和迁移。
- **BE-FILE-001** 实现图片上传 API：校验类型/大小、本地存储、静态文件访问。
- **BE-PRODUCT-001** 实现商品 CRUD API：列表（搜索/筛选/排序/分页）、创建（SKU 自动生成、利润计算）、详情、编辑（价格变更记录）、删除（软删除）、停用、价格历史。
- **BE-CUSTOMER-001** 实现客户 CRUD API：列表、创建（手机号重复检测）、详情、编辑、删除、归属转移。
- 修复 Alembic env.py 未导入模型导致空迁移。
- 修复配置 UPLOAD_DIR 默认值（从 /app/uploads 改为相对于 backend 的路径）。
- 前端：添加 Ant Design、路由布局、API 请求层、工具函数。
- 前端：配置 Vite 路径别名和 API 代理（含 Docker）。
- 修复 Docker 前端 API 代理 502。
- 数据库种子数据初始化：admin 用户、6 角色、32 权限、默认分类。
- 后端测试 10/10 通过，API 实测通过。

### 阶段 2：认证、用户、权限

- **BE-AUTH-001** 实现后端认证系统（登录、Token 刷新、退出、当前用户）。
- **FE-AUTH-001** 实现前端认证系统（登录页、受保护路由、主布局）。
- 后端测试 10/10 通过。

### 阶段 1：工程基础设施

- **BE-001 / DB-001 / FE-001 / DEVOPS-001** 全部完成。

## 2026-04-29

- 创建销售管理系统开发执行文档。
- 补充实现记录、中断恢复协议、问题台账和重复问题台账。
- 创建 `.agent_workspace/` 协作入口模板。
