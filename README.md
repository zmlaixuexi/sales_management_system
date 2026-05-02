# 销售管理系统

面向中小团队的轻量级 Web 销售管理系统，覆盖商品、客户、订单、库存、收款、报表的内部管理闭环。

## 技术栈

| 层级 | 选型 |
|---|---|
| 前端 | React 19 + TypeScript + Vite 8 + Ant Design |
| 后端 | FastAPI + SQLAlchemy 2.x (sync) + Alembic |
| 数据库 | PostgreSQL 17 |
| 认证 | JWT (python-jose + bcrypt) |
| 部署 | Docker Compose |

## 功能模块

- **认证与权限**：JWT 登录/刷新/退出，角色权限体系（RBAC），数据范围权限，敏感字段过滤，登录失败速率限制，完整登录页面。
- **商品管理**：商品 CRUD、图片上传、SKU 自动生成、利润/毛利率自动计算、价格变更记录、派生销售字段（sales_quantity/sales_amount）。
- **客户管理**：客户 CRUD、手机号重复检测、归属转移。
- **订单管理**：草稿创建、确认（扣减库存）、取消（回滚库存）、状态机（draft→confirmed→completed/cancelled）、操作日志查询、支付路径对齐规范。
- **收款管理**：收款登记（自动更新订单状态）、冲正。
- **库存管理**：库存流水追踪、手工调整、可配置预警阈值。
- **报表看板**：销售汇总、趋势、商品排行、客户排行、销售人员排行、库存预警。
- **操作日志**：关键业务操作日志查询，记录 IP/user_agent/request_id，手机号和邮箱自动脱敏，用户管理操作审计。
- **数据导出**：商品、客户、订单、收款 CSV 导出，按权限过滤数据范围。
- **批量导入**：商品/客户 CSV 批量导入，支持中英文表头，逐行校验和错误收集。
- **工程化**：前端代码拆分（lazy loading）、TypeScript strict 模式、Vitest 测试框架、ruff lint、ESLint、结构化 JSON 日志、Pydantic 请求/响应模型、分页响应辅助函数、文件上传所有权检查。

## 快速启动

### 前置条件

- Docker & Docker Compose
- （本地开发可选）Python 3.11+、Node.js 20+

### Docker Compose 启动

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 启动所有服务
cd deploy
docker compose -f docker-compose.dev.yml up -d

# 3. 运行数据库迁移和种子数据
docker compose -f docker-compose.dev.yml exec backend bash
# 在容器内：
alembic upgrade head
python -m app.db.seed

# 4. 访问
# 前端：http://localhost:5173
# 后端 API 文档：http://localhost:8000/docs
# 默认管理员：admin / admin123
```

### 本地开发

**后端：**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed  # 初始化种子数据
uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

数据库需要 PostgreSQL 运行在 localhost:5432，或修改 `.env` 中的 `DATABASE_URL`。

### 常用命令（Makefile）

```bash
make help              # 查看所有可用命令
make dev               # 启动 Docker 开发环境
make dev-backend       # 启动后端开发服务器
make dev-frontend      # 启动前端开发服务器
make test              # 运行全部测试（后端 + 前端）
make lint              # 运行全部 lint 检查
make build             # 完整构建（lint + test + build）
make db-migrate        # 运行数据库迁移
make db-seed           # 初始化种子数据
```

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/          # API 路由（auth, products, customers, orders, payments, inventory, reports, audit_logs, exports, users）
│   │   ├── core/            # 配置、安全工具、日志、速率限制
│   │   ├── db/              # 数据库会话
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 业务服务（文件上传、审计日志、数据导出）
│   │   └── main.py          # 应用入口
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试
├── frontend/                # React 前端
│   ├── src/
│   │   ├── api/             # API 调用层
│   │   ├── components/      # 公共组件
│   │   ├── pages/           # 页面组件
│   │   ├── routes/          # 路由配置
│   │   ├── __tests__/       # Vitest 测试
│   │   ├── test/            # 测试 setup
│   │   ├── stores/          # 状态管理
│   │   ├── types/           # TypeScript 类型
│   │   └── utils/           # 工具函数
│   └── vite.config.ts
├── deploy/                  # 部署配置
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── nginx.conf
│   ├── backup.sh
│   ├── restore.sh
│   ├── backup.ps1
│   └── restore.ps1
├── docs/                    # 文档
└── .env.example             # 环境变量示例
```

## 测试

