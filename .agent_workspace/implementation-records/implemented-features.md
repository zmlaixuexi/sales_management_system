# 已实现功能记录

本文件记录已经实现并验证过的功能。

## 状态口径说明

本文件记录的是已经落地的功能切片，不等同于开发文档 Definition of Done 全部满足。凡是各功能的“已知限制”中涉及权限、数据范围、敏感字段、交付文档或测试报告的内容，都必须继续视为未完成事项。

## 功能编号：FEAT-20260430-11

功能名称：库存预警阈值可配置
所属模块：报表
关联任务编号：EXT-003
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- config.py 新增 `INVENTORY_WARNING_THRESHOLD` 配置项（默认 10，支持环境变量覆盖）
- reports.py 库存预警 API：threshold 参数默认值改为从配置读取，前端不传时使用服务端默认
- 前端 Dashboard：不再硬编码阈值，从 API 返回值动态显示"库存预警（≤N）"
- 前端 reports.ts：仅在明确传参时才附带 threshold 查询参数

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/core/config.py | 新增 INVENTORY_WARNING_THRESHOLD 配置项 |
| backend/app/api/v1/reports.py | threshold 默认值改为从 settings 读取 |
| frontend/src/api/reports.ts | 优化参数传递逻辑 |
| frontend/src/pages/Dashboard.tsx | 动态显示阈值 |

### 测试状态

- 后端 87/87 测试通过，前端 TypeScript 编译通过

---

## 功能编号：FEAT-20260430-10

功能名称：审计日志请求元数据
所属模块：审计日志
关联任务编号：AUDIT-REQ-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- audit_service.py 新增 `get_request_meta(request)` 函数，提取 IP、user_agent、request_id
- 6 个 API 模块共 17 个 log_action 调用全部传入请求元数据
- request_id 优先从 `x-request-id` 请求头获取，否则自动生成 8 位短 UUID

### 测试状态

- 后端 51/51 测试通过

### 已知限制

- 审计日志查询页面前端尚未展示 IP、user_agent、request_id 字段

## 功能编号：FEAT-20260430-09
所属模块：安全
关联任务编号：SEC-002 / RBAC-003
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 客户列表 API：无 `customer:view_all` 权限时，自动过滤为 `owner_user_id == current_user.id`
- 订单列表 API：无 `order:view_all` 权限时，自动过滤为 `sales_user_id == current_user.id`
- 客户导出 CSV：同样应用 `owner_user_id` 过滤
- 订单导出 CSV：同样应用 `sales_user_id` 过滤
- 使用 `has_permission()` 辅助函数做非抛异常检查，superuser 自动通过

### 测试状态

- 后端 51/51 测试通过

### 已知限制

- 数据范围仅支持"本人"和"全部"两级，暂无"团队"级别
- 报表 API 尚未应用数据范围过滤

## 功能编号：FEAT-20260430-08

功能名称：统一权限校验系统
所属模块：安全
关联任务编号：SEC-001 / RBAC-002 / RBAC-004
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- deps.py 新增 `require_permission(code)` FastAPI 依赖和 `has_permission(user, code)` 辅助函数
- superuser 自动通过所有权限校验
- 8 个 API 模块共 25 个端点添加权限码校验
- 商品列表 API 实现敏感字段过滤：无 `product:view_cost` 权限时不返回成本价/毛利/毛利率
- 审计日志查询限制为 `audit:view` 权限

### 测试状态

- 后端 51/51 测试通过

### 已知限制

- 审计日志尚未记录 IP、user_agent、request_id

## 功能编号：FEAT-20260430-07

功能名称：数据导出功能
所属模块：数据导出
关联任务编号：EXT-002
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- export_service.py：商品/客户/订单/收款 CSV 流式导出
  - 使用 Python csv 模块 + StringIO 逐行生成，支持 yield_per(500) 流式输出
  - UTF-8 BOM 头确保 Excel 正确识别编码
  - 中文字段头：SKU、商品名称、客户名称、订单号等
  - 状态字段中文映射（active→上架、confirmed→已确认等）
- 4 个导出 API 端点：
  - GET /api/v1/exports/products：支持 keyword/status/category_id 筛选
  - GET /api/v1/exports/customers：支持 keyword/source 筛选
  - GET /api/v1/exports/orders：支持 keyword/status/customer_id/start_date/end_date 筛选
  - GET /api/v1/exports/payments：支持 order_id/start_date/end_date 筛选
- 前端 downloadCsv 工具函数：fetch + Blob 触发浏览器下载，携带 Token 认证
- 商品/客户/订单列表页添加"导出"按钮，携带当前筛选条件

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/services/export_service.py | 新建：CSV 流式导出服务 |
| backend/app/api/v1/exports.py | 新建：4 个导出 API 端点 |
| backend/app/api/v1/router.py | 更新：注册 exports 路由 |
| frontend/src/utils/index.ts | 更新：添加 downloadCsv 工具函数 |
| frontend/src/pages/Products.tsx | 更新：添加导出按钮 |
| frontend/src/pages/Customers.tsx | 更新：添加导出按钮 |
| frontend/src/pages/Orders.tsx | 更新：添加导出按钮 |

