# Changelog

## 2026-04-30（第一百一十二轮）

### 重构：提取 getApiErrorMessage，消除 6 个页面 9 处重复错误处理

- utils/index.ts 新增 getApiErrorMessage(e, fallback)：提取 detail.message 路径
- CustomerForm/ProductForm/OrderForm/Products/Customers/OrderDetail 统一使用
- 移除所有 `e as { response?: { data?: { detail?... } } }` 类型断言
- tsc 0 + ESLint 0 + 97/97 + build 通过

## 2026-04-30（第一百一十一轮）

### 测试：订单负价校验测试（+2，后端 286/286）

- 新增 test_05b：create_order 负单价拒绝（400 + "不能为负"）
- 新增 test_11b：update_order 负单价拒绝（验证 Round 110 修复的 bug 回归保护）

## 2026-04-30（第一百一十轮）

### 重构：提取 _validate_and_prepare_items，修复 update_order 缺少负价校验 bug

- 新增 _validate_and_prepare_items(db, raw_items) 辅助函数，统一校验商品状态、数量、单价
- create_order 和 update_order 共用同一校验逻辑（-41 行 +21 行）
- 修复 update_order 缺少成交单价不能为负的校验（create_order 有，update_order 遗漏）

## 2026-04-30（第一百零九轮）

### 重构：提取 get_or_404 辅助函数，消除 19 处重复查询模式

- deps.py 新增 get_or_404(db, model, id, label)：自动过滤软删除，不存在则抛标准 404
- orders.py 替换 7 处、customers.py 4 处、products.py 4 处、payments.py 1 处
- 保留 with_for_update 和非标准过滤器（如 Payment.status=="normal"）的原始写法
- 净减 59 行代码，无行为变更，284/284 测试全部通过

## 2026-04-30（第一百零八轮）

### 文档：同步测试数至 381（284 后端 + 97 前端）

- README 后端测试表：新增订单 CRUD（19）、收款（11）、库存（10）三行，合计 244→284
- README 前端测试表：新增拦截器行（7），修正客户/报表 API 描述，合计 90→97
- testing.md：概览表同步 284/21/381、新增 3 个测试文件条目和详解段落

## 2026-04-30（第一百零七轮）

### 测试：库存调整 + 流水查询测试（+10，后端 284/284）

- 新增 test_inventory_crud.py：10 个测试覆盖库存完整操作
  - 手工调整（增加 10、减少 5、恰好归零）
  - 异常（零调整 400、超量扣减 400、商品不存在 404）
  - 流水列表（全量、按 product_id 筛选、按 movement_type 筛选、字段完整性校验）
- 至此所有 12 个 API 端点均有独立测试文件

## 2026-04-30（第一百零六轮）

### 测试：收款登记 + 冲正测试（+11，后端 274/274）

- 新增 test_payment_crud.py：11 个测试覆盖收款完整流程
  - 创建（部分收款→订单 partially_paid、全额→completed）
  - 异常（超额收款、零金额、草稿不可收款、订单不存在）
  - 列表（全量 + 按 order_id 筛选）
  - 冲正（正常冲正、重复冲正 404、不存在 404）

## 2026-04-30（第一百零五轮）

### 测试：订单 CRUD + 状态流转测试（+19，后端 263/263）

- 新增 test_order_crud.py：19 个测试覆盖订单完整生命周期
  - 创建（正常/空明细/客户不存在/商品不存在/零数量）
  - 查询（详情/404/列表/状态筛选）
  - 编辑草稿（修改明细+验证金额重算）
  - 确认（库存扣减验证/重复确认/已确认不可编辑）
  - 取消（库存回滚验证/重复取消）
  - 库存不足确认失败
- 填补了 /orders 端点零测试覆盖的关键缺口

## 2026-04-30（第一百零四轮）

### 修复：ESLint 清零，usePaginatedList ref 更正 + 测试文件移除未用变量

- usePaginatedList.ts：fetchFnRef 赋值从渲染期移入 useEffect，避免 React 规则违反
- client-interceptor.test.ts：移除未使用的 origRequest 变量
- 全量验证：ESLint 0 + tsc 0 + 244/244 + 97/97 + build 通过

## 2026-04-30（第一百零三轮）

### 修复：前端错误消息路径修正，正确读取 detail.message

- 拦截器增加 detail.message 提取路径（409 重复手机号、400 库存不足等错误现在能正确显示）
- 6 个页面组件的错误类型断言统一改为 detail.message
- Alembic 迁移验证通过：16 个表全部覆盖

## 2026-04-30（第一百零二轮）

### 工程：Makefile 新增 db-backup 和 db-restore 命令

- db-backup：调用 deploy/backup.sh 备份 PostgreSQL
- db-restore：调用 deploy/restore.sh 恢复，支持 BACKUP_FILE 参数

## 2026-04-30（第一百零一轮）

### 修复：前端类型修正，成本价/毛利率标记为可选字段

