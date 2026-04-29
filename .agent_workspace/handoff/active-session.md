# 当前工作现场

最后更新时间：2026-04-30
当前阶段：安全加固 — 数据范围权限
当前任务编号：SEC-002
当前任务名称：数据范围权限和导出过滤
当前 Agent：Claude
任务状态：已完成

## 本次目标

实现客户/订单数据范围权限（销售只能看本人数据），并在导出 CSV 时同样过滤。

## 最近完成

- 客户列表 API：无 `customer:view_all` 权限时只返回 `owner_user_id == current_user.id` 的客户
- 订单列表 API：无 `order:view_all` 权限时只返回 `sales_user_id == current_user.id` 的订单
- 客户导出 CSV：同样应用 `owner_user_id` 过滤
- 订单导出 CSV：同样应用 `sales_user_id` 过滤
- 后端 51/51 测试通过

## 当前正在做

数据范围权限已完成。下一步继续 P0 缺口。

## 下一步第一动作

1. 审计日志补充 IP、user_agent、request_id（AUDIT-REQ-001）
2. 补齐阶段 6 交付物和文档

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| backend/app/api/v1/customers.py | 更新 | 数据范围过滤 |
| backend/app/api/v1/orders.py | 更新 | 数据范围过滤 |
| backend/app/api/v1/exports.py | 更新 | 导出数据范围过滤 |
| backend/app/services/export_service.py | 更新 | 导出函数增加 owner_user_id/sales_user_id 参数 |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| pytest tests/ -v | 51/51 通过 | 无回归 |

## 未完成事项

- 审计日志补充 IP、user_agent、request_id。
- 补齐文档和交付物。

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
- [x] 已阅读实现记录
- [x] 已阅读重复问题记录
- [x] 已确认下一步第一动作
