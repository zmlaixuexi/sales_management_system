# 系统架构

本文档描述销售管理系统的整体架构设计。

## 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 后端框架 | FastAPI | Python 3.13 |
| ORM | SQLAlchemy 2.x（Mapped Column 风格） | — |
| 数据库 | PostgreSQL | 17 |
| 数据库迁移 | Alembic | — |
| 认证 | JWT（python-jose + bcrypt） | — |
| 前端框架 | React + TypeScript | React 19 |
| UI 组件库 | Ant Design | — |
| 状态管理 | Zustand | — |
| HTTP 客户端 | Axios | — |
| 构建工具 | Vite | — |
| 路由 | react-router-dom v7 | — |
| 容器化 | Docker + Docker Compose V2 | — |
| 反向代理 | Nginx | — |

## 系统架构概览

```
┌─────────────┐
│   浏览器     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     /api/*     ┌──────────────────┐
│    Nginx     │ ──────────────▶│   FastAPI 后端    │
│  (生产环境)  │                │   (uvicorn)       │
│  静态文件    │     /uploads   │                    │
│  反向代理    │ ──────────────▶│   中间件栈：        │
└─────────────┘                │   CORS             │
                               │   安全头            │
                               │   请求日志          │
                               │   速率限制          │
                               └────────┬───────────┘
                                        │
                                        ▼
                                ┌──────────────────┐
                                │   PostgreSQL 17   │
                                └──────────────────┘
```

开发环境中前端通过 Vite Dev Server 直接访问后端，不经过 Nginx。

## 后端架构

### 目录结构

```
backend/
  app/
    main.py              # 应用入口、中间件注册、路由挂载
    api/
      deps.py            # 依赖注入（get_db, get_current_user, require_permission）
      v1/
        router.py        # 路由聚合
        auth.py          # 认证端点
        users.py         # 用户管理
        products.py      # 产品管理
        customers.py     # 客户管理
        orders.py        # 订单管理
        payments.py      # 收款管理
        inventory.py     # 库存管理
        reports.py       # 报表统计
        exports.py       # CSV 导出
        files.py         # 文件上传
        audit_logs.py    # 审计日志
        health.py        # 健康检查
    core/
      config.py          # 配置（pydantic BaseSettings）
      security.py        # 密码哈希、JWT 生成
      security_headers.py # 安全响应头中间件
      request_log.py     # 请求日志中间件
      ratelimit.py       # 速率限制中间件
      logging.py         # 结构化日志配置
      sanitize.py        # LIKE 注入防护
    db/
      session.py         # 数据库引擎与会话
      seed.py            # 种子数据
    models/              # SQLAlchemy 模型
    schemas/             # Pydantic 请求/响应模型
    services/            # 业务逻辑服务
      audit_service.py   # 审计日志记录
      export_service.py  # CSV 导出生成
      file_service.py    # 文件上传校验
      payment_service.py # 收款登记（含行锁防并发）
      csv_import.py      # CSV 导入文件校验
  alembic/               # 数据库迁移
  tests/                 # 测试
```

### 中间件栈

请求经过以下中间件（注册顺序，实际执行为反向）：

1. **CORSMiddleware** — 跨域请求处理
2. **SecurityHeadersMiddleware** — 添加 X-Content-Type-Options、X-Frame-Options、CSP 等安全头
3. **RequestIDMiddleware** — 生成/透传 X-Request-ID，关联日志和审计
4. **RequestLogMiddleware** — 记录 /api/ 请求的方法、路径、状态码、耗时、X-Response-Time
5. **RateLimitMiddleware** — 基于 IP 的滑动窗口速率限制

### API 路由

所有 API 端点以 `/api/v1` 为前缀，共 11 个功能模块：

| 模块 | 路径前缀 | 说明 |
|---|---|---|
| 认证 | `/auth` | 登录、刷新令牌、获取当前用户 |
| 用户 | `/users` | 用户 CRUD（管理员） |
| 产品 | `/products` | 产品 CRUD、导入、价格历史 |
| 客户 | `/customers` | 客户 CRUD、导入、转移 |
| 订单 | `/sales-orders` | 订单 CRUD、确认、取消 |
| 收款 | `/payments` | 收款登记、冲销 |
| 库存 | `/inventory` | 库存变动查询、手动调整 |
| 报表 | `/reports` | 销售汇总、趋势、排名、库存预警 |
| 导出 | `/exports` | CSV 流式导出 |
| 文件 | `/files` | 图片上传 |
| 审计 | `/audit-logs` | 操作日志查询 |

