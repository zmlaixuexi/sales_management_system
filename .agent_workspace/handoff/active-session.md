# 当前工作现场

最后更新时间：2026-04-30
当前阶段：阶段 6 交付加固
当前任务编号：DEVOPS-PROD-001 / DEVOPS-NGINX-001 / DEVOPS-BACKUP-001
当前任务名称：生产部署配置
当前 Agent：Claude
任务状态：已完成

## 本次目标

创建生产 Docker Compose、Nginx 配置和备份恢复脚本。

## 最近完成

- deploy/docker-compose.prod.yml：四容器架构（PG + 后端 + 前端构建 + Nginx）
- deploy/nginx.conf：SPA 路由、API 代理、静态资源缓存
- deploy/backup.sh / restore.sh：PostgreSQL 备份恢复脚本
- frontend/Dockerfile：多阶段生产构建

## 当前正在做

生产部署配置已完成。阶段 6 仅剩 DOC-WINDOWS-001。

## 下一步第一动作

1. DOC-WINDOWS-001：Windows 启动文档
2. P1 扩展：测试补强、导出审计日志、异常路径

## 未完成事项

- Windows 启动文档（可选）

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1. passlib 与 bcrypt 5.x 不兼容 → 使用 bcrypt 直接调用。
2. JWT 存储用户 ID 是 string → 查询时需 uuid.UUID(user_id) 转换。
3. Alembic env.py 必须导入所有模型 → 否则自动生成空迁移。
4. 库存扣减必须使用 with_for_update() 行锁 → 否则并发超卖。
5. Ant Design 组件 import 必须使用实际用到的组件 → 否则构建失败。
6. 测试文件中 app.dependency_overrides[get_db] 必须在 setup_module 中设置、teardown_module 中恢复。
7. log_action 调用后如果抛异常，必须先 commit 审计日志再抛异常。
8. 测试业务流程的用户必须是 is_superuser=True，否则新权限校验会拦截请求。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已确认下一步第一动作
