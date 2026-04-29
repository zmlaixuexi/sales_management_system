# 当前工作现场

最后更新时间：2026-04-30
当前阶段：P1 前端体验 / 扩展功能
当前任务编号：UX-006
当前任务名称：列表页空状态提示和分页大小选项
当前 Agent：Claude
任务状态：已完成

## 最近完成

- 4 个列表页新增上下文感知空状态提示（加载中/筛选无结果/无数据引导）
- 统一 pageSizeOptions: [10, 20, 50, 100]
- 前端 10/10 测试通过，TypeScript 编译通过

## 下一步第一动作

1. 前端测试补强（更多组件测试、API mock）
2. 订单 CSV 批量导入
3. 代码质量：ESLint 规则完善
4. 仪表盘数据可视化增强

## 当前里程碑总结（Round 15-36）

- 后端测试：51 → 116（+65）
- 前端测试：0 → 10（框架搭建完成）
- 安全：RBAC 权限、数据范围过滤、速率限制、敏感字段控制、logout token 清理
- 可观测性：结构化 JSON 日志（LOG_FORMAT）、审计日志请求元数据
- 性能：前端代码拆分（1.4MB → 40+ chunk）、TypeScript strict 模式
- 前端体验：统一错误提示、429 重试、ErrorBoundary、菜单修复、用户名/角色展示、空状态引导
- 功能：商品/客户 CSV 批量导入、4 种数据导出
- 工程化：Vitest + Testing Library 测试框架
- 文档：API 文档、README、.env.example、测试报告全部更新
- 配置：INVENTORY_WARNING_THRESHOLD、LOG_FORMAT、RATE_LIMIT_MAX/WINDOW
- 后端 116/116 通过，前端 10/10 + TypeScript 通过

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
9. logout 必须同时清除 access_token 和 refresh_token。
10. file_service.py 的 MAX_SIZE_BYTES 是模块级变量，修改限制需直接 patch 模块变量而非 settings。
11. 测试速率限制时，test_ratelimit.py 的 429 压力测试必须放在最后，否则耗尽 IP 配额影响后续测试。
12. 批量导入中调用 _generate_sku() 会因未提交而重复 → 必须在导入函数内自维护序号计数器。
13. 批量导入客户手机号需同时检查数据库和批量内去重（used_phones set）。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已确认下一步第一动作
- [x] 已阅读重复问题列表（13 条）
