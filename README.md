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

- **认证与权限**：JWT 登录/刷新/退出，角色权限体系（RBAC），数据范围权限，敏感字段过滤，登录失败速率限制。
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
# 后端测试（600 个）
cd backend
source .venv/bin/activate
pytest tests/ -v

# 前端测试（278 个）
cd frontend
npm test

# 前端构建检查
npx tsc --noEmit
npm run build
```

### 后端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 认证 | 16 | 登录成功/失败、Token 刷新、当前用户、权限校验、禁用用户刷新被拒、密码修改、登录失败速率限制（连续失败触发 429） |
| 健康检查 | 17 | 健康状态、版本信息、安全响应头、请求日志记录、请求 ID 生成/透传/日志关联/响应体、生产环境 JWT 密钥检查、未处理异常 JSON 响应、CORS 允许/拒绝验证、生产环境 OpenAPI 禁用 |
| 集成（端到端） | 28 | 完整业务流程：商品→客户→订单→库存→收款→报表→订单日志 |
| 审计日志 | 19 | 全操作类型日志、筛选、操作类型列表、用户管理操作审计日志 |
| 数据导出 | 37 | 四模块 CSV 导出、多维度筛选、空数据、认证、审计日志、BOM/表头/字段数/状态映射验证 |
| 文件上传 | 22 | 上传成功、类型/大小校验、获取/删除、认证、文件所有权检查（非所有者返回 403） |
| 权限校验 | 10 | 数据范围、敏感字段过滤、权限码拦截、导出过滤 |
| 权限辅助函数 | 10 | _get_user_permissions 多角色收集/去重，has_permission，check_owner_or_forbid，parse_uuid_or_400 |
| 异常路径 | 31 | 缺字段、负值、重复、404、状态转换、库存不足、伪造 Token、无效 UUID、收款导出数据范围 |
| 验证补充 | 25 | refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表、密码强度、客户 source/level 枚举 |
| 边界测试 | 47 | 认证边界、订单状态机、收款边界、用户管理、库存调整、Token 刷新、流水类型筛选 |
| 报表与审计查询 | 46 | 销售汇总（6 种 period + 无效 period 返回 400）、趋势、排行、客户排行（含数据范围）、销售人员排行（含数据范围）、库存预警、权限、period 参数校验、审计日志列表/筛选/分页/关键词/操作类型 |
| 商品导入 | 17 | CSV 成功/带 SKU/重复 SKU/空名称/非 CSV/认证/中文表头/大小限制/行数上限/HTML 标签剥离/commit 回滚失败 |
| 客户导入 | 16 | CSV 成功/带详情/手机号重复/批量内重复/空名称/非 CSV/认证/大小限制/行数上限/HTML 标签剥离/无效 source/无效 level/commit 回滚失败 |
| 速率限制 | 4 | 响应头验证、429 触发、窗口清理 |
| XSS 防护 | 14 | escape_like 特殊字符转义、strip_html XSS 防护 |
| 用户管理 | 23 | 用户列表/搜索、创建（含重复用户名）、编辑、禁用、角色变更、编辑时无效角色 ID、403 权限、创建/编辑审计日志记录 |
| 商品 CRUD | 42 | 商品详情、软删除、列表排除已删除、分类筛选/排序、SKU 更新、CSV 导入、价格变更 |
| 客户 CRUD | 26 | 客户详情、编辑、转移、软删除、来源筛选、关键词搜索、CSV 导入 |
| 订单 CRUD | 41 | 创建（正常/空明细/客户不存在/商品不存在/零数量/负价拒绝）、详情/404/列表/状态筛选/客户筛选、编辑草稿（含负价拒绝）、确认/取消/库存不足、订单号回退 |
| 收款 | 25 | 创建（部分收款→完成、超额、零金额、草稿不可收款、订单不存在）、列表/按订单筛选/数据范围过滤、冲正/重复冲正/不存在/关联订单已删除 |
| 库存 | 20 | 手工调整（增加/减少/归零/零调整拒绝/超量拒绝/商品不存在）、流水列表/按商品筛选/按类型筛选/字段完整性 |
| 订单金额计算 | 10 | _calc_order_totals 金额/零值/精度，_prepare_item 价格/折扣/快照/低于成本价阻止 |
| 商品利润计算 | 6 | _calc_profit 基本利润/除零保护/亏损/零利润/精度/高毛利率 |
| 审计服务函数 | 11 | _mask_sensitive 脱敏（含手机号/邮箱），model_to_dict 模型转换，get_request_meta |
| 日志格式器 | 6 | _JsonFormatter JSON 输出/异常/extra_fields，log_action 容错 |
| 导出辅助函数 | 13 | _dec/_str/_dt CSV 格式化 |
| 文件服务 | 4 | 扩展名/MIME/大小/正常 |
| CSV 导入校验 | 9 | 文件名/扩展名/BOM/编码/大小限制/空文件/仅有表头 |
| 慢查询 | 5 | 慢查询日志记录与阈值验证 |
| **合计** | **600** | |

### 前端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 拦截器 | 14 | 401 刷新重试、401 无 refresh 跳转、403/404/500 错误提示、网络错误、429 重试、_toastDisplayed 标记 |
| utils | 13 | formatAmount / formatPercent / getApiErrorMessage 纯函数 |
| 商品表单 | 12 | 新增模式标题/字段/提交/取消/上传/编辑模式（标题/fetchProduct/数据填充/保存修改） |
| 客户表单 | 12 | 新增模式标题/字段/提交/编辑模式（标题/fetchCustomer/数据填充/保存修改） |
| usePaginatedList | 11 | 初始加载、错误处理、筛选、分页切换、刷新、空结果、_toastDisplayed 跳过 |
| 订单表单 | 11 | 新增模式标题/字段/提交/编辑模式（标题/fetchOrder/保存修改） |
| auth store | 11 | login/logout/fetchUser/hasPermission/loading 状态 |
| 商品列表 | 10 | 渲染/搜索/筛选/新增按钮/表格数据/空状态/错误状态+重试 |
| 客户列表 | 10 | 渲染/搜索/筛选/新增按钮/表格数据/空状态/错误状态+重试 |
| 订单列表 | 10 | 渲染/搜索/筛选/新建按钮/表格数据/空状态/错误状态+重试 |
| 审计日志 | 10 | 渲染/筛选/表格/操作标签中文映射/资源类型中文/空值/列标题/fetchAuditActions 调用/空状态/错误状态+重试 |
| 用户列表 | 9 | 渲染/搜索/表格数据/角色标签/超级管理员标记/新建按钮/空状态 |
| 报表 API | 8 | fetchSalesSummary（含无参数）/Trend/ProductRanking/InventoryWarning（含无阈值）/CustomerRanking/SalespersonRanking |
| 商品 API | 8 | fetchProducts/fetchProduct/create/update/delete/disable/uploadImage/priceHistory |
| 收款列表 | 8 | 渲染/筛选/表格数据 |
| 库存列表 | 8 | 渲染/筛选/表格数据 |
| 报表中心 | 8 | 渲染标题/周期选择器/五个标签页 |
| 客户详情 | 8 | 加载显示客户名称/返回按钮 |
| 订单详情 | 8 | 加载显示订单号/返回按钮 |
| Dashboard | 8 | 渲染看板标题/期间选择器/数据卡片 |
| 客户 API | 7 | fetchCustomers（含无参数）/fetchCustomer/create/update/delete/transfer |
| 状态映射 | 6 | 商品/客户/订单状态映射完整性 |
| 订单 API | 6 | fetchOrders/fetchOrder/create/update/confirm/cancel |
| downloadCsv | 6 | 成功下载、查询参数、过滤、错误、文件名提取 |
| useSubmit | 6 | 成功调用/提交中状态/错误提示/Ant Design 校验静默/防重/_toastDisplayed 跳过 |
| AppLayout | 5 | 用户加载/菜单导航/退出/失败/回退 |
| auth API | 5 | login/refresh/logout/getMe/changePassword 路径验证 |
| 用户 API | 5 | fetchUsers/fetchUser/create/update/roles |
| 审计日志 API | 5 | fetchAuditLogs/筛选/日期范围/数据解析/fetchAuditActions |
| 收款 API | 5 | fetchPayments/筛选/createPayment/备注/reversePayment |
| 库存 API | 5 | fetchInventory/adjust/筛选 |
| request 封装 | 5 | get/post/put/del/upload 调用验证 |
| ErrorBoundary | 5 | 正常渲染 + 错误捕获 + 重试恢复 + 路由重置 + 返回首页 |
| ProtectedRoute | 4 | 无 token 重定向/加载中/已认证渲染/fetchUser 失败/异步重定向 |
| API client | 3 | baseURL、token 附加、无 token |
| NotFound | 3 | 404 渲染/返回首页按钮/按钮点击导航 |
| **合计** | **278** | |

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

## License

MIT
