# 部署指南

本文档涵盖开发环境和生产环境的部署方式。

## 环境要求

- Docker 24+ / Docker Compose V2
- Node.js 24+（本地开发）
- Python 3.13+（本地开发）
- PostgreSQL 17（Docker 环境自动提供）

## 快速开始

```bash
cp .env.example .env         # 复制环境变量模板
make dev                     # 启动 Docker 开发环境
```

首次启动后初始化数据库：

```bash
make db-migrate              # 运行数据库迁移
make db-seed                 # 初始化种子数据（管理员账号等）
```

访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000/api/docs
- 默认管理员：admin / admin123

## 本地开发（不用 Docker）

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

数据库需要 PostgreSQL 运行在 localhost:5432，或修改 `.env` 中的 `DATABASE_URL`。

## 开发工作流常用命令

```bash
make test-unit           # 快速运行非集成测试（~15s）
make test-integration    # 仅运行集成测试（~2s）
make test                # 运行全部测试
make quality             # lint + typecheck + test
make ci                  # 完整质量门禁（lint + typecheck + coverage + build）
```

## 生产部署

### 1. 配置环境变量

```bash
cp .env.example .env
```

必须修改的变量：

```bash
POSTGRES_PASSWORD=<强密码>
JWT_SECRET_KEY=<随机密钥，至少 32 字符>
CORS_ORIGINS=https://your-domain.com
```

### 2. 启动服务

```bash
make docker-up
```

生产环境包含 4 个容器：
- **postgres**：PostgreSQL 17 数据库
- **backend**：FastAPI 后端（自动执行数据库迁移）
- **frontend-build**：前端构建（输出到 Nginx）
- **nginx**：反向代理 + 静态文件服务

### 3. 初始化数据

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.db.seed
```

### 4. 停止服务

```bash
make docker-down
```

## 环境变量说明

### 基础配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| APP_ENV | development | 应用环境（development / production） |
| BACKEND_PORT | 8000 | 后端服务端口 |
| FRONTEND_PORT | 5173 | 前端开发服务端口（仅 Docker 开发环境） |
| HTTP_PORT | 80 | 生产环境 Nginx 端口 |
| UVICORN_WORKERS | 2 | Uvicorn Worker 数量（仅生产环境） |

### 数据库

| 变量 | 默认值 | 说明 |
|---|---|---|
| DATABASE_URL | — | PostgreSQL 连接字符串（同步驱动） |
| DATABASE_ASYNC_URL | — | PostgreSQL 连接字符串（异步驱动） |
| POSTGRES_USER | postgres | PostgreSQL 用户名（Docker 环境使用） |
| POSTGRES_PASSWORD | — | PostgreSQL 密码（**Docker 环境必须设置**） |
| POSTGRES_DB | sales_mgmt | PostgreSQL 数据库名（Docker 环境使用） |
| DB_POOL_SIZE | 5 | 连接池大小（生产建议 10） |
| DB_MAX_OVERFLOW | 10 | 连接池最大溢出（生产建议 20） |
| DB_POOL_RECYCLE_SECONDS | 1800 | 连接回收时间（秒） |

### JWT 认证

| 变量 | 默认值 | 说明 |
|---|---|---|
| JWT_SECRET_KEY | change-me | JWT 签名密钥（**生产必须修改**） |
| JWT_ALGORITHM | HS256 | JWT 签名算法 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Access Token 有效期（分钟） |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | 7 | Refresh Token 有效期（天） |

### CORS 与日志

| 变量 | 默认值 | 说明 |
|---|---|---|
| CORS_ORIGINS | http://localhost:5173 | 允许的前端地址（多个用逗号分隔） |
| LOG_LEVEL | INFO | 日志级别（生产建议 WARNING） |
| LOG_FORMAT | text | 日志格式（生产建议 json） |

### 文件上传

| 变量 | 默认值 | 说明 |
|---|---|---|
| UPLOAD_STORAGE_TYPE | local | 存储类型 |
| UPLOAD_DIR | uploads | 上传目录 |
| UPLOAD_PUBLIC_BASE_URL | /uploads | 上传文件访问路径 |
| MAX_IMAGE_SIZE_MB | 5 | 图片上传大小限制（MB） |
| MAX_CSV_IMPORT_SIZE_MB | 10 | CSV 导入文件大小限制（MB） |
| MAX_CSV_IMPORT_ROWS | 1000 | CSV 导入行数上限 |

### 业务与安全

| 变量 | 默认值 | 说明 |
|---|---|---|
| INVENTORY_WARNING_THRESHOLD | 10 | 库存预警阈值 |
| RATE_LIMIT_MAX | 1000 | API 速率限制（每窗口请求数） |
| RATE_LIMIT_WINDOW | 60 | 速率限制窗口（秒） |
| MAX_JSON_BODY_MB | 1 | JSON 请求体大小上限（MB，文件上传有独立限制） |

### 可观测性

| 变量 | 默认值 | 说明 |
|---|---|---|
| SLOW_REQUEST_THRESHOLD_MS | 1000 | 慢请求阈值（毫秒） |
| SLOW_SQL_THRESHOLD_MS | 200 | 慢 SQL 阈值（毫秒，负值禁用） |

## Nginx 配置

生产环境 Nginx 配置（`deploy/nginx.conf`）：

- 前端 SPA 路由支持（try_files fallback）
- API 请求代理到后端（`/api/` → `http://backend`）
- 上传文件代理到后端（`/uploads/` → `http://backend`）
- 健康检查代理（`/health` → `/api/v1/health`）
- 静态资源 7 天缓存（js/css/图片/字体等）
- Gzip 压缩
- 安全响应头（CSP、X-Frame-Options、X-Content-Type-Options 等）
- 隐藏文件拒绝访问（`.env`、`.git` 等）
- 请求体大小限制 20MB（`client_max_body_size`，为后端 `MAX_IMAGE_SIZE_MB`/`MAX_CSV_IMPORT_SIZE_MB` 的上限）