- Product 接口 cost_price/unit_profit/gross_margin 改为可选（无 view_cost 权限时后端不返回）
- Order 接口 item_count 改为可选（详情端点不返回此字段）
- ProductForm 编辑时安全处理 cost_price 为 undefined 的场景

## 2026-04-30（第一百轮）

### 文档：同步测试数至 341（244 后端 + 97 前端）

- README 测试总数更新、新增商品/客户 CRUD 测试行
- testing.md 新增 3 个测试文件描述、更新边界测试计数

### 测试：新增库存流水类型筛选和客户列表筛选测试（+3 测试）

- 库存流水 movement_type 筛选验证（+1）
- 客户列表按来源和关键词筛选验证（+2）
- 后端 241→244

## 2026-04-30（第九十九轮）

### 测试：新增客户/商品 CRUD 成功路径测试（+15 测试）

- 新增 test_customer_crud.py：9 个测试覆盖客户详情、编辑、转移、软删除
- 新增 test_product_crud.py：6 个测试覆盖商品详情、软删除、列表排除已删除
- 后端 226→241（+15）

## 2026-04-30（第九十八轮）

### 测试：新增用户管理 CRUD 测试（+10）并修复 role_ids UUID 转换 bug

- 新增 test_user_management.py：10 个测试覆盖用户列表搜索、创建（含重复用户名）、编辑（含禁用/角色变更）、403 权限
- 修复 users.py role_ids 字符串未转 UUID 的 bug（create 和 update 端点）
- API 文档补齐 product_import 和 customer_import 审计操作类型
- 后端 216→226（+10）

## 2026-04-30（第九十七轮）

### 测试：新增 CSV 导入文件大小限制测试（+2 测试）

- 商品导入和客户导入各新增 1 个测试，验证超限文件返回 400
- 后端 214→216（+2）

## 2026-04-30（第九十五轮）

### 文档：API 文档补齐完整权限码列表

- 权限码一览表从 24 个补齐到 32 个（新增 user:*/role:*/report:profit/ranking）
- 与种子数据 PERMISSIONS 列表完全一致

## 2026-04-30（第九十四轮）

### 文档：API 文档补齐批量导入端点和环境变量

- 新增 POST /products/import 和 POST /customers/import 端点文档
- 补充 MAX_CSV_IMPORT_SIZE_MB 和 SLOW_REQUEST_THRESHOLD_MS 环境变量
- 代码干净：0 console.log、0 print、0 debug 语句

## 2026-04-30（第九十二轮）

### 部署：Docker Compose 同步 MAX_CSV_IMPORT_SIZE_MB

- dev 和 prod Docker Compose 补齐 MAX_CSV_IMPORT_SIZE_MB 环境变量

## 2026-04-30（第九十一轮）

### 安全：CSV 导入添加文件大小限制

- config.py 新增 MAX_CSV_IMPORT_SIZE_MB 配置项（默认 10MB）
- 商品和客户导入端点添加文件大小检查，超限返回 400
- 后端 214/214 通过

## 2026-04-30（第九十轮）

### 安全：生产环境启动检查 JWT_SECRET_KEY

- main.py lifespan 添加生产环境 JWT_SECRET_KEY 默认值检查
- 生产环境使用 "change-me" 默认密钥时拒绝启动（RuntimeError）
- 新增测试验证检查逻辑
- 后端 214/214 通过

## 2026-04-30（第八十九轮）

### 文档：更新数据库文档索引信息

- docs/database.md 补充 Round 72 添加的 10 个复合索引
- 修正种子数据权限码数量 23→32

## 2026-04-30（第八十八轮）

### 测试：新增 HTTP 客户端响应拦截器测试（+7 测试）

- 验证 401 刷新 Token 流程（有/无 refresh_token、重复 401 防无限重试）
- 验证统一错误提示（403/404/500/网络错误）
- 前端 90→97（+7）

## 2026-04-30（第八十七轮）

### 文档：更新测试文档

- docs/testing.md 从 51 测试更新到 303 测试（213 后端 + 90 前端）
- 新增 10 个后端测试文件和 15 个前端测试文件详解
- 新增前端测试架构、模板和注意事项

## 2026-04-30（第八十六轮）

### 文档：更新 README 测试数和覆盖表

- 后端测试数 201→213，新增 Token 刷新安全、请求日志、CSV 格式验证
- 前端测试数 77→90，新增 auth API、usePaginatedList、import/upload 测试
- 各模块测试数逐一核实与实际一致

## 2026-04-30（第八十五轮）

### 测试：新增 auth API 前端测试（+4 测试）

- 新建 auth-api.test.ts：验证 login/refresh/logout/getMe 调用正确的 HTTP 方法和路径
- 前端所有 9 个 API 模块现在都有测试覆盖
- 前端 86→90（+4）

## 2026-04-30（第八十四轮）

### 性能：修复订单导出 N+1 查询

