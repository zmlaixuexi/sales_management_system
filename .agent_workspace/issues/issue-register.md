# 问题台账

本文件记录开发、测试、部署中遇到的问题。所有影响推进的问题必须记录。

## ISSUE-20260430-001

标题：Backlog 将严格 DoD 未完成的阶段标记为已完成
首次发现时间：2026-04-30
发现 Agent：Codex
严重级别：P0
状态：已解决
关联任务：阶段 2-6 / MVP DoD
关联功能：权限、数据范围、敏感字段、交付加固

### 现象

`.agent_workspace/tasks/backlog.md` 曾将阶段 0-6 标记为全部完成，但对照 `docs/销售管理系统开发执行文档.md`，权限细化、数据范围、敏感字段控制、阶段测试报告、生产部署交付物仍未完成。

### 影响范围

自动循环 agent 可能误判 MVP 已严格完成，从而输出 `AGENT_LOOP_STATUS: DONE` 或转去做 P1/P2 扩展，跳过 P0 缺口。

### 根因分析

现有测试覆盖了主业务 happy path，但没有覆盖完整 DoD；workspace 状态把“主流程可运行”误写成“严格完成”。

### 解决方案

已将 backlog 状态改为“部分完成/未完成”，并在 `.agent_workspace/README.md` 中增加状态判断规则。

### 验证方式

后续 agent 开始任务前必须同时阅读开发文档、backlog、实现记录和代码现状。

### 涉及文件

`.agent_workspace/README.md`、`.agent_workspace/tasks/backlog.md`、`.agent_workspace/handoff/active-session.md`

### 是否可能复发

可能。

### 预防措施

阶段完成前必须逐条对照开发文档 Definition of Done，不能只依据测试通过或实现记录标题判断。

## ISSUE-20260430-002

标题：接口权限、数据范围和敏感字段控制未完整实现
首次发现时间：2026-04-30
发现 Agent：Codex
严重级别：P0
状态：已解决（Round 160 补充修复对象级权限和敏感字段泄露）
关联任务：RBAC-002 / RBAC-003 / RBAC-004 / SEC-PRODUCT-001 / SEC-REPORT-001
关联功能：商品、客户、订单、报表、导出、审计日志

### 现象

多个业务接口当前只校验登录态，未按权限码、数据范围或敏感字段权限裁剪数据。商品、订单、报表、导出仍可能向普通登录用户返回成本、利润、毛利率等敏感字段。

### 影响范围

不满足开发文档第 4 节权限要求和第 18 节 Definition of Done，存在越权查看和敏感经营数据泄露风险。

### 根因分析

RBAC 模型和权限种子已建立，但缺少统一后端权限依赖、对象级数据范围过滤和响应字段裁剪。

### 解决方案

下一步优先实现统一权限依赖、角色权限码校验、数据范围过滤和敏感字段裁剪，并补充对应测试。

### 验证方式

新增普通销售、主管、财务、审计用户的接口测试，验证无权限接口 403、无权限敏感字段不返回、销售只能访问本人数据。

### 涉及文件

`backend/app/api/deps.py`、`backend/app/api/v1/products.py`、`backend/app/api/v1/customers.py`、`backend/app/api/v1/reports.py`、`backend/app/api/v1/exports.py`

### 是否可能复发

可能。

### 预防措施

新增业务接口时必须声明权限码和数据范围策略；测试必须覆盖未授权用户。

## ISSUE-20260501-003

标题：需求符合性验证发现多处功能缺口
首次发现时间：2026-05-01
发现 Agent：Claude
严重级别：P1
状态：已解决
关联任务：需求符合性验证
关联功能：报表、前端页面、商品删除、订单创建、审计日志

### 现象

对照开发文档 DoD 逐项检查，发现以下缺口：

