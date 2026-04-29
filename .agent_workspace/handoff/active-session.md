# 当前工作现场

最后更新时间：2026-04-30
当前阶段：阶段 4 后端已完成，前端页面待实现
当前任务编号：DB-ORDER-001 / BE-ORDER-001 / BE-PAYMENT-001
当前任务名称：订单、库存、收款后端 API
当前 Agent：Claude
任务状态：已完成

## 本次目标

实现阶段 4 后端 API：订单创建/确认/取消、库存扣减/回滚、收款登记。

## 最近完成

- 创建 SalesOrder/SalesOrderItem/InventoryMovement/Payment 四个模型和 Alembic 迁移。
- 实现订单 API：创建草稿（含商品快照）、编辑草稿、确认（扣减库存）、取消（回滚库存）。
- 订单状态机：draft → confirmed → partially_paid → completed；draft/confirmed → cancelled。
- 实现收款 API：登记收款（自动更新订单状态到 partially_paid/completed）、冲正收款。
- 实现库存 API：库存流水查询、手工库存调整。
- 库存扣减/回滚使用行锁（with_for_update）保护并发安全。
- 订单明细保存商品快照（名称/SKU/图片/成本价），商品改价不影响历史订单。
- 金额使用 Decimal，折扣金额/折扣率由后端自动计算。
- 完整订单流程实测通过：创建 → 确认 → 收款 → 完成。
- 后端测试 10/10 通过。

## 当前正在做

阶段 4 后端 API 全部完成。前端订单页面（FE-ORDER-001）待下一轮实现。

## 下一步第一动作

实现阶段 4 前端页面：
1. 在 `frontend/src/api/` 创建 orders.ts 和 payments.ts API 调用。
2. 在 `frontend/src/pages/Orders.tsx` 实现订单列表页。
3. 创建 `frontend/src/pages/OrderForm.tsx` 实现订单创建页（选择客户 + 添加商品明细）。
4. 创建 `frontend/src/pages/OrderDetail.tsx` 实现订单详情页（明细/收款/状态操作）。
5. 更新路由配置添加订单页面路由。

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| backend/app/models/order.py | 新建 | 订单、明细、库存流水、收款模型 |
| backend/app/api/v1/orders.py | 新建 | 订单 CRUD + 状态操作 API |
| backend/app/api/v1/payments.py | 新建 | 收款登记和冲正 API |
| backend/app/api/v1/inventory.py | 新建 | 库存流水和调整 API |
| backend/app/api/v1/router.py | 已更新 | 注册新路由 |
| backend/alembic/versions/eb6a1ce2c197_*.py | 新建 | 订单相关表迁移 |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| alembic revision --autogenerate | 通过 | 检测到 4 张新表 |
| alembic upgrade head | 通过 | 16 张表已创建 |
| pytest tests/ -v | 10/10 通过 | |
| curl POST /sales-orders | 通过 | 订单创建成功 |
| curl POST /{id}/confirm | 通过 | 库存扣减正确 |
| curl POST /payments | 通过 | 收款登记成功，订单完成 |

## 未完成事项

- FE-ORDER-001：订单列表、创建、详情前端页面。
- 操作日志记录。
- 权限校验细化。

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1. passlib 与 bcrypt 5.x 不兼容 → 使用 bcrypt 直接调用。
2. JWT 存储用户 ID 是 string → 查询时需 uuid.UUID(user_id) 转换。
3. Alembic env.py 必须导入所有模型 → 否则自动生成空迁移。
4. 库存扣减必须使用 with_for_update() 行锁 → 否则并发超卖。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已阅读实现记录
- [x] 已阅读重复问题记录
- [x] 已确认下一步第一动作