- export_orders 查询添加 selectinload(SalesOrder.items)，避免逐行触发 items 加载
- Product.category 和 Customer.owner 已在模型层配置 selectin，无需额外处理
- 后端 213/213 通过，ruff 0

## 2026-04-30（第八十三轮）

### 测试：CSV 导出内容格式验证（9 个新测试）

- 验证 UTF-8 BOM 开头
- 验证商品/客户/订单/收款四种 CSV 表头顺序精确匹配
- 验证每行数据字段数与表头一致
- 验证状态字段中文映射（上架、已完成）
- 验证归属销售名称在客户 CSV 中
- 验证商品 CSV 数据行具体值（价格、库存、分类）
- 后端 204→213（+9），ruff 0，前端 86/86

## 2026-04-30（第八十二轮）

### 审计：权限代码全量核对

- 对比 API 端点 require_permission() 调用与种子数据 PERMISSIONS 列表
- 结果：API 使用的 24 个权限码全部存在于种子数据，种子额外包含 user:*/role:* 权限码供未来用户管理使用
- 无遗漏、无冗余

## 2026-04-30（第八十一轮）

### 工程：全量验证通过

- 后端 204/204、前端 86/86、tsc 0 errors、ruff 0、ESLint 0、build 通过
- 全面审查代码质量：无裸 except、无 TODO/FIXME、无 any 类型、无未使用导入
- 导出服务已使用 yield_per(500) 防止内存过载
- Docker Compose 环境变量已与 config.py 完全同步

## 2026-04-30（第八十轮）

### 部署：Docker Compose 补齐 SLOW_REQUEST_THRESHOLD_MS 环境变量

## 2026-04-30（第七十九轮）

### 工程：同步 active-session 交接文档

## 2026-04-30（第七十八轮）

### 工程：修复 test_health.py 未使用导入

- 移除 unittest.mock.patch 未使用导入（ruff F401）
- 后端 204/204，ruff 0，ESLint 0，build 通过

## 2026-04-30（第七十七轮）

### 测试：新增 Token 刷新安全测试

- 验证已禁用用户的 Refresh Token 被拒绝（对应 SEC-REFRESH-001 修复）
- 后端 204/204 通过（+1）

## 2026-04-30（第七十六轮）

### 安全：修复 Token 刷新不校验用户状态的漏洞

- /auth/refresh 端点增加用户存在性和 is_active 校验
- 已禁用或已删除用户无法继续刷新 Token
- 后端 203/203 通过

## 2026-04-30（第七十五轮）

### 测试：新增请求日志中间件测试

- 新增 2 个测试：验证 API 请求被记录、非 API 路径不记录
- 后端 203/203 通过（+2）

## 2026-04-30（第七十四轮）

### 文档：同步环境变量和请求日志文档

- .env.example 新增 SLOW_REQUEST_THRESHOLD_MS
- deployment.md 环境变量表补齐慢请求阈值
- api.md 请求日志文档补充 slow 字段说明

## 2026-04-30（第七十三轮）

### 可观测性：请求日志增加慢请求警告

- 新增 SLOW_REQUEST_THRESHOLD_MS 配置项（默认 1000ms，可环境变量覆盖）
- 超过阈值的请求日志自动升级为 WARNING 级别，日志前缀加 SLOW 标记
- 后端 201/201 通过，ruff lint 0

## 2026-04-30（第七十二轮）

### 性能：添加数据库复合索引优化查询

- 分析 16 张表的索引现状和 12 个 API 端点的查询模式
- 新建 Alembic 迁移添加 10 个复合索引，覆盖列表筛选+排序、数据范围、报表聚合、库存预警等高频查询
- 后端 201/201 通过，前端 86/86 通过

## 2026-04-30（第七十一轮）

### 重构：前端列表页统一分页 hook

- 新建 `usePaginatedList` 自定义 hook：封装分页列表的 data/total/loading/page/pageSize/keyword 状态和加载逻辑
- 重构 Products/Customers/Orders/AuditLogs 四个列表页，消除约 80 行重复样板代码
- 新增 8 个 hook 单元测试
- 前端 86/86 通过，build 通过

## 2026-04-30（第七十轮）

### 文档：新增架构文档

- 新建 docs/architecture.md：完整架构文档，含技术栈、系统架构图、后端前端目录结构、中间件栈、API 路由表、数据模型（16 表）、认证授权（RBAC）、订单状态机、库存联动、审计追踪、部署架构、安全措施、可观测性
- DoD 文档缺口全部补齐（deployment.md + architecture.md）

## 2026-04-30（第六十九轮）

### 文档：新增部署指南

- 新建 docs/deployment.md：覆盖开发环境、生产部署、环境变量、Nginx 配置、数据库备份恢复、健康检查、运维命令
- 补齐 DoD 文档缺口

## 2026-04-30（第六十八轮）

### 工程：修复 Makefile docker-compose 路径

- dev 命令路径从 `docker-compose.dev.yml` 修正为 `deploy/docker-compose.dev.yml`