```bash
# 后端测试（910 个）
cd backend
source .venv/bin/activate
pytest tests/ -v

# 前端测试（382 个）
cd frontend
npm test

# 前端构建检查
npx tsc --noEmit
npm run build
```

### 后端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 认证 | 20 | 登录成功/失败、Token 刷新/无效 token 401/access token 被拒 401、当前用户、权限校验、禁用用户刷新被拒、密码修改（含未认证 401/空旧密码 422）、登录失败速率限制（连续失败触发 429） |
| 登录速率限制函数 | 8 | _check_login_rate_limit 阈值通过/拒绝/独立 IP/过期清理/混合过期+新鲜条目/错误码验证，_record_login_fail 时间戳追加 |
| 健康检查 | 25 | 健康状态、版本信息、安全响应头（含 Cache-Control: no-store）、请求日志记录、请求 ID 生成/透传/日志关联/响应体、生产环境 JWT 密钥检查、未处理异常 JSON 响应、CORS 允许/拒绝/credentials/方法白名单/自定义头白名单/空Origin/nullOrigin验证、生产环境 OpenAPI 禁用、连接池状态 |
| 集成（端到端） | 28 | 完整业务流程：商品→客户→订单→库存→收款→报表→订单日志 |
| 审计日志 | 22 | 全操作类型日志、筛选、操作类型列表、用户管理操作审计日志、LIKE 注入搜索防护（%/）、page_size=100 边界 |
| 数据导出 | 37 | 四模块 CSV 导出、多维度筛选、空数据、认证、审计日志、BOM/表头/字段数/状态映射验证 |
| 文件上传 | 24 | 上传成功、类型/大小校验、获取/删除、认证、文件所有权检查、伪装扩展名/魔数字节、审计日志 |
| 权限校验 | 10 | 数据范围、敏感字段过滤、权限码拦截、导出过滤 |
| 权限辅助函数 | 27 | _get_user_permissions 多角色收集/去重，has_permission，check_owner_or_forbid，parse_uuid_or_400，resp，paginated_resp，get_or_404（存在/不存在/软删除/无 deleted_at），generate_sequential_code（含序号 > 9 数字排序验证），paginate |
| 异常路径 | 33 | 缺字段、负值、重复、404、状态转换、库存不足、伪造 Token、无效 UUID、收款导出数据范围、LIKE 注入防护（订单+客户） |
| 验证补充 | 25 | refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表、密码强度、客户 source/level 枚举 |
| 边界测试 | 47 | 认证边界、订单状态机、收款边界、用户管理、库存调整、Token 刷新、流水类型筛选 |
| 报表与审计查询 | 48 | 销售汇总（6 种 period + 无效 period 返回 400 + Decimal 精度验证）、趋势、排行、客户排行（含数据范围）、销售人员排行（含数据范围）、库存预警、权限、period 参数校验、审计日志列表/筛选/分页/关键词/操作类型、limit 边界值（0/50/51） |
| 商品导入 | 18 | CSV 成功/带 SKU/重复 SKU/空名称/非 CSV/认证/中文表头/大小限制/行数上限/HTML 标签剥离/commit 回滚失败/权限 403 |
| 客户导入 | 17 | CSV 成功/带详情/手机号重复/批量内重复/空名称/非 CSV/认证/大小限制/行数上限/HTML 标签剥离/无效 source/无效 level/commit 回滚失败/权限 403 |
| 速率限制 | 5 | 响应头验证、429 触发（含响应头）、窗口清理 |
| XSS 防护 | 14 | escape_like 特殊字符转义、strip_html XSS 防护 |
| 用户管理 | 35 | 用户列表/搜索、创建（含重复用户名）、编辑、禁用、角色变更、编辑时无效角色 ID、403 权限、创建/编辑审计日志记录、输入长度溢出、无效UUID 400、畸形role_ids 400、空角色清空、密码无数字 422、LIKE 注入搜索防护（%/）、page_size=100 边界 |
| 商品 CRUD | 49 | 商品详情、软删除、列表排除已删除、分类筛选/排序、SKU 更新、CSV 导入、价格变更、输入长度溢出、成本字段权限过滤（列表+详情）、LIKE 注入搜索防护（%/）、page_size=100 边界 |
| 客户 CRUD | 36 | 客户详情、编辑、转移、软删除、来源筛选、关键词搜索、CSV 导入、输入长度溢出、备注 XSS 清理、转移不存在用户 404、邮箱重复边界、LIKE 注入搜索防护、page_size=100 边界、page_size=101 超限 422 |
| 订单 CRUD | 58 | 创建（正常/空明细/客户不存在/商品不存在/零数量/负价拒绝）、详情/404/列表/状态筛选/客户筛选、编辑草稿（含负价拒绝）、确认/取消/库存不足、软删除商品订单确认/取消回归、订单号回退、零利润边界、订单日志端点、取消草稿无库存变动、取消无效UUID 422、取消已完成订单 400、仅更新备注、零价阻止下单、关键字搜索、LIKE 注入防护、page_size=1 边界、降序排列验证、订单日志成本字段权限过滤、page_size=100 边界、备注 XSS 清理 |
| 收款 | 36 | 创建（部分收款→完成、超额、零金额、草稿不可收款、订单不存在）、列表/按订单筛选/数据范围过滤、冲正/重复冲正/不存在/关联订单已删除、冲正状态回退、非所有者拒绝、列表排除已冲正、金额多小数位精度、列表降序排列验证、page_size=100 边界、备注 XSS 清理 |
| 库存 | 26 | 手工调整（增加/减少/归零/零调整拒绝/超量拒绝/商品不存在）、流水列表/按商品筛选/按类型筛选/组合筛选/字段完整性、备注 XSS 清理、小数数量拒绝、备注长度边界、page_size=100 边界 |
| 订单金额计算 | 10 | _calc_order_totals 金额/零值/精度，_prepare_item 价格/折扣/快照/低于成本价阻止 |
| 商品利润计算 | 6 | _calc_profit 基本利润/除零保护/亏损/零利润/精度/高毛利率 |
| 审计服务函数 | 11 | _mask_sensitive 脱敏（含手机号/邮箱），model_to_dict 模型转换，get_request_meta |
| 日志格式器 | 18 | _JsonFormatter JSON 输出/异常/extra_fields，log_action 容错，request_id/user_id contextvar 注入/空值/优先级，_TextFormatter 文本格式/日期格式，setup_logging 级别/第三方抑制/格式器选择/无效级别回退/handler 清理 |
| 导出辅助函数 | 22 | _dec/_str/_dt CSV 格式化，_product_row/_order_row 成本字段过滤，状态映射，_customer_row/_payment_row |
| 导出 API 辅助函数 | 3 | _csv_filename 文件名格式/前缀/后缀 |
| 文件服务 | 13 | 扩展名/MIME/大小/正常/webp/大写扩展名/扩展名与 MIME 独立校验/边界大小/魔数字节校验 |
| CSV 导入校验 | 9 | 文件名/扩展名/BOM/编码/大小限制/空文件/仅有表头 |
| Schema 校验器 | 23 | 全部 Pydantic field_validator：单价非负/金额正数/密码强度/strip_html XSS 防护 |
| 安全模块 | 14 | hash_password bcrypt 哈希/盐值、verify_password 正确/错误/空密码、create_access_token 解码/type/exp/自定义过期、create_refresh_token 解码/type/exp/长于 access |
| 报表辅助函数 | 11 | _date_range 全分支（today/7d/30d/this_month/last_month/跨月边界/跨年边界/月初/无效 period）、_apply_data_scope 管理员/销售 |
| 慢查询 | 8 | 慢查询结构化日志记录、SQL 截断、阈值验证、request_id 关联、参数截断边界、SQL 恰好 500 字符不截断 |
| 商品辅助函数 | 10 | _validate_category_id 存在/不存在，_get_default_category_id 已存在/自动创建，_batch_sales_stats 空列表/无订单/已确认/排除草稿取消/排除软删除/多订单汇总 |
| 客户辅助函数 | 4 | _validate_owner_user 活跃/不存在/已禁用/软删除 |
| 订单库存辅助函数 | 10 | _deduct_inventory 正常/库存不足/商品不存在/软删除/多明细/恰好等于需求，_restore_inventory 正常/不存在静默跳过/软删除跳过/多明细 |
| 订单明细校验 | 10 | _validate_and_prepare_items 单个/多商品/不存在/软删除/停用/禁用/自定义单价/空列表/无效 UUID/混合 |
| 收款登记服务 | 10 | register_payment 部分/全额/分次收款，订单不存在/草稿/取消/完成拒绝，超额/恰好剩余，操作人记录 |
| 请求体大小限制 | 9 | GET/OPTIONS/HEAD 不受限，正常 POST 通过，超限返回 413，multipart 豁免，恰好等于限制通过，/uploads 路径豁免 |
| 文件上传权限 | 1 | 无 product:create 权限用户上传返回 403 |
| 导出敏感字段 + 报表利润权限 | 6 | 导出商品/订单 CSV 成本价列权限过滤，报表概览利润字段权限过滤 |
| 对象级权限 | 11 | 客户/订单 detail/update/delete/transfer 非 owner 返回 403，管理员绕过 |
| 边界条件 + 安全 | 6 | SQL 注入搜索安全（3 项）、分页边界 page=0/page_size=101/page_size=-1（3 项） |
| 软删除过滤 | 2 | 客户列表排除已删除、支付列表排除已删除订单 |
| 外键验证 | 4 | 客户 owner_user_id 无效/不存在、订单 customer_id 不存在、订单 items 含不存在商品 |
| **合计** | **938** | |

