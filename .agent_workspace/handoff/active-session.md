# 当前工作现场

最后更新时间：2026-04-30
当前阶段：阶段 3 已完成，准备进入阶段 4
当前任务编号：FE-PRODUCT-001 / FE-FILE-001 / FE-CUSTOMER-001
当前任务名称：商品和客户管理前端页面
当前 Agent：Claude
任务状态：已完成

## 本次目标

实现阶段 3 前端页面：商品列表/编辑、图片上传、客户列表/编辑。

## 最近完成

- 创建 frontend/src/api/products.ts 和 customers.ts API 调用层。
- 实现商品列表页（Ant Design Table + 搜索/状态筛选/分页 + 图片缩略图 + 利润/毛利率展示 + 停用/删除）。
- 实现商品新增/编辑页（4 必填字段：名称/图片/成本价/销售价 + 折叠高级设置：SKU/库存/状态/排序/备注 + 图片上传交互）。
- 实现客户列表页（搜索/来源筛选/分页 + 等级/跟进状态标签 + 删除）。
- 实现客户新增/编辑页（完整字段表单：名称/联系人/电话/邮箱/来源/等级/跟进状态/备注）。
- 更新路由配置：添加 /products、/products/new、/products/:id/edit、/customers、/customers/new、/customers/:id/edit。
- 前端构建通过，后端测试 10/10 通过。

## 当前正在做

阶段 3 全部完成（后端 + 前端）。准备进入阶段 4：订单、库存、收款。

## 下一步第一动作

从首批 Backlog 中选择阶段 4 的任务开始：
1. `DB-ORDER-001`：创建订单表、订单明细表、库存流水表、收款表的 Alembic 迁移。
2. `BE-ORDER-001`：实现订单创建、编辑草稿、确认、取消 API（含库存扣减/回滚、金额/毛利计算）。
3. `BE-PAYMENT-001`：实现收款登记 API。
4. `FE-ORDER-001`：实现订单列表、创建、详情页。

具体第一动作：在 `backend/app/models/` 创建 `order.py`（SalesOrder/SalesOrderItem/InventoryMovement/Payment 模型），然后生成迁移。

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| frontend/src/api/products.ts | 新建 | 商品 API 调用层 |
| frontend/src/api/customers.ts | 新建 | 客户 API 调用层 |
| frontend/src/pages/Products.tsx | 重写 | 商品列表页 |
| frontend/src/pages/ProductForm.tsx | 新建 | 商品新增/编辑页 |
| frontend/src/pages/Customers.tsx | 重写 | 客户列表页 |
| frontend/src/pages/CustomerForm.tsx | 新建 | 客户新增/编辑页 |
| frontend/src/routes/index.tsx | 已更新 | 添加商品和客户路由 |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| npm run build (frontend) | 通过 | 前端构建成功 |
| pytest tests/ -v | 10/10 通过 | 后端测试 |

## 未完成事项

- 阶段 4 全部任务尚未开始。

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1. passlib 与 bcrypt 5.x 不兼容 → 使用 bcrypt 直接调用。
2. JWT 存储用户 ID 是 string → 查询时需 uuid.UUID(user_id) 转换。
3. Alembic env.py 必须导入所有模型 → 否则自动生成空迁移。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已阅读实现记录
- [x] 已阅读重复问题记录
- [x] 已确认下一步第一动作