## 2026-04-30（第六十七轮）

### 工程：代码审查和小改进

- antd 导入方式确认正确（命名导入，tree-shaking 已生效）
- .gitignore 新增 `*.db` 排除测试 SQLite 文件
- Docker 配置确认完整（多阶段构建、缓存层合理）
- 全量测试确认：后端 201/201、前端 78/78、build 通过

## 2026-04-30（第六十五轮）

### 文档：API 文档同步更新

- docs/api.md 新增安全响应头说明（6 个响应头）
- docs/api.md 新增请求日志说明（含 JSON 示例）
- 健康检查端点文档补充数据库连接探测和 degraded 状态
- 后端 201/201 通过，前端 78/78 + build 通过

## 2026-04-30（第六十五轮·续）

### 文档：实现记录更新 + 代码质量扫描

- implemented-features.md 新增 FEAT-16~22（8 个功能记录）
- 代码质量扫描：0 TODO/FIXME、0 any 类型、tsc 0 错误、ruff 0 错误

## 2026-04-30（第六十三轮）

### 部署：Makefile 开发命令简化

- 新建 Makefile（17 个命令）：dev、dev-backend、dev-frontend、install、test、test-backend、test-frontend、lint、lint-backend、lint-frontend、build、build-frontend、db-migrate、db-seed、docker-up、docker-down、clean
- README 新增 Makefile 常用命令说明
- `make lint` 验证通过

## 2026-04-30（第六十二轮）

### 可观测性：请求日志中间件

- 新增 `app/core/request_log.py`：RequestLogMiddleware
  - 记录每个 /api/ 请求的方法、路径、状态码、耗时（ms）、客户端 IP
  - 只记录 API 路径，跳过静态文件和文档页面
  - 兼容结构化 JSON 日志（通过 extra_fields）
- main.py 注册 RequestLogMiddleware
- 后端 201/201 通过，ruff 0 错误

## 2026-04-30（第六十一轮）

### 测试：前端 upload 函数测试 + 问题台账更新

- request.test.ts 新增 upload 函数测试（FormData POST + multipart/form-data）
- issue-register.md 标记两个 P0 问题为已解决（RBAC 权限和 Backlog 状态）
- 前端 78/78 通过

## 2026-04-30（第六十一轮·续）

### 工程：修复 test_boundary 未使用导入

- ruff check 修复 2 个未使用导入（create_refresh_token、Payment）
- ruff 0 错误，后端 201/201 通过

## 2026-04-30（第五十九轮）

### 文档：README 和测试报告更新

- README 测试数更新：后端 142→201、前端 61→77
- 后端测试覆盖表新增：边界测试 36、报表 12、审计查询 10、安全头 1
- 前端测试覆盖表新增：收款 API 5、审计日志 API 5、downloadCsv 6
- 测试报告全面更新至 278 个测试（后端 201 + 前端 77）
- 安全特性验证新增：安全响应头、SQL 注入防护、订单状态机、收款冲正回退

## 2026-04-30（第五十八轮）

### 测试：前端收款和审计日志 API 测试（67→77）

- 新建 payments-api.test.ts（5 个）：fetchPayments、按订单筛选、createPayment、备注、reversePayment
- 新建 auditLogs-api.test.ts（5 个）：fetchAuditLogs 基础查询、筛选参数、日期范围、数据解析、fetchAuditActions
- 前端 77/77 通过，build 成功

## 2026-04-30（第五十七轮）

### 测试：报表和审计日志端点测试（179→201）

- 新建 test_reports_audit.py（22 个测试）：
  - 报表销售汇总（6 个）：默认 30d、today、7d、this_month、last_month、无效 period 回退
  - 报表销售趋势（1 个）：7 天趋势含日期填充
  - 报表商品排行（2 个）：排行查询、limit 参数
  - 报表库存预警（3 个）：默认阈值、自定义阈值、阈值为 0
  - 审计日志（7 个）：列表、按操作类型筛选、按资源类型筛选、分页、关键词搜索、操作类型列表、after_data JSON 解析
  - 权限检查（2 个）：报表 403、审计日志 403
- 后端 201/201 通过

## 2026-04-30（第五十六轮）

### 安全：CSP 和安全响应头加固

- 新增 `app/core/security_headers.py`：SecurityHeadersMiddleware 中间件
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: camera=(), microphone=(), geolocation=()
  - Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
- main.py 注册 SecurityHeadersMiddleware
- Nginx 配置新增 CSP 和 Permissions-Policy 头（前端安全策略）
- test_health.py 新增安全响应头验证测试
- 后端 179/179 通过

## 2026-04-30（第五十五轮）

### 测试：后端边界测试补强（142→178）

