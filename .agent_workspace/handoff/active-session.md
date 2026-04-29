# 当前工作现场

最后更新时间：2026-04-30
当前阶段：安全加固 — 权限校验
当前任务编号：SEC-001
当前任务名称：统一权限依赖和敏感字段控制
当前 Agent：Claude
任务状态：已完成

## 本次目标

实现统一权限依赖，保护所有业务 API 接口按权限码校验，实现敏感字段（成本价/毛利）过滤。

## 最近完成

- 在 deps.py 添加 `require_permission(permission_code)` 依赖和 `has_permission(user, code)` 辅助函数
- 为全部 8 个业务 API 模块共 25 个端点添加权限校验：
  - products：product:list/create/update/delete + product:view_cost 敏感字段过滤
  - customers：customer:list/create/update/delete
  - orders：order:list/create/update/confirm/cancel
  - payments：payment:list/create/reverse
  - inventory：inventory:list/adjust
  - reports：report:sales
  - audit-logs：audit:view
  - exports：使用对应模块的 list 权限
- 商品列表 API 实现敏感字段过滤：无 product:view_cost 权限时不返回 cost_price/unit_profit/gross_margin
- superuser 自动通过所有权限校验
- 更新测试用户为 is_superuser=True 以保持测试通过
- 后端 51/51 测试通过，前端构建通过

## 当前正在做

权限校验已完成。下一步继续 P0 缺口。

## 下一步第一动作

继续 P0 缺口：
1. 数据范围权限：销售只能看本人客户/订单（需 customer:view_all、order:view_all）
2. 审计日志补充 IP、user_agent、request_id
3. 补齐文档和交付物

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| backend/app/api/deps.py | 更新 | 添加 require_permission 和 has_permission |
| backend/app/api/v1/products.py | 更新 | 权限校验 + 敏感字段过滤 |
| backend/app/api/v1/customers.py | 更新 | 权限校验 |
| backend/app/api/v1/orders.py | 更新 | 权限校验 |
| backend/app/api/v1/payments.py | 更新 | 权限校验 |
| backend/app/api/v1/inventory.py | 更新 | 权限校验 |
| backend/app/api/v1/reports.py | 更新 | 权限校验 |
| backend/app/api/v1/audit_logs.py | 更新 | 权限校验 |
| backend/app/api/v1/exports.py | 更新 | 权限校验 |
| backend/tests/test_integration.py | 更新 | 测试用户改为 superuser |
| backend/tests/test_audit_log.py | 更新 | 测试用户改为 superuser |
| backend/tests/test_export.py | 更新 | 测试用户改为 superuser |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| pytest tests/ -v | 51/51 通过 | 无回归 |
| npm run build | 成功 | 前端构建通过 |

## 未完成事项

- 数据范围权限（销售看本人客户/订单）。
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
