# 当前工作现场

最后更新时间：2026-04-30
当前阶段：P1 性能优化
当前任务编号：PERF-001
当前任务名称：前端路由级代码拆分
当前 Agent：Claude
任务状态：已完成

## 最近完成

- 路由配置改为 React.lazy + Suspense 动态导入
- bundle 从单个 1,452KB 拆分为 40+ 个按需加载 chunk
- 页面级模块独立：Dashboard 11KB、Products 4.5KB、Orders 3KB 等
- 加载中显示 Spin 全屏占位
- TypeScript 编译通过，构建成功

## 下一步第一动作

1. 批量导入功能
2. 前端错误边界和 loading 状态统一
3. 前端请求层 429 重试和错误提示

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