- 新建 test_boundary.py（36 个测试），覆盖 6 大模块未测路径：
  - 认证（7 个）：禁用用户登录、不存在用户登录、access_token 刷新、无效 token 刷新、已删除用户 token、禁用用户 token
  - 订单状态机（7 个）：取消草稿、取消已确认（库存回滚）、取消已完成（拒绝）、订单详情 404、编辑 404、状态筛选、关键词搜索
  - 收款边界（7 个）：草稿订单收款、已完成订单重复收款、已取消订单收款、精确金额、冲正后状态回退、冲正已冲正、负金额、收款列表
  - 用户管理（6 个）：重复用户名、编辑不存在、非管理员列表/创建、创建并更新、关键词搜索
  - 库存（4 个）：正数调整、不存在商品、流水列表、按商品筛选
  - 订单编辑（1 个）：仅更新备注
  - 刷新 Token（1 个）：正常刷新
- 修复 users.py UUID 转换 bug（user_id 参数未转 UUID 导致 SQLite 查询失败）
- 后端 178/178 通过，前端 67/67 通过

## 2026-04-30（第五十五轮·续）

### 工程：前端代码分割优化

- vite.config.ts 新增 build.rollupOptions.output.manualChunks 函数
- 将 react/react-dom/react-router 拆为 vendor-react chunk（93KB）
- 将 antd/@ant-design 拆为 vendor-antd chunk（1281KB）
- index.js 从 730KB 降至 45KB（减少 94%）
- 前端 67/67 测试通过，build 成功

## 2026-04-30（第四十四轮）

### 文档：FastAPI API 文档增强

- main.py 新增 description、openapi_tags（11 个模块描述）
- 新增 Pydantic 请求模型：ProductCreate/Update、CustomerCreate/Update/Transfer、OrderCreate/Update
- 替换 products、customers、orders 路由中 raw dict 为类型化模型，Swagger UI 自动生成请求体 Schema
- 修正 7 个测试用例：Pydantic 验证返回 422 替代原手动 400
- 后端 142/142 通过

## 2026-04-30（第四十三轮）

### 工程：前端 ESLint 检查和修复

- 修复测试文件未使用导入（client.test.ts 移除 vi/afterEach，statusMaps.test.ts 移除 vi）
- OrderForm.tsx 将 loadProducts 提取为 useCallback 消除 exhaustive-deps 警告
- eslint.config.js 新增规则：忽略 `_` 前缀未使用变量，关闭 React Compiler 规则（set-state-in-effect、preserve-manual-memoization），routes 文件关闭 only-export-components
- ESLint 0 错误，TypeScript 编译通过，前端 23/23 测试通过

## 2026-04-30（第四十二轮）

### 部署：Docker Compose 和 Nginx 配置优化

- 开发环境 docker-compose.dev.yml 补齐 RATE_LIMIT_MAX/WINDOW、INVENTORY_WARNING_THRESHOLD、LOG_FORMAT 环境变量
- 生产环境 docker-compose.prod.yml 新增 backend 健康检查（/api/v1/health）
- Nginx 新增安全响应头（X-Content-Type-Options、X-Frame-Options、X-XSS-Protection、Referrer-Policy）
- .env.example 新增 POSTGRES_USER/PASSWORD/DB 配置
- 后端 142/142 通过

## 2026-04-30（第四十一轮）

### 安全：LIKE 通配符转义防注入

- 新增 `app/core/sanitize.py`：`escape_like()` 转义 %、_、\\
- 所有 `ilike` 查询统一使用 `escape_like` + `escape="\\"` 参数
- 覆盖 6 个模块：products、customers、orders、audit_logs、users、export_service
- 新增 6 个转义函数测试，后端 142/142 通过

## 2026-04-30（第四十轮）

### 文档：README 更新

- 功能模块新增批量导入和工程化描述
- 后端测试覆盖表更新至 136 个（原 90 个）
- 新增前端测试覆盖表（23 个）
- API 概览新增商品/客户 CSV 导入端点
- 项目结构新增 __tests__ 和 test 目录
- 当前限制移除"前端尚无自动化测试"，新增 CSV 导入限制

## 2026-04-30（第三十九轮）

### 工程：ruff lint 全面修复（72 自动 + 31 手动）

- 自动修复 72 个问题：未使用导入、导入排序
- 手动修复 31 个问题：行过长（E501）、歧义变量名（E741）、尾部空白（W291）
- 新增 pyproject.toml per-file-ignores：SQLAlchemy 前向引用 F821
- ruff check 0 错误，后端 136/136 测试通过

## 2026-04-30（第三十八轮）

### 测试：后端测试补强（116 → 136）

- 新增 test_validation.py（20 个测试）：
  - 认证：无效/缺失 refresh_token
  - 商品：负价格、空名称、SKU 重复、非法价格格式、负库存、停用不存在、价格历史
  - 客户：编辑/删除/转移不存在、空名称
  - 导入：空 CSV、无表头 CSV、非法/负价格
  - 用户管理：管理员用户列表
- 新增 conftest.py：pytest 收集钩子确保 test_ratelimit 始终最后运行
- 后端 136/136 通过