### 前端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 拦截器 | 14 | 401 刷新重试、401 无 refresh 跳转、403/404/500 错误提示、网络错误、429 重试、_toastDisplayed 标记 |
| utils | 19 | formatAmount / formatPercent / getApiErrorMessage 纯函数（含负数/大数/零/空字符串边界） |
| 商品表单 | 12 | 新增模式标题/字段/提交/取消/上传/编辑模式（标题/fetchProduct/数据填充/保存修改） |
| 客户表单 | 12 | 新增模式标题/字段/提交/编辑模式（标题/fetchCustomer/数据填充/保存修改） |
| usePaginatedList | 11 | 初始加载、错误处理、筛选、分页切换、刷新、空结果、_toastDisplayed 跳过 |
| 订单表单 | 11 | 新增模式标题/字段/提交/编辑模式（标题/fetchOrder/保存修改） |
| auth store | 14 | login/logout/fetchUser/hasPermission/loading 状态、login success:false 不存 token、fetchUser success:false 不设 user、空权限数组 |
| 商品列表 | 11 | 渲染/搜索/筛选/新增按钮/表格数据/空状态/错误状态+重试/loading 状态 |
| 客户列表 | 11 | 渲染/搜索/筛选/新增按钮/表格数据/空状态/错误状态+重试/loading 状态 |
| 订单列表 | 11 | 渲染/搜索/筛选/新建按钮/表格数据/空状态/错误状态+重试/loading 状态 |
| 审计日志 | 11 | 渲染/筛选/表格/操作标签中文映射/资源类型中文/空值/列标题/fetchAuditActions 调用/空状态/错误状态+重试/loading 状态 |
| 用户列表 | 14 | 渲染/搜索/表格数据/角色标签/超级管理员标记/新建按钮/空状态/loading 状态/错误重试/编辑弹窗/启用停用切换 |
| 报表 API | 8 | fetchSalesSummary（含无参数）/Trend/ProductRanking/InventoryWarning（含无阈值）/CustomerRanking/SalespersonRanking |
| 商品 API | 16 | fetchProducts（筛选/排序/派生字段）/fetchProduct（完整详情+图片）/create（可选字段）/update（价格）/delete/disable/priceHistory/uploadImage（文件信息） |
| 收款列表 | 12 | 渲染/筛选/表格数据/loading 状态/错误重试/收款 ID 截断/空备注显示 |
| 库存列表 | 11 | 渲染/筛选/表格数据/loading 状态/错误重试/空备注显示 |
| 报表中心 | 11 | 渲染标题/周期选择器/五个标签页/客户排行/销售排行数据/周期切换重载/API 默认周期 |
| 客户详情 | 9 | 加载显示客户名称/返回按钮/loading 状态 |
| 订单详情 | 9 | 加载显示订单号/返回按钮/loading 状态 |
| Dashboard | 11 | 渲染看板标题/期间选择器/数据卡片/趋势汇总/库存预警数据/期间选项数/切换重载 |
| 客户 API | 12 | fetchCustomers（完整数据）/fetchCustomer/create（可选字段）/update（联系方式）/delete/transfer（不同目标） |
| 状态映射 | 10 | 商品/客户来源/客户等级/订单（含 partially_paid/completed）/收款状态映射完整性（导入共享常量） |
| 订单 API | 14 | fetchOrders（关键词/客户ID/分页/无参数）/fetchOrder（完整明细+收款）/create（多商品）/update（明细）/confirm/cancel |
| downloadCsv | 9 | 成功下载、查询参数、过滤、错误、文件名提取、attachment 前缀、全空参数、全有效参数 |
| useSubmit | 11 | 成功调用/提交中状态/错误提示/Ant Design 校验静默/防重/_toastDisplayed 跳过/默认 fallback/非 Error 异常/错误恢复/response.data.error.message/detail.message 提取 |
| AppLayout | 8 | 用户加载/菜单导航/退出/失败/回退/系统标题/菜单项数/路径高亮 |
| auth API | 8 | login/refresh/logout/getMe（权限列表）/changePassword/token 返回 |
| 用户 API | 11 | fetchUsers（分页/完整数据）/create（最少/完整参数）/update（角色）/fetchRoles |
| 审计日志 API | 11 | fetchAuditLogs（筛选/日期/分页/关键词/完整条目/actor_id）/fetchAuditActions（空列表） |
| 收款 API | 11 | fetchPayments（分页/完整记录）/createPayment（现金/微信/支付宝/备注）/reversePayment |
| 库存 API | 10 | fetchInventory（分页/完整流水/无参数）/adjust（正负数/备注） |
| request 封装 | 8 | get/post/put/del/upload 调用验证（含无参数 get、无 body post/put） |
| ErrorBoundary | 5 | 正常渲染 + 错误捕获 + 重试恢复 + 路由重置 + 返回首页 |
| ProtectedRoute | 5 | 无 token 重定向/加载中/已认证渲染/fetchUser 失败/异步重定向/Spin large 尺寸 |
| 登录页 | 7 | 渲染标题/输入框/登录按钮/提交调用 login/登录失败错误提示/成功跳转首页/redirect 参数跳转 |
| API client | 7 | baseURL、token 附加、无 token、timeout 15s、Content-Type、X-Request-ID 生成和唯一性 |
| NotFound | 3 | 404 渲染/返回首页按钮/按钮点击导航 |
| **合计** | **380** | |