### API 变更

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | /api/v1/exports/products | 导出商品 CSV | 登录 |
| GET | /api/v1/exports/customers | 导出客户 CSV | 登录 |
| GET | /api/v1/exports/orders | 导出订单 CSV | 登录 |
| GET | /api/v1/exports/payments | 导出收款 CSV | 登录 |

### 已执行测试

测试命令：`pytest tests/ -v` + `npm run build`
测试结果：后端 34/34 通过，前端构建通过

### 已知限制

- 导出功能暂无角色权限限制（任何登录用户可导出）。
- 暂不支持 Excel (.xlsx) 格式。
- 大量数据导出时暂无进度提示。

---

## 功能编号：FEAT-20260430-06

功能名称：操作日志（Audit Log）系统
所属模块：审计日志
关联任务编号：EXT-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- AuditLog 数据模型：actor_id、actor_name、action、resource_type、resource_id、before_data、after_data、ip_address、user_agent、request_id、created_at
- Alembic 迁移：audit_logs 表（含复合索引 action+resource_type）
- audit_service.py：log_action 通用日志记录函数、model_to_dict 辅助函数、敏感字段自动脱敏
- GET /api/v1/audit-logs：分页查询，支持 action、resource_type、actor_id、start_date、end_date、keyword 筛选
- GET /api/v1/audit-logs/actions：获取所有操作类型和资源类型列表
- 集成到全部业务 API：
  - auth.py：login_success、login_failed
  - products.py：product_create、product_update、product_delete、product_disable
  - customers.py：customer_create、customer_update、customer_delete、customer_transfer
  - orders.py：order_create、order_update、order_confirm、order_cancel
  - payments.py：payment_create、payment_reverse
  - inventory.py：inventory_adjust
- 前端审计日志页面：操作类型/资源类型/日期范围/关键词筛选，分页表格
- 侧边栏菜单：添加"操作日志"入口

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/models/audit.py | 新建：AuditLog 模型 |
| backend/app/models/__init__.py | 更新：导入 AuditLog |
| backend/alembic/versions/baf204f3ea66_*.py | 新建：audit_logs 表迁移 |
| backend/app/services/audit_service.py | 新建：日志记录服务 |
| backend/app/api/v1/audit_logs.py | 新建：日志查询 API |
| backend/app/api/v1/router.py | 更新：注册 audit_logs 路由 |
| backend/app/api/v1/auth.py | 更新：集成登录日志 |
| backend/app/api/v1/products.py | 更新：集成商品操作日志 |
| backend/app/api/v1/customers.py | 更新：集成客户操作日志 |
| backend/app/api/v1/orders.py | 更新：集成订单操作日志 |
| backend/app/api/v1/payments.py | 更新：集成收款操作日志 |
| backend/app/api/v1/inventory.py | 更新：集成库存调整日志 |
| frontend/src/api/auditLogs.ts | 新建：日志 API 调用 |
| frontend/src/pages/AuditLogs.tsx | 新建：审计日志页面 |
| frontend/src/routes/index.tsx | 更新：添加路由 |
| frontend/src/components/MainLayout.tsx | 更新：添加菜单项 |

### API 变更

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | /api/v1/audit-logs | 操作日志查询 | 登录 |
| GET | /api/v1/audit-logs/actions | 操作类型列表 | 登录 |

### 已执行测试

测试命令：`pytest tests/ -v` + `npm run build`
测试结果：后端 34/34 通过，前端构建通过

### 已知限制

- 审计日志查询暂未做角色权限限制（任何登录用户可查）。
- 日志不记录请求 IP 和 user_agent（需从 Request 对象提取，待后续集成 FastAPI Request）。
- 暂无日志保留策略（需定期清理历史日志）。

---

## 功能编号：FEAT-20260430-05

功能名称：报表 API 和首页看板
所属模块：报表
关联任务编号：BE-REPORT-001 / FE-REPORT-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 后端报表 API：
  - GET /reports/sales-summary：销售汇总（总额/成本/毛利/毛利率/订单数），支持时间段筛选。
  - GET /reports/sales-trend：按日销售趋势，自动填充空缺日期。
  - GET /reports/product-ranking：商品销售排行（按销售额降序），支持 Top N。
  - GET /reports/inventory-warning：库存预警（低于阈值的活跃商品）。
  - 时间段：today/7d/30d/this_month/last_month。