## 2026-04-30（第三十七轮）

### 测试：前端测试补强（10 → 23）

- 新增 client.test.ts（3 个）：API 客户端 baseURL、token 附加、无 token 场景
- 新增 request.test.ts（4 个）：get/post/put/del 封装函数调用验证
- 新增 statusMaps.test.ts（6 个）：商品状态/客户来源/客户等级/订单状态映射完整性
- 前端 23/23 测试通过，TypeScript 编译通过

## 2026-04-30（第三十六轮）

### 体验：列表页空状态提示和分页大小选项

- 4 个列表页（商品/客户/订单/操作日志）新增空状态提示
  - 加载中 → "加载中..."
  - 有筛选条件 → "没有匹配的 XX"
  - 无数据 → "暂无 XX，点击"新增"添加"（引导文案）
- 所有列表页统一 `pageSizeOptions: [10, 20, 50, 100]`
- 前端 10/10 测试通过，TypeScript 编译通过

## 2026-04-30（第三十五轮）

### 工程：前端自动化测试框架搭建

- 安装 Vitest + @testing-library/react + @testing-library/jest-dom + @testing-library/user-event + jsdom
- 配置 vite.config.ts 的 test 块（globals、jsdom、setupFiles、css）
- 创建 src/test/setup.ts 初始化 jest-dom 匹配器
- 新增 10 个前端测试：
  - utils.test.ts（8 个）：formatAmount / formatPercent 纯函数测试
  - ErrorBoundary.test.tsx（2 个）：正常渲染 + 错误捕获
- package.json 新增 test / test:watch 脚本
- 前端 10/10 测试通过，TypeScript 编译通过

## 2026-04-30（第三十四轮）

### 功能：客户 CSV 批量导入

- **EXT-006** 后端新增 `POST /customers/import` 批量导入端点：
  - 支持中文表头（客户名称、电话、联系人、邮箱、来源、等级、备注）和英文表头
  - 手机号唯一性检查（数据库去重 + 批量内去重）
  - 验证：名称必填
  - 记录 `customer_import` 审计日志
- 前端客户列表页新增"导入"按钮
- 后端 116/116 测试通过，前端 TypeScript 编译通过

## 2026-04-30（第三十三轮）

### 功能：商品 CSV 批量导入

- **EXT-005** 后端新增 `POST /products/import` 批量导入端点：
  - 支持中文表头（商品名称、销售价、成本价、库存数量）和英文表头
  - 自动生成唯一 SKU（批次内递增序号，避免碰撞）
  - 验证：名称必填、价格格式/非负、SKU 唯一性
  - 记录 `product_import` 审计日志
- 前端商品列表页新增"导入"按钮，上传 CSV 文件
- 修复 `price_history` 端点缺失 return 语句
- 后端 108/108 测试通过，前端 TypeScript 编译通过。

## 2026-04-30（第三十轮）

### 前端体验：Header 显示当前用户名和角色

- **UX-004** AppLayout 加载时调用 `/auth/me` 获取当前用户信息
- Header 区域显示：用户图标 + 用户名 + 角色标签 + 退出登录按钮
- TypeScript 编译通过，构建成功。

## 2026-04-30（第二十九轮）

### 安全修复：logout 清理 refresh_token

- **SEC-004** 修复前端 logout 未清除 refresh_token 的 bug：
  - AppLayout logout 同时清除 access_token 和 refresh_token
  - client.ts 401 无 refresh_token 分支也清除 token 后再跳转登录页
- 后端 100/100 通过，前端 TypeScript 编译通过。

## 2026-04-30（第二十八轮）

### 文档：API 文档更新

- 新增速率限制章节：429 响应码、X-RateLimit-* 响应头、默认配置
- 新增 RATE_LIMIT_EXCEEDED 错误码
- 修正报表端点参数：`start_date`/`end_date` → `period`（today/7d/30d/this_month/last_month）
- 更新库存预警端点：说明可配置阈值、响应字段
- 更新导出端点：完整查询参数、审计日志记录说明
- 更新审计日志章节：请求元数据字段、21 种操作类型完整列表
- 新增环境变量章节：13 个配置项

## 2026-04-30（第二十七轮）

### 测试补强：导出审计日志测试

- **QA-006** test_export.py 新增审计日志验证测试：
  - 验证导出操作生成正确的审计记录
  - 检查 action=export_products、resource_type=product、actor_name、ip_address
- 全量测试从 99 增至 100，全部通过。

## 2026-04-30（第二十六轮）

### 审计完善：导出操作记录审计日志

- **AUDIT-EXP-001** 导出端点集成审计日志：
  - exports.py 4 个导出端点添加 Request 参数，调用 log_action 记录操作
  - 记录操作者、筛选条件、IP、user_agent、request_id
  - 前端 AuditLogs.tsx 添加 export_products/customers/orders/payments 标签（青色）
- 后端 99/99 通过，前端 TypeScript 编译通过。

