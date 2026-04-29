# 当前工作现场

最后更新时间：2026-04-30
当前阶段：P1 前端体验
当前任务编号：UX-003
当前任务名称：侧边栏菜单修复
当前 Agent：Claude
任务状态：已完成

## 最近完成

- 修复侧边栏菜单路径 /sales-orders → /orders
- 添加操作日志菜单项
- 移除未实现的系统设置菜单
- 修复子路径高亮（/orders/123 → 高亮 /orders）
- TypeScript 编译通过，前端构建通过，后端 90/90 通过

## 下一步第一动作

1. 批量导入功能
2. 部署文档完善
3. 测试报告更新（测试数从 51 增至 90）

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