### 数据模型

系统包含 16 张数据库表，全部使用 UUID 主键：

- **用户域**：`users`、`roles`、`permissions`、`user_roles`、`role_permissions`
- **产品域**：`products`、`product_categories`、`files`、`product_images`、`product_price_history`
- **客户域**：`customers`
- **订单域**：`sales_orders`、`sales_order_items`、`payments`、`inventory_movements`
- **审计域**：`audit_logs`

### 数据库迁移

使用 Alembic 管理，共 4 个迁移版本：

1. 初始化用户、权限、产品相关表
2. 新增客户表
3. 新增订单、订单项、库存变动、收款表
4. 新增审计日志表

## 前端架构

### 目录结构

```
frontend/src/
  main.tsx              # 应用入口
  routes/
    index.tsx           # 路由定义（懒加载）
    AppLayout.tsx       # 侧边栏 + 头部布局
    ProtectedRoute.tsx  # 认证守卫
  pages/                # 页面组件
  components/           # 通用组件
  api/
    client.ts           # Axios 实例与拦截器
    request.ts          # 通用请求封装
    auth.ts             # 认证 API
    products.ts         # 产品 API
    customers.ts        # 客户 API
    orders.ts           # 订单 API
    payments.ts         # 收款 API
    reports.ts          # 报表 API
    auditLogs.ts        # 审计 API
  stores/
    auth.ts             # 认证状态（Zustand）
  types/
    index.ts            # 共享类型定义
  utils/
    index.ts            # 工具函数
```

### 路由设计

所有页面采用 `React.lazy()` 懒加载，由 `ProtectedRoute` 守卫认证状态：

| 路径 | 页面 | 说明 |
|---|---|---|
| `/login` | Login | 登录 |
| `/` | Dashboard | 首页仪表盘 |
| `/products` | Products | 产品列表 |
| `/products/new` | ProductForm | 新增产品 |
| `/products/:id/edit` | ProductForm | 编辑产品 |
| `/customers` | Customers | 客户列表 |
| `/customers/new` | CustomerForm | 新增客户 |
| `/customers/:id/edit` | CustomerForm | 编辑客户 |
| `/orders` | Orders | 订单列表 |
| `/orders/new` | OrderForm | 新增订单 |
| `/orders/:id` | OrderDetail | 订单详情 |
| `/orders/:id/edit` | OrderForm | 编辑订单 |
| `/audit-logs` | AuditLogs | 审计日志 |

### API 客户端

- 基于 Axios 封装，`baseURL` 从 `VITE_API_BASE_URL` 环境变量读取
- 请求拦截器自动附加 Bearer Token
- 响应拦截器处理：401 自动刷新令牌并重试、429 退避重试、错误消息提示
- 代码分割：vendor-react 和 vendor-antd 独立 chunk

## 认证与授权

### 认证流程

1. 用户通过 `/auth/login` 提交用户名和密码
2. 后端验证后返回 `access_token`（默认 30 分钟）和 `refresh_token`（默认 7 天）
3. 前端将令牌存储在 localStorage，通过 Axios 拦截器自动附加到请求头
4. 令牌过期时自动使用 refresh_token 刷新

### RBAC 权限模型

```
用户 ──(多对多)── 角色 ──(多对多)── 权限
```

权限码格式为 `模块:操作`（如 `product:list`、`order:confirm`）。超级用户自动通过所有权限检查。

系统预置 6 个角色：

| 角色 | 权限范围 |
|---|---|
| admin | 全部 29 个权限 |
| sales_manager | 产品查看 + 客户/订单全权限（含 view_all）+ 收款查看 + 报表 + 库存查看 |
| sales | 产品查看 + 客户/订单基本操作 + 收款查看 |
| inventory | 产品管理 + 库存管理 + 订单查看 |
| finance | 产品查看（含成本价）+ 订单全查看 + 收款全操作 + 报表 |
| audit | 仅审计日志查看 |

### 数据范围控制