- 首页看板：四个汇总卡片、销售趋势条形图、库存预警表格、商品排行表格。
- 前端 API 调用层：reports.ts。

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/api/v1/reports.py | 新建：报表 API |
| backend/app/api/v1/router.py | 更新：注册报表路由 |
| frontend/src/api/reports.ts | 新建：报表 API 调用 |
| frontend/src/pages/Dashboard.tsx | 重写：首页看板 |

### 已执行测试

测试命令：`pytest tests/ -v` + `npx tsc --noEmit` + `npm run build`
测试结果：后端 10/10 通过，TypeScript 编译通过，前端构建通过

---

## 功能编号：FEAT-20260430-04

功能名称：订单管理前端页面
所属模块：订单管理
关联任务编号：FE-ORDER-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 订单列表页（Orders.tsx）：订单号搜索、状态筛选、分页、金额/毛利/毛利率/收款展示。
- 订单创建/编辑页（OrderForm.tsx）：选择客户（搜索下拉）、添加商品明细（内嵌商品选择器）、编辑数量和成交单价、实时小计和合计。
- 订单详情页（OrderDetail.tsx）：明细展示、确认订单（扣减库存）、取消订单（回滚库存）、收款登记弹窗（金额/方式/备注）、收款冲正。
- API 调用层：orders.ts（CRUD + 确认/取消）、payments.ts（收款登记/冲正/列表）。
- 路由配置：/orders、/orders/new、/orders/:id、/orders/:id/edit。
- 侧边栏菜单修复：key 从 /sales-orders 改为 /orders，支持子路径高亮。

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| frontend/src/api/orders.ts | 新建：订单 API 调用 |
| frontend/src/api/payments.ts | 新建：收款 API 调用 |
| frontend/src/pages/Orders.tsx | 重写：订单列表页 |
| frontend/src/pages/OrderForm.tsx | 新建：订单创建/编辑页 |
| frontend/src/pages/OrderDetail.tsx | 新建：订单详情页 |
| frontend/src/routes/index.tsx | 更新：添加订单路由 |
| frontend/src/components/MainLayout.tsx | 更新：修复侧边栏菜单 |

### 已执行测试

测试命令：`npx tsc --noEmit` + `npm run build` + `pytest tests/ -v`
测试结果：TypeScript 编译通过，前端构建通过，后端测试 10/10 通过

---

## 功能编号：FEAT-20260430-03

功能名称：订单、库存、收款后端 API
所属模块：订单管理
关联任务编号：DB-ORDER-001 / BE-ORDER-001 / BE-PAYMENT-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 订单模型：SalesOrder、SalesOrderItem、InventoryMovement、Payment。
- 订单 CRUD API：创建草稿（含商品快照）、编辑草稿、确认（扣减库存）、取消（回滚库存）。
- 订单状态机：draft → confirmed → partially_paid → completed；draft/confirmed → cancelled。
- 收款 API：登记收款（自动更新订单状态）、冲正收款。
- 库存 API：库存流水查询、手工库存调整。
- 库存扣减/回滚使用行锁（with_for_update）保护并发安全。

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/models/order.py | 新建：订单相关模型 |
| backend/app/api/v1/orders.py | 新建：订单 CRUD + 状态操作 API |
| backend/app/api/v1/payments.py | 新建：收款登记和冲正 API |
| backend/app/api/v1/inventory.py | 新建：库存流水和调整 API |
| backend/app/api/v1/router.py | 更新：注册新路由 |
| backend/alembic/versions/eb6a1ce2c197_*.py | 新建：订单相关表迁移 |

### 已执行测试

测试命令：`pytest tests/ -v`
测试结果：10/10 通过
API 实测：创建 → 确认 → 收款 → 完成流程通过

---

## 功能编号：FEAT-20260430-02

功能名称：商品管理、文件上传和客户管理后端 API
所属模块：商品管理、文件管理、客户管理
关联任务编号：DB-PRODUCT-001 / DB-FILE-001 / BE-PRODUCT-001 / BE-FILE-001 / DB-CUSTOMER-001 / BE-CUSTOMER-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 商品模型：Product、ProductCategory、File、ProductImage、ProductPriceHistory。
- 客户模型：Customer。
- 商品 CRUD API：列表（搜索/筛选/排序/分页）、创建（SKU 自动生成、默认分类、利润计算）、详情、编辑（价格变更记录）、软删除、停用、价格历史。
- 文件上传 API：图片上传（类型/大小校验）、文件信息查询、删除。
- 客户 CRUD API：列表（搜索/筛选/分页）、创建（手机号重复检测）、详情、编辑、软删除、归属转移。
- 静态文件服务（/uploads）。
- 数据库迁移和种子数据。

### 不包含范围

