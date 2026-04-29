# Windows 开发环境启动指南

## 方式一：Docker Desktop（推荐）

### 1. 安装 Docker Desktop

下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)，安装后重启电脑。

### 2. 启动项目

打开 PowerShell 或 CMD：

```powershell
# 克隆项目
git clone <仓库地址>
cd sales_management_system

# 复制环境变量
copy .env.example .env

# 启动服务
cd deploy
docker compose -f docker-compose.dev.yml up -d

# 初始化数据库
docker compose -f docker-compose.dev.yml exec backend bash -c "alembic upgrade head && python -m app.db.seed"
```

### 3. 访问

- 前端：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs
- 默认管理员：admin / admin123

### 4. 停止服务

```powershell
docker compose -f docker-compose.dev.yml down
```

---

## 方式二：本地开发（不用 Docker）

### 前置条件

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 20+](https://nodejs.org/)
- [PostgreSQL 17](https://www.postgresql.org/download/windows/)

### 1. 安装 PostgreSQL

安装时记住设置的超级用户密码。安装完成后，创建数据库：

```powershell
psql -U postgres
CREATE DATABASE sales_management;
\q
```

### 2. 后端

```powershell
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（修改 .env 中的 DATABASE_URL）
# DATABASE_URL=postgresql+psycopg://postgres:你的密码@localhost:5432/sales_management

# 数据库迁移和种子数据
alembic upgrade head
python -m app.db.seed

# 启动后端
uvicorn app.main:app --reload --port 8000
```

### 3. 前端

新开一个 PowerShell 窗口：

```powershell
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端：http://localhost:5173
- 后端：http://localhost:8000/docs

---

## 常见问题

### PowerShell 执行策略

如果无法运行脚本，以管理员身份执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### PostgreSQL 连接失败

确认 PostgreSQL 服务正在运行：`services.msc` → 找到 `postgresql-x64-17` → 启动。

确认 `pg_hba.conf` 允许本地连接（默认即可）。

### npm install 很慢

可配置淘宝镜像：

```powershell
npm config set registry https://registry.npmmirror.com
```
