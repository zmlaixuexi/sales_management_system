.PHONY: help dev dev-backend dev-frontend install test test-backend test-frontend coverage lint lint-backend lint-frontend typecheck quality build build-frontend db-migrate db-seed db-backup db-restore docker-up docker-down clean

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── 开发 ─────────────────────────────────────────────────

dev-backend: ## 启动后端开发服务器（需要 .env）
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## 启动前端开发服务器
	cd frontend && npm run dev

dev: ## 启动 Docker 开发环境
	docker compose -f deploy/docker-compose.dev.yml up --build

# ─── 安装 ─────────────────────────────────────────────────

install: ## 安装前后端依赖
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# ─── 测试 ─────────────────────────────────────────────────

test-backend: ## 运行后端测试
	cd backend && python -m pytest tests/ -v

test-frontend: ## 运行前端测试
	cd frontend && npx vitest run

test: test-backend test-frontend ## 运行全部测试

coverage: ## 后端测试覆盖率报告
	cd backend && python -m pytest tests/ --cov --cov-report=term-missing -q

# ─── 代码质量 ──────────────────────────────────────────────

lint-backend: ## 后端 lint 检查
	cd backend && ruff check .

lint-frontend: ## 前端 lint 检查
	cd frontend && npx eslint src/ --max-warnings=0

lint: lint-backend lint-frontend ## 全部 lint 检查

typecheck: ## 前端 TypeScript 类型检查
	cd frontend && npx tsc --noEmit

quality: lint typecheck test ## 全部质量检查（lint + typecheck + test）

# ─── 构建 ─────────────────────────────────────────────────

build-frontend: ## 构建前端生产包
	cd frontend && npm run build

build: lint test build-frontend ## 完整构建（lint + test + build）

# ─── 数据库 ────────────────────────────────────────────────

db-migrate: ## 运行数据库迁移
	cd backend && alembic upgrade head

db-seed: ## 初始化种子数据
	cd backend && python -m app.db.seed

db-backup: ## 备份数据库（PostgreSQL）
	bash deploy/backup.sh

db-restore: ## 恢复数据库（参数：BACKUP_FILE=backups/xxx.sql.gz）
	bash deploy/restore.sh $${BACKUP_FILE:-}

# ─── Docker ────────────────────────────────────────────────

docker-up: ## 启动生产 Docker 环境
	docker compose -f deploy/docker-compose.prod.yml up --build -d

docker-down: ## 停止 Docker 环境
	docker compose -f deploy/docker-compose.prod.yml down

# ─── 清理 ─────────────────────────────────────────────────

clean: ## 清理生成文件
	find backend -name '*.pyc' -delete
	find backend -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache
	rm -rf frontend/dist
