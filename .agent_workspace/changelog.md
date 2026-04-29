# Changelog

## 2026-04-29

### 阶段 1：工程基础设施

- **BE-001** 初始化 FastAPI 后端工程骨架：创建 app/main.py、api/v1/health.py、core/config.py、core/security.py、core/logging.py、db/session.py、Dockerfile。健康检查测试 2/2 通过，uvicorn 启动验证通过。
- **DB-001** 配置 Alembic 迁移环境：创建 alembic.ini、alembic/env.py、alembic/script.py.mako。
- **FE-001** 初始化 React + TypeScript + Vite 前端工程：创建 frontend/ 目录，安装依赖，构建验证通过。
- **DEVOPS-001** 创建 Docker Compose 开发环境：创建 deploy/docker-compose.dev.yml（postgres、backend、frontend 服务）、.env.example、.env、.editorconfig，更新 .gitignore。

### 阶段 0：需求与架构冻结

- 创建销售管理系统开发执行文档。
- 补充商品图片上传、存储、极简商品录入、自动排序、利润和折扣规则。
- 补充实现记录、中断恢复协议、问题台账和重复问题台账。
- 创建 `.agent_workspace/` 协作入口模板。
