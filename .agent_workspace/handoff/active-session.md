# 当前工作现场

最后更新时间：2026-04-30
当前阶段：阶段 6 交付加固
当前任务编号：DOC-002 / DOC-003
当前任务名称：API 和数据库文档
当前 Agent：Claude
任务状态：已完成

## 本次目标

创建完整的 API 接口文档和数据库文档。

## 最近完成

- docs/api.md：46 个 API 端点、23 个权限码、错误码、请求/响应格式
- docs/database.md：16 张表、ER 关系、字段说明、种子数据、迁移命令

## 当前正在做

文档已完成。下一步继续阶段 6 交付物。

## 下一步第一动作

1. docs/testing.md（DOC-004）
2. 测试报告（QA-REPORT-001）
3. 生产 Docker Compose 和 Nginx 配置

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| docs/api.md | 新建 | API 接口文档 |
| docs/database.md | 新建 | 数据库文档 |

## 已执行命令

无需运行测试（纯文档任务）。

## 未完成事项

- docs/testing.md
- 阶段测试报告
- 生产部署配置

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