## API 概览

所有 API 端点均包含 Swagger 文档（`/api/docs`），支持在线调试。路由使用 Pydantic 请求/响应模型，错误响应（401/403/400/404/409）已文档化。

| 模块 | 路径前缀 | 说明 |
|---|---|---|
| 认证 | `/api/v1/auth` | 登录、刷新、退出、当前用户 |
| 用户 | `/api/v1/users` | 用户列表、创建、编辑、角色管理 |
| 商品 | `/api/v1/products` | 商品 CRUD + 停用 + 价格历史 + CSV 批量导入 |
| 文件 | `/api/v1/files` | 图片上传 |
| 客户 | `/api/v1/customers` | 客户 CRUD + 归属转移 + CSV 批量导入 |
| 订单 | `/api/v1/sales-orders` | 订单 CRUD + 确认/取消 + 操作日志 + 支付 |
| 收款 | `/api/v1/payments` | 收款登记 + 冲正 |
| 库存 | `/api/v1/inventory` | 库存流水 + 手工调整 |
| 报表 | `/api/v1/reports` | 销售汇总、趋势、排行、客户排行、销售人员排行、库存预警 |
| 操作日志 | `/api/v1/audit-logs` | 操作日志查询 |
| 数据导出 | `/api/v1/exports` | 商品、客户、订单、收款 CSV 导出 |