## 2026-04-30（第二十五轮）

### 文档：环境变量和部署配置更新

- .env.example 新增 5 个配置项：LOG_FORMAT、INVENTORY_WARNING_THRESHOLD、RATE_LIMIT_MAX、RATE_LIMIT_WINDOW
- deploy/docker-compose.prod.yml 添加新配置项，速率限制默认 100/60s（生产更保守）
- 生产环境默认 LOG_FORMAT=json

## 2026-04-30（第二十四轮）

### 测试补强：文件上传集成测试

- **QA-005** 创建 test_file_upload.py（9 个测试）：
  - 上传 PNG 图片成功
  - 查询图片信息
  - 上传不支持类型（.txt → 400）
  - 上传超过大小限制（→ 400）
  - 查询不存在文件（→ 404）
  - 删除已上传图片 + 删除后再查 404
  - 删除不存在文件（→ 404）
  - 未认证上传（→ 401）
- 使用临时目录避免写入项目 uploads 目录
- 全量测试从 90 增至 99，全部通过。

## 2026-04-30（第二十三轮）

### 文档：测试报告更新

- 测试报告从 51 更新到 90 测试：
  - 新增权限校验测试（9 个）：数据范围、敏感字段、权限码拦截、导出过滤
  - 新增异常路径测试（27 个）：6 模块边界值和错误处理
  - 新增速率限制测试（3 个）：响应头验证、429 触发
  - 更新功能覆盖率矩阵和安全特性验证表
  - 更新已知限制（移除已解决的"数据范围未独立测试"项）

## 2026-04-30（第二十一轮）

### 前端体验：侧边栏菜单修复

- **UX-003** 修复侧边栏菜单问题：
  - 订单菜单路径从 `/sales-orders` 修正为 `/orders`
  - 添加"操作日志"菜单项（`/audit-logs`）
  - 移除未实现的"系统设置"菜单项
  - 修复子路径高亮：`/orders/123` 现在正确高亮"销售订单"
- TypeScript 编译通过，前端构建通过，后端 90/90 通过。

## 2026-04-30（第二十轮）

### 前端体验：错误边界 ErrorBoundary

- **UX-002** 前端错误边界：
  - 新增 `components/ErrorBoundary.tsx`：class component + getDerivedStateFromError
  - 渲染崩溃时显示 Result error 页面（错误信息 + 重试按钮 + 返回首页按钮）
  - main.tsx 包裹 RouterProvider，全局兜底未捕获的渲染错误
- TypeScript 编译通过，前端构建通过。

## 2026-04-30（第十九轮）

### 前端体验：请求层 429 重试和统一错误提示

- **UX-001** 前端请求层改进：
  - 合并两个 axios 实例：request.ts 改为基于 apiClient 的轻量封装
  - client.ts 新增 429 自动重试：等待 Retry-After（最多 5s）后重试一次
  - 统一错误提示：403（无权限）、404（不存在）、429（频繁）、500（服务器错误）、网络失败 → 自动 message.error
  - 401 处理保留 token 刷新逻辑
- TypeScript 编译通过，前端构建通过，后端 90/90 通过。

## 2026-04-30（第十八轮）

### 性能优化：前端路由级代码拆分

- **PERF-001** 前端代码拆分：
  - routes/index.tsx 改为 React.lazy + Suspense 动态导入
  - 所有页面组件（Dashboard、Products、Orders、Customers 等）按路由独立 chunk
  - 新增 lazyPage 辅助函数和全屏 Spin 加载占位
  - bundle 从单个 1,452KB 拆分为 40+ 个按需加载 chunk
  - 页面级模块独立：Dashboard 11KB、Products 4.5KB、Orders 3KB、AuditLogs 206KB
- TypeScript 编译通过，构建成功。

## 2026-04-30（第十七轮）

### 安全加固：API 速率限制

- **SEC-003** 实现基于滑动窗口的 IP 级速率限制：
  - 新增 `app/core/ratelimit.py`：RateLimitMiddleware（stdlib 实现，无外部依赖）
  - 按 IP 地址滑动窗口计数，超限返回 429 + `RATE_LIMIT_EXCEEDED`
  - 正常请求返回 `X-RateLimit-Limit` 和 `X-RateLimit-Remaining` 响应头
  - 非 API 路径（静态文件等）不受限制
  - config.py 新增 `RATE_LIMIT_MAX`（默认 1000）和 `RATE_LIMIT_WINDOW`（默认 60s）
  - main.py 注册中间件
- 新增 test_ratelimit.py（3 个测试）：响应头验证、429 触发验证
- 全量测试从 87 增至 90，全部通过。

## 2026-04-30（第十六轮）

### 质量加固：TypeScript 严格模式 + 结构化日志

