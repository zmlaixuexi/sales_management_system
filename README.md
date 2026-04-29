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

- **认证与权限**：JWT 登录/刷新/退出，角色权限体系（RBAC），数据范围权限，敏感字段过滤。
- **商品管理**：商品 CRUD、图片上传、SKU 自动生成、利润/毛利率自动计算、价格变更记录。
- **客户管理**：客户 CRUD、手机号重复检测、归属转移。
- **订单管理**：草稿创建、确认（扣减库存）、取消（回滚库存）、状态机（draft→confirmed→completed/cancelled）。
- **收款管理**：收款登记（自动更新订单状态）、冲正。
- **库存管理**：库存流水追踪、手工调整、可配置预警阈值。
- **报表看板**：销售汇总、趋势、商品排行、库存预警。
- **操作日志**：关键业务操作日志查询，记录 IP/user_agent/request_id。
- **数据导出**：商品、客户、订单、收款 CSV 导出，按权限过滤数据范围。
- **批量导入**：商品/客户 CSV 批量导入，支持中英文表头，逐行校验和错误收集。
- **工程化**：前端代码拆分（lazy loading）、TypeScript strict 模式、Vitest 测试框架、ruff lint、ESLint、结构化 JSON 日志、Pydantic 请求/响应模型。

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

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/          # API 路由（auth, products, customers, orders, payments, inventory, reports, audit_logs, exports）
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
│   └── restore.sh
├── docs/                    # 文档
└── .env.example             # 环境变量示例
```

## 测试

```bash
# 后端测试（201 个）
cd backend
source .venv/bin/activate
pytest tests/ -v

# 前端测试（77 个）
cd frontend
npm test

# 前端构建检查
npx tsc --noEmit
npm run build
```

### 后端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 认证 | 7 | 登录成功/失败、Token 刷新、当前用户、权限校验 |
| 健康检查 | 3 | 健康状态、版本信息、安全响应头验证 |
| 集成（端到端） | 24 | 完整业务流程：商品→客户→订单→库存→收款→报表 |
| 审计日志 | 9 | 全操作类型日志、筛选、操作类型列表 |
| 数据导出 | 9 | 四模块 CSV 导出、筛选、空数据、认证、审计日志 |
| 文件上传 | 9 | 上传成功、类型/大小校验、获取/删除、认证 |
| 权限校验 | 9 | 数据范围、敏感字段过滤、权限码拦截、导出过滤 |
| 异常路径 | 27 | 缺字段、负值、重复、404、状态转换、库存不足、伪造 Token |
| 验证补充 | 20 | refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表 |
| 边界测试 | 36 | 认证边界、订单状态机、收款边界、用户管理、库存调整、Token 刷新 |
| 报表 | 12 | 销售汇总（6 种 period）、趋势、排行、库存预警、权限 |
| 审计查询 | 10 | 日志列表、筛选、分页、关键词、操作类型、权限 |
| 商品导入 | 8 | CSV 成功/带 SKU/重复 SKU/空名称/非 CSV/认证/中文表头 |
| 客户导入 | 8 | CSV 成功/带详情/手机号重复/批量内重复/空名称/非 CSV/认证 |
| 速率限制 | 3 | 响应头验证、429 触发 |
| SQL 注入防护 | 6 | escape_like 特殊字符转义 |
| **合计** | **201** | |

### 前端测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| utils | 8 | formatAmount / formatPercent 纯函数 |
| ErrorBoundary | 2 | 正常渲染 + 错误捕获 |
| API client | 3 | baseURL、token 附加、无 token |
| request 封装 | 4 | get/post/put/del 调用验证 |
| 状态映射 | 6 | 商品/客户/订单状态映射完整性 |
| 商品 API | 7 | fetchProducts/fetchProduct/create/update/delete/disable/uploadImage |
| 客户 API | 6 | fetchCustomers/fetchCustomer/create/update/delete/transfer |
| 订单 API | 6 | fetchOrders/fetchOrder/create/update/confirm/cancel |
| 收款 API | 5 | fetchPayments/筛选/createPayment/备注/reversePayment |
| 报表 API | 6 | fetchSalesSummary/Trend/ProductRanking/InventoryWarning |
| 审计日志 API | 5 | fetchAuditLogs/筛选/日期范围/数据解析/fetchAuditActions |
| auth store | 11 | login/logout/fetchUser/hasPermission/loading 状态 |
| downloadCsv | 6 | 成功下载、查询参数、过滤、错误、文件名提取 |
| **合计** | **77** | |

## API 概览

所有 API 端点均包含 Swagger 文档（`/api/docs`），支持在线调试。路由使用 Pydantic 请求/响应模型，错误响应（401/403/400/404/409）已文档化。

| 模块 | 路径前缀 | 说明 |
|---|---|---|
| 认证 | `/api/v1/auth` | 登录、刷新、退出、当前用户 |
| 用户 | `/api/v1/users` | 用户列表 |
| 商品 | `/api/v1/products` | 商品 CRUD + 停用 + 价格历史 + CSV 批量导入 |
| 文件 | `/api/v1/files` | 图片上传 |
| 客户 | `/api/v1/customers` | 客户 CRUD + 归属转移 + CSV 批量导入 |
| 订单 | `/api/v1/sales-orders` | 订单 CRUD + 确认/取消 |
| 收款 | `/api/v1/payments` | 收款登记 + 冲正 |
| 库存 | `/api/v1/inventory` | 库存流水 + 手工调整 |
| 报表 | `/api/v1/reports` | 销售汇总、趋势、排行、库存预警 |
| 操作日志 | `/api/v1/audit-logs` | 操作日志查询 |
| 数据导出 | `/api/v1/exports` | 商品、客户、订单、收款 CSV 导出 |

## 当前限制

- 数据范围权限仅支持"本人"和"全部"两级，暂无"团队"级别。
- 文件上传仅支持本地存储，未接入对象存储（S3/OSS）。
- 速率限制基于内存，多实例部署时不共享状态。
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
