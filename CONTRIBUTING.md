# 贡献指南

## 开发环境

```bash
# 1. 克隆仓库
git clone <repo-url> && cd sales_management_system

# 2. 复制环境变量
cp .env.example .env

# 3. 启动 PostgreSQL（Docker）
cd deploy && docker compose -f docker-compose.dev.yml up -d postgres

# 4. 后端
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000

# 5. 前端
cd ../frontend
npm install
npm run dev
```

## 代码规范

### 后端（Python）

- 格式化和 lint：`ruff check backend/`（零 error 要求）
- 测试：`pytest backend/tests/ -v`
- 注释和用户可见文案使用中文
- 提交信息使用中文，格式：`类型：简短说明`

### 前端（TypeScript/React）

- 类型检查：`npx tsc --noEmit`（零 error 要求）
- Lint：`npx eslint src/`（零 warning 要求）
- 测试：`npx vitest run`
- 组件使用函数式组件 + Hooks

### 通用

- 提交前运行 `make build` 确保全量通过
- 金额、权限、订单状态、库存相关逻辑以后端为准
- 不要提交 `.env` 文件或包含真实密钥的配置

## 运行全部检查

```bash
make build   # lint + test + build 一键验证
```

## 测试

- 后端测试位于 `backend/tests/`，每个 API 模块有独立测试文件
- 前端测试位于 `frontend/src/__tests__/`
- 新增业务接口必须补充对应测试

## 数据库迁移

修改模型后：

```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```
