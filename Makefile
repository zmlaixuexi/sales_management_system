.PHONY: help dev dev-backend dev-frontend install test test-unit test-integration test-backend test-frontend coverage coverage-frontend lint lint-fix lint-backend lint-frontend typecheck typecheck-backend quality ci build build-frontend db-migrate db-check db-seed db-backup db-restore docker-up docker-down deploy-check deploy-rollback clean

# 后端 Python：优先使用 venv，回退到系统 python
PYTHON ?= $(shell [ -f backend/.venv/bin/python ] && echo ".venv/bin/python" || echo "python")

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
	cd backend && pip install ".[dev]"
	cd frontend && npm install

# ─── 测试 ─────────────────────────────────────────────────

test-backend: ## 运行后端测试
	cd backend && $(PYTHON) -m pytest tests/ -v

test-frontend: ## 运行前端测试
	cd frontend && npx vitest run

test: test-backend test-frontend ## 运行全部测试

test-unit: ## 快速运行非集成测试（排除 integration 标记）
	cd backend && $(PYTHON) -m pytest tests/ -v -m "not integration"

test-integration: ## 仅运行集成测试
	cd backend && $(PYTHON) -m pytest tests/ -v -m integration

coverage: ## 后端测试覆盖率报告
	cd backend && $(PYTHON) -m pytest tests/ --cov --cov-report=term-missing -q

coverage-frontend: ## 前端测试覆盖率报告
	cd frontend && npx vitest run --coverage

# ─── 代码质量 ──────────────────────────────────────────────

lint-backend: ## 后端 lint 检查
	cd backend && ruff check .

lint-frontend: ## 前端 lint 检查
	cd frontend && npx eslint src/ --max-warnings=0

lint: lint-backend lint-frontend ## 全部 lint 检查

lint-fix: ## 自动修复 lint 问题
	cd backend && ruff check --fix .
	cd frontend && npx eslint src/ --fix

typecheck: typecheck-backend typecheck-frontend ## 全部类型检查（mypy + tsc）

typecheck-backend: ## 后端 mypy 静态类型检查
	cd backend && $(PYTHON) -m mypy app/

typecheck-frontend: ## 前端 TypeScript 类型检查
	cd frontend && npx tsc --noEmit

quality: lint typecheck test ## 全部质量检查（lint + typecheck + test）

ci: lint-backend lint-frontend typecheck coverage coverage-frontend build-frontend ## 本地 CI：完整质量门禁（lint + typecheck + coverage + build）

# ─── 构建 ─────────────────────────────────────────────────

build-frontend: ## 构建前端生产包
	cd frontend && npm run build

build: lint test build-frontend ## 完整构建（lint + test + build）

# ─── 数据库 ────────────────────────────────────────────────

db-migrate: ## 运行数据库迁移
	cd backend && alembic upgrade head

db-check: ## 检查模型与迁移是否同步
	cd backend && alembic upgrade head && alembic check

db-seed: ## 初始化种子数据
	cd backend && $(PYTHON) -m app.db.seed

db-backup: ## 备份数据库（PostgreSQL）
	bash deploy/backup.sh

db-restore: ## 恢复数据库（参数：BACKUP_FILE=backups/xxx.sql.gz）
	bash deploy/restore.sh $${BACKUP_FILE:-}

# ─── Docker ────────────────────────────────────────────────

docker-up: ## 启动生产 Docker 环境
	docker compose -f deploy/docker-compose.prod.yml up --build -d

docker-down: ## 停止 Docker 环境
	docker compose -f deploy/docker-compose.prod.yml down

# ─── 部署 ──────────────────────────────────────────────────

deploy-check: ## 部署前检查（文件/环境/Docker/代码质量/构建/迁移）
	bash deploy/pre-deploy-check.sh

deploy-rollback: ## 回滚到指定版本（参数：TARGET=v1.0.0）
	bash deploy/rollback.sh $${TARGET:-HEAD~1}

# ─── 清理 ─────────────────────────────────────────────────

clean: ## 清理生成文件
	find backend -name '*.pyc' -delete
	find backend -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache
	rm -rf frontend/dist
