# 当前工作现场

最后更新时间：2026-04-30
当前阶段：MVP 后续扩展
当前任务编号：EXT-002
当前任务名称：数据导出功能
当前 Agent：Claude
任务状态：已完成

## 本次目标

实现 CSV 数据导出功能：后端流式导出服务、4 个导出 API、前端列表页导出按钮。

## 最近完成

- 创建 export_service.py：商品/客户/订单/收款 CSV 流式导出（含 BOM 头，Excel 兼容）
- 创建 exports API（GET /api/v1/exports/products|customers|orders|payments）
- 前端 downloadCsv 工具函数（fetch + blob 触发浏览器下载）
- 商品/客户/订单列表页添加"导出"按钮，携带当前筛选条件
- 后端 34/34 测试通过，前端构建通过

## 当前正在做

数据导出功能已完成。准备提交代码并更新文档。

## 下一步第一动作

从 P1/P2 扩展 Backlog 选择下一个任务：
- 批量导入商品和客户
- 库存预警阈值配置
- 折扣/低毛利审批

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| backend/app/services/export_service.py | 新建 | CSV 流式导出服务 |
| backend/app/api/v1/exports.py | 新建 | 4 个导出 API 端点 |
| backend/app/api/v1/router.py | 更新 | 注册 exports 路由 |
| frontend/src/utils/index.ts | 更新 | 添加 downloadCsv 工具函数 |
| frontend/src/pages/Products.tsx | 更新 | 添加导出按钮 |
| frontend/src/pages/Customers.tsx | 更新 | 添加导出按钮 |
| frontend/src/pages/Orders.tsx | 更新 | 添加导出按钮 |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| pytest tests/ -v | 34/34 通过 | 无回归 |
| npm run build | 成功 | 前端构建通过 |

## 未完成事项

- 权限校验细化（数据范围权限、敏感字段权限）。
- P1/P2 扩展功能（批量导入、库存预警阈值、折扣审批等）。

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1. passlib 与 bcrypt 5.x 不兼容 → 使用 bcrypt 直接调用。
2. JWT 存储用户 ID 是 string → 查询时需 uuid.UUID(user_id) 转换。
3. Alembic env.py 必须导入所有模型 → 否则自动生成空迁移。
4. 库存扣减必须使用 with_for_update() 行锁 → 否则并发超卖。
5. Ant Design 组件 import 必须使用实际用到的组件 → 否则构建失败。
6. 测试文件中 app.dependency_overrides[get_db] 必须在 setup_module 中设置、teardown_module 中恢复 → 否则多个测试文件冲突。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已阅读实现记录
- [x] 已阅读重复问题记录
- [x] 已确认下一步第一动作