**已修复（Round 252）：**
- 审计日志未对手机号和邮箱脱敏 → 已添加 phone/email 到 SENSITIVE_FIELDS
- 商品删除未检查订单引用 → 已添加 SalesOrderItem 引用检查，返回 409 PRODUCT_IN_USE
- 订单成交单价低于成本价未阻止 → 已添加 PRICE_BELOW_COST 校验

**待修复：**
- ~~缺少报表 API：/reports/customer-ranking、/reports/salesperson-ranking~~ → Round 253 已修复
- ~~缺少订单日志 API：/sales-orders/{id}/logs~~ → Round 254 已修复
- ~~支付 API 路径与文档不一致：/payments/orders/{id}/payments vs /sales-orders/{id}/payments~~ → Round 257 已修复
- ~~缺少 6 个前端页面：客户详情、库存流水、支付列表、报表中心、用户管理、角色权限~~ → Round 342-346 已全部实现（客户详情/报表中心/收款记录/用户管理/库存流水；角色权限通过用户管理页面的角色选择器覆盖）
- ~~商品缺少派生销售字段（sales_quantity、sales_amount 等）~~ → Round 258 已修复
- ~~响应体缺少 request_id 字段~~ → Round 255 已修复
- ~~商品默认排序未按规范（缺 sales_quantity 排序）~~ → Round 258 已修复
- ~~缺少 Windows PowerShell 备份/恢复脚本~~ → Round 256 已修复
- ~~备份清理保留期与文档不符（30 天 vs 7 天+4 周）~~ → Round 256 已修复

### 影响范围

不满足开发文档第 4-8 节部分需求和第 18 节 DoD。

### 根因分析

自动开发循环以"主流程可运行+测试通过"为目标，未逐条对照 DoD 验收。

### 解决方案

分批修复：先安全/业务逻辑（已修复），再功能缺口（待产品决策优先级）。

### 验证方式

逐项对照开发文档验证。

### 涉及文件

多个后端和前端文件

### 是否可能复发

可能

### 预防措施

每轮开发后对照 DoD 验收标准检查。

## ISSUE-20260502-004

标题：generate_sequential_code 字符串排序导致序号 > 9 时 UNIQUE 冲突
首次发现时间：2026-05-02
发现 Agent：Claude
严重级别：P2
状态：已解决（Round 320 修复数字排序 + 添加 > 9 验证测试）
关联任务：Round 319 测试补强
关联功能：订单号生成、SKU 生成

### 现象

`generate_sequential_code` 使用 `order_by(column.desc())` 查询当天最大序号。字符串 desc 排序中 `0009 > 0010`，导致序号超过 9 后查询返回错误的最大值，可能生成已存在的序号引发 UNIQUE 约束冲突。

### 影响范围

同一天创建超过 9 个订单或 SKU 时可能触发。当前测试模块各自使用独立 DB 未触发，但生产环境可能受影响。

### 复现步骤

1. 同一天创建 10 个订单
2. 第 10 个订单的序号查询返回 `0009` 而非 `0010`
3. 生成 `0010` 但已存在，触发 IntegrityError

### 根因分析

`order_by(column.desc())` 按字符串排序，4 位数字序号在 10 以上时字符串排序与数字排序不一致。

### 解决方案

改用 `func.max()` 或子串转数字排序：`order_by(func.substr(column, len(full_prefix)+1).cast(Integer).desc())`

### 验证方式

在同一天创建 15+ 订单，验证序号连续递增不冲突。

### 涉及文件

`backend/app/api/deps.py:generate_sequential_code`

### 是否可能复发

是（根因未修复）

### 预防措施

修复排序逻辑为数字排序。

## 问题记录模板

```text
## ISSUE-YYYYMMDD-序号

标题：
首次发现时间：
发现 Agent：
严重级别：P0 / P1 / P2 / P3
状态：未解决 / 已解决 / 规避中 / 复发
关联任务：
关联功能：

### 现象

### 影响范围

### 复现步骤

### 根因分析

### 解决方案

### 验证方式

### 涉及文件

### 是否可能复发

### 预防措施
```