- 前端页面（FE-PRODUCT-001、FE-FILE-001、FE-CUSTOMER-001 待实现）。
- 操作日志记录。
- 细粒度权限校验（目前仅验证登录）。
- 数据范围权限（销售只能看本人客户）。

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/models/product.py | 新建：商品相关模型 |
| backend/app/models/customer.py | 新建：客户模型 |
| backend/app/api/v1/products.py | 新建：商品 CRUD API |
| backend/app/api/v1/files.py | 新建：文件上传 API |
| backend/app/api/v1/customers.py | 新建：客户 CRUD API |
| backend/app/services/file_service.py | 新建：文件上传服务 |
| backend/app/main.py | 更新：静态文件挂载 |
| backend/app/core/config.py | 更新：UPLOAD_DIR 默认值 |
| backend/alembic/env.py | 修复：导入模型 |
| backend/alembic/versions/6800eb76fb83_*.py | 新建：全部初始表迁移 |
| backend/alembic/versions/67fdb7b8db27_*.py | 新建：客户表迁移 |

### 数据库变更

迁移文件：
- 6800eb76fb83：全部初始表（users, roles, permissions, user_roles, role_permissions, product_categories, products, files, product_images, product_price_history）
- 67fdb7b8db27：客户表（customers）

### API 变更

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | /api/v1/products | 商品列表 | 登录 |
| POST | /api/v1/products | 新增商品 | 登录 |
| GET | /api/v1/products/{id} | 商品详情 | 登录 |
| PUT | /api/v1/products/{id} | 编辑商品 | 登录 |
| DELETE | /api/v1/products/{id} | 删除商品 | 登录 |
| POST | /api/v1/products/{id}/disable | 停用商品 | 登录 |
| GET | /api/v1/products/{id}/price-history | 价格历史 | 登录 |
| POST | /api/v1/files/images | 上传图片 | 登录 |
| GET | /api/v1/files/images/{id} | 获取图片信息 | 登录 |
| DELETE | /api/v1/files/images/{id} | 删除图片 | 登录 |
| GET | /api/v1/customers | 客户列表 | 登录 |
| POST | /api/v1/customers | 新增客户 | 登录 |
| GET | /api/v1/customers/{id} | 客户详情 | 登录 |
| PUT | /api/v1/customers/{id} | 编辑客户 | 登录 |
| DELETE | /api/v1/customers/{id} | 删除客户 | 登录 |
| POST | /api/v1/customers/{id}/transfer | 转移归属 | 登录 |

### 自动处理逻辑

- SKU 自动生成：SPU-YYYYMMDD-四位序号
- 默认分类：自动归入"未分类"
- 利润/毛利率自动计算：unit_profit = sale_price - cost_price，gross_margin = unit_profit / sale_price
- 价格变更自动记录

### 已执行测试

测试命令：`pytest tests/ -v`
测试结果：10/10 通过
API 实测：商品创建/列表/详情通过

### 已知限制

- 权限校验仅验证登录状态，未做角色/数据范围校验。
- 文件上传未做文件头校验（仅校验扩展名和 MIME）。
- 无缩略图生成。
- 客户数据范围权限未实现。

### 后续任务

- FE-PRODUCT-001：商品列表页和编辑页
- FE-FILE-001：图片上传交互
- FE-CUSTOMER-001：客户列表页和详情页
- 操作日志
- 权限和数据范围校验细化

---

## 功能编号：FEAT-20260429-001

功能名称：FastAPI 后端工程骨架
所属模块：后端基础设施
关联任务编号：BE-001、DB-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- FastAPI 应用入口，含 CORS 中间件、API 路由。
- 健康检查接口 GET /api/v1/health。
- 版本信息接口 GET /api/v1/version。
- 配置管理（pydantic-settings），支持环境变量。
- JWT 和密码工具（python-jose + bcrypt）。
- 数据库会话管理（SQLAlchemy 2.x sync session）。
- Alembic 迁移环境配置。
- 后端 Dockerfile。
- 测试基础设施（pytest + httpx）。

### 已执行测试

测试命令：pytest tests/test_health.py -v
测试结果：2/2 通过

---

## 功能编号：FEAT-20260429-002

功能名称：React + TypeScript + Vite 前端工程
所属模块：前端基础设施
关联任务编号：FE-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- Vite + React + TypeScript 脚手架。
- Ant Design、react-router-dom、axios 依赖。
- 基础布局（侧边栏导航）。
- API 请求层和类型定义。
- Vite 路径别名和 API 代理配置。

### 已执行测试

测试命令：cd frontend && npm run build
测试结果：构建成功

---

## 功能编号：FEAT-20260429-003

功能名称：Docker Compose 开发环境
所属模块：DevOps
关联任务编号：DEVOPS-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- Docker Compose 开发环境（postgres 17、backend、frontend）。
- 环境变量示例文件。
- 编辑器配置。

### 已执行测试

测试命令：docker compose up -d
测试结果：三服务全部运行，API 代理正常