## 数据持久化

Docker Compose 使用命名卷持久化数据：

| 卷名 | 挂载点 | 用途 |
|---|---|---|
| postgres_data | /var/lib/postgresql/data | 数据库数据 |
| uploads_data | /app/uploads | 上传文件 |

删除容器不会丢失数据，但 `docker compose down -v` 会删除卷。

## 数据库备份与恢复

```bash
# 备份
bash deploy/backup.sh

# 恢复
bash deploy/restore.sh backup_file.sql.gz
```

备份脚本支持 Docker 和本地两种环境，自动压缩，保留 7 天每日备份 + 4 周每周备份。

## 常用运维命令

```bash
# 查看服务状态
docker compose -f deploy/docker-compose.prod.yml ps

# 查看后端日志
docker compose -f deploy/docker-compose.prod.yml logs -f backend

# 重新构建并启动
docker compose -f deploy/docker-compose.prod.yml up --build -d

# 执行数据库迁移
docker compose -f deploy/docker-compose.prod.yml exec backend alembic upgrade head
```

## 部署前检查

部署前运行自动化检查脚本，验证文件完整性、环境变量、Docker 状态、代码质量和前端构建：

```bash
bash deploy/pre-deploy-check.sh

# 跳过测试和构建（加速检查）
bash deploy/pre-deploy-check.sh --skip-tests --skip-build
```

检查项目包括：文件完整性、环境变量配置、Docker 可用性、ruff/mypy 代码检查、后端测试、前端构建、数据库迁移一致性、端口可用性、磁盘空间。

## 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 运行部署前检查
bash deploy/pre-deploy-check.sh

# 3. 重建并重启容器
docker compose -f deploy/docker-compose.prod.yml up --build -d
```

## 回滚

```bash
# 回滚到指定 Git 版本（自动备份数据库 + 重建容器）
bash deploy/rollback.sh <git-commit-or-tag>

# 示例
bash deploy/rollback.sh v1.0.0
bash deploy/rollback.sh abc1234
```

回滚流程：
1. 自动备份当前数据库
2. 回退代码到指定版本
3. 重建并重启 Docker 容器
4. 等待后端健康检查就绪

数据库需手动回滚（如需要）：

```bash
bash deploy/restore.sh backups/sales_mgmt_*.sql.gz
```

## HTTPS 配置

`deploy/nginx.conf` 包含注释掉的 HTTPS 配置模板。启用步骤：

1. 获取 TLS 证书（推荐 Let's Encrypt）
2. 取消 `deploy/nginx.conf` 中 HTTPS server 块的注释
3. 填入证书路径
4. 重启 Nginx 容器

## 健康检查

- `GET /api/v1/health`：返回服务健康状态
  - `{"status": "ok"}`：正常
  - `{"status": "degraded"}`：数据库不可用
- 生产环境 Docker 自动执行健康检查（每 15 秒）