## 当前限制

- 数据范围权限仅支持"本人"和"全部"两级，暂无"团队"级别。
- 文件上传仅支持本地存储，未接入对象存储（S3/OSS）。
- 速率限制和登录失败计数基于内存，多实例部署时不共享状态。
- CSV 导入不支持分类映射和图片导入。

## 环境变量

参见 `.env.example`，关键变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | 数据库连接 | `postgresql+psycopg://postgres:postgres@localhost:5432/sales_management` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `change-me` |
| `UPLOAD_DIR` | 上传文件目录 | `uploads` |
| `MAX_IMAGE_SIZE_MB` | 图片大小限制(MB) | `5` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_FORMAT` | 日志格式（`text` 或 `json`） | `text` |
| `RATE_LIMIT_MAX` | API 速率限制（每窗口请求数） | `1000` |
| `RATE_LIMIT_WINDOW` | 速率限制窗口（秒） | `60` |
| `INVENTORY_WARNING_THRESHOLD` | 库存预警阈值 | `10` |
| `SLOW_REQUEST_THRESHOLD_MS` | 慢请求阈值（毫秒） | `1000` |
| `SLOW_SQL_THRESHOLD_MS` | 慢 SQL 阈值（毫秒） | `200` |
| `MAX_CSV_IMPORT_ROWS` | CSV 导入行数上限 | `1000` |
| `DB_POOL_SIZE` | 数据库连接池大小 | `5` |
| `DB_MAX_OVERFLOW` | 连接池最大溢出 | `10` |
| `DB_POOL_RECYCLE_SECONDS` | 连接回收时间（秒） | `1800` |

## License

MIT
