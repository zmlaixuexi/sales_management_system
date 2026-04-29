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

- **认证与权限**：JWT 登录/刷新/退出，角色权限体系（RBAC）。
- **商品管理**：商品 CRUD、图片上传、SKU 自动生成、利润/毛利率自动计算、价格变更记录。
- **客户管理**：客户 CRUD、手机号重复检测、归属转移。
- **订单管理**：草稿创建、确认（扣减库存）、取消（回滚库存）、状态机（draft→confirmed→completed/cancelled）。
- **收款管理**：收款登记（自动更新订单状态）、冲正。
- **库存管理**：库存流水追踪、手工调整。
- **报表看板**：销售汇总、趋势、商品排行、库存预警。

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
python -m app.seed

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
python -m app.seed  # 初始化种子数据
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
│   │   ├── api/v1/          # API 路由（auth, products, customers, orders, payments, inventory, reports）
│   │   ├── core/            # 配置、安全工具
│   │   ├── db/              # 数据库会话
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── services/        # 业务服务（文件上传）
│   │   └── main.py          # 应用入口
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试
├── frontend/                # React 前端
│   ├── src/
│   │   ├── api/             # API 调用层
│   │   ├── components/      # 公共组件
│   │   ├── pages/           # 页面组件
│   │   ├── routes/          # 路由配置
│   │   ├── stores/          # 状态管理
│   │   ├── types/           # TypeScript 类型
│   │   └── utils/           # 工具函数
│   └── vite.config.ts
├── deploy/                  # 部署配置
│   └── docker-compose.dev.yml
├── docs/                    # 文档
└── .env.example             # 环境变量示例
```

## 测试

```bash
# 后端测试（全部 34 个）
cd backend
source .venv/bin/activate
pytest tests/ -v

# 前端构建检查
cd frontend
npx tsc --noEmit
npm run build
```

### 测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| 认证 | 8 | 登录、Token 刷新、当前用户、权限校验 |
| 健康检查 | 2 | 健康状态、版本信息 |
| 集成（端到端） | 24 | 完整业务流程：商品→客户→订单→库存→收款→报表 |

## API 概览

| 模块 | 路径前缀 | 说明 |
|---|---|---|
| 认证 | `/api/v1/auth` | 登录、刷新、退出、当前用户 |
| 用户 | `/api/v1/users` | 用户列表 |
| 商品 | `/api/v1/products` | 商品 CRUD + 停用 + 价格历史 |
| 文件 | `/api/v1/files` | 图片上传 |
| 客户 | `/api/v1/customers` | 客户 CRUD + 归属转移 |
| 订单 | `/api/v1/sales-orders` | 订单 CRUD + 确认/取消 |
| 收款 | `/api/v1/payments` | 收款登记 + 冲正 |
| 库存 | `/api/v1/inventory` | 库存流水 + 手工调整 |
| 报表 | `/api/v1/reports` | 销售汇总、趋势、排行、库存预警 |

## 环境变量

参见 `.env.example`，关键变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | 数据库连接 | `postgresql+psycopg://postgres:postgres@localhost:5432/sales_management` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `change-me` |
| `UPLOAD_DIR` | 上传文件目录 | `uploads` |
| `MAX_IMAGE_SIZE_MB` | 图片大小限制(MB) | `5` |

## License

MIT