- **QUALITY-001** 前端 tsconfig.app.json 启用 `strict: true`，编译零错误。
- **OBS-001** 后端结构化日志：
  - logging.py 重写为支持 JSON/文本双格式，通过 `LOG_FORMAT` 环境变量切换
  - config.py 新增 `LOG_FORMAT` 配置项（默认 `text`，生产环境设 `json`）
  - JSON 格式输出 timestamp、level、logger、message、exception 字段
  - main.py 显式导入日志模块确保初始化
  - seed.py 的 `print()` 改为 `logger.info/error`
- 全量测试 87/87 通过。

## 2026-04-30（第十五轮）

### 扩展：库存预警阈值可配置

- **EXT-003** 库存预警阈值可配置：
  - config.py 新增 `INVENTORY_WARNING_THRESHOLD` 配置项（默认 10，支持环境变量覆盖）
  - reports.py 库存预警 API 默认值改为读取配置项，前端不传 threshold 时使用服务端默认值
  - 前端 Dashboard 不再硬编码阈值，改用 API 返回的 threshold 值动态显示卡片标题
  - 前端 reports.ts 优化：仅在明确传参时才附带 threshold 查询参数
- 全量测试 87/87 通过，前端 TypeScript 编译通过。

## 2026-04-30（第十四轮）

### 测试补强：异常路径和边界值集成测试

- **QA-004** 创建 test_edge_cases.py（27 个测试）：
  - 商品：缺名称、负价格、重复 SKU、404 读写删
  - 客户：空名称、手机号重复、404
  - 订单：未选客户、空明细、不存在商品、数量 0、负单价、库存不足、重复确认、重复取消、编辑非草稿
  - 收款：金额 0、超额、不存在订单、冲正不存在
  - 库存：调整 0、未指定商品、负库存
  - 认证：伪造 Token
- 全量测试从 60 增至 87，全部通过。

## 2026-04-30（第十三轮）

### 前端：审计日志展示请求元数据

- 后端审计日志 API 新增返回 `user_agent` 和 `request_id` 字段
- 前端审计日志页面：IP 列悬停展示 request_id 和 user_agent 摘要
- 后端 60/60 测试通过，前端构建通过。

## 2026-04-30（第十二轮）

### 测试补强：权限校验和数据范围集成测试

- **QA-003** 创建 test_permissions.py（9 个测试）：
  - 客户数据范围：销售员只看到本人客户，管理员看到全部
  - 订单数据范围：销售员只看到本人订单
  - 敏感字段过滤：无 product:view_cost 权限不返回成本价/利润/毛利率
  - 权限码拦截：无权限接口返回 403
  - 导出数据范围：客户和订单 CSV 导出同样过滤
- 创建非超级用户带指定权限的辅助函数 `_create_user_with_perms`
- 全量测试从 51 增至 60，全部通过。

## 2026-04-30（第十一轮）

### 阶段 6 交付物：Windows 启动文档 + README 更新

- **DOC-WINDOWS-001** 创建 docs/windows-setup.md：Docker Desktop 和本地开发两种方式。
- 更新 README.md：
  - 修正测试数为 51
  - 更新项目结构（含生产部署文件）
  - 更新当前限制（移除已完成的旧限制）
- 更新 backlog：阶段 2/3/5 标记为已完成。

## 2026-04-30（第十轮）

### 阶段 6 交付物：生产部署配置

- **DEVOPS-PROD-001** 创建生产 Docker Compose（deploy/docker-compose.prod.yml）：
  - PostgreSQL + 后端 + 前端构建 + Nginx 四容器架构
  - 环境变量强制设置 POSTGRES_PASSWORD 和 JWT_SECRET_KEY
  - 后端启动时自动执行数据库迁移
- **DEVOPS-NGINX-001** 创建 Nginx 反向代理配置（deploy/nginx.conf）：
  - 前端 SPA 路由支持（try_files fallback）
  - API 请求代理到后端，传递 X-Real-IP / X-Forwarded-For / X-Request-ID
  - 静态资源 7 天缓存
- **DEVOPS-BACKUP-001** 创建备份恢复脚本（deploy/backup.sh、deploy/restore.sh）：
  - 支持 Docker 和本地两种环境
  - 自动压缩、30 天清理、恢复前确认
- 创建前端生产 Dockerfile（多阶段构建）

## 2026-04-30（第九轮）

### 阶段 6 交付物：测试报告

- **QA-REPORT-001** 创建阶段测试报告：51/51 通过，按阶段统计，功能覆盖率，安全特性验证，已知限制。

## 2026-04-30（第八轮）

### 阶段 6 交付物：测试文档

- **DOC-004** 创建 docs/testing.md：完整测试文档（51 个测试、5 个文件详解、编写指南、注意事项）。

## 2026-04-30（第七轮）

### 阶段 6 交付物：API 和数据库文档

- **DOC-002** 创建 docs/api.md：完整 API 接口文档（46 个端点、权限码、请求/响应格式、错误码）。
- **DOC-003** 创建 docs/database.md：完整数据库文档（16 张表、ER 关系、字段说明、种子数据、迁移命令）。

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