销售人员默认只能查看自己的客户和订单。拥有 `customer:view_all` 或 `order:view_all` 权限的角色可以查看全部数据。

## 核心业务逻辑

### 订单状态机

```
draft ──确认──▶ confirmed ──部分收款──▶ partially_paid ──全额收款──▶ completed
  │                │                       │
  └──取消──▶ cancelled ◀──────────────────┘
```

状态转换规则在 `VALID_TRANSITIONS` 字典中定义，后端严格校验。

### 库存联动

- 确认订单时原子扣减库存（行级锁 `with_for_update()`），并创建库存变动记录
- 取消已确认/部分收款订单时自动回补库存
- 手动库存调整同样创建变动记录

### 收款并发保护

- 收款登记使用 `with_for_update()` 行锁查询订单，防止并发收款导致超额
- 收款冲正同样使用行锁，确保状态回退原子性

### 订单快照

`SalesOrderItem` 在创建时捕获产品的 SKU、名称、图片、成本价，确保历史订单数据不受后续产品变更影响。

### 审计追踪

所有变更操作通过 `log_action()` 记录：操作人、动作类型、变更前后数据（敏感字段掩码）、IP 地址、User-Agent。

### CSV 导出

使用 Python 生成器 + `yield_per(500)` 实现流式 CSV 导出，支持 UTF-8 BOM 以兼容 Excel。

## 部署架构

### 生产环境

Docker Compose 启动 4 个容器：

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  nginx   │────▶│ backend  │────▶│ postgres │
│  :80     │     │ :8000    │     │ :5432    │
└──────────┘     └──────────┘     └──────────┘
     ▲
     │          ┌──────────────┐
     └──────────│frontend-build│ (构建阶段)
                └──────────────┘
```

- **postgres**：PostgreSQL 17，数据持久化到 Docker Volume
- **backend**：FastAPI 应用，启动前自动执行 `alembic upgrade head`
- **frontend-build**：多阶段构建，产出静态文件由 Nginx 服务
- **nginx**：反向代理 + 静态文件服务 + 安全头 + SPA 路由 fallback + 静态资源 7 天缓存

### 开发环境

Docker Compose 启动 3 个容器（无 Nginx）：

- **postgres**：PostgreSQL 17
- **backend**：代码卷挂载，uvicorn `--reload` 热重载
- **frontend**：Vite Dev Server，支持 HMR

## 安全措施

| 措施 | 实现方式 |
|---|---|
| 认证 | JWT Bearer Token |
| 授权 | RBAC 权限模型 + 数据范围隔离 |
| 密码存储 | bcrypt 哈希 + 强度校验（必须含字母和数字） |
| SQL 注入防护 | SQLAlchemy ORM + `escape_like()` |
| XSS 防护 | 安全响应头（CSP、X-XSS-Protection）+ 输入消毒 strip_html |
| 点击劫持防护 | X-Frame-Options: DENY |
| 速率限制 | 基于 IP 的滑动窗口 |
| 敏感数据 | 审计日志密码/令牌字段掩码 + 成本价按权限过滤 |
| 软删除 | `deleted_at` 时间戳，非物理删除 |
| 输入验证 | Pydantic Schema 约束 + Literal 枚举 |
| 并发防护 | 收款登记/冲正 `with_for_update()` 行锁 |
| 文件上传 | 扩展名 + MIME + 魔数字节 + 大小限制 |
| CSV 导入 | 大小限制 + UTF-8 编码校验 + 逐行错误收集 |
| CORS | 白名单（非通配符） |
| 排序注入 | `sort_by` 白名单校验 |
| 成本价保护 | 低于成本价阻止下单 |
| 报表参数 | period 严格校验，无效值返回 400 |

## 可观测性

- **健康检查**：`GET /api/v1/health` 探测数据库连接，返回 `ok` 或 `degraded`
- **请求 ID**：`X-Request-ID` 自动生成/透传，关联请求日志和审计日志
- **请求日志**：记录所有 `/api/` 请求的方法、路径、状态码、耗时、客户端 IP
- **响应耗时**：`X-Response-Time` 响应头
- **结构化日志**：生产环境 JSON 格式，支持慢请求警告（可配置阈值）
- **审计日志**：完整记录所有数据变更操作，含请求元数据
- **全局异常处理**：未处理异常返回一致 JSON，防泄露内部详情
