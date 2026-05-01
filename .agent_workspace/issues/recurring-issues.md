# 重复问题台账

同类问题第二次出现时，必须登记到这里。后续 agent 开始相关模块任务前必须先检查本文件。

## RECURRING-20260430-001

问题主题：软删除模型遗漏 deleted_at 过滤
关联 issue：Round 232-234
复发次数：4（payments list, payments reverse, payments export, orders create, orders deduct/restore inventory, reports customer_ranking, products CSV SKU sequence）
最后复发时间：2026-05-02
高风险模块：所有包含 deleted_at 字段的模型（Customer, Product, SalesOrder, User）

### 固定根因

查询未添加 `Model.deleted_at.is_(None)` 条件，导致已软删除的记录仍可通过 API 访问。

### 必须遵守的预防规则

1. 所有查询软删除模型的列表/详情/关联接口，必须添加 `deleted_at.is_(None)` 过滤
2. JOIN 查询两侧都需检查（如 Payment JOIN SalesOrder，两侧都要过滤）
3. 导出服务同样需要过滤（export_payments 等）
4. `get_or_404` 已自动处理，但手动查询需要显式添加

### 开发前检查

- 新增查询时，检查模型是否有 deleted_at 字段
- JOIN 查询时，两侧模型都需要检查

### 禁止做法

- 不经过 get_or_404 的手动 db.query 必须自行添加 deleted_at 过滤

### 关闭条件

所有模型的查询路径均有 deleted_at 过滤保护。

---

## RECURRING-20260430-002

问题主题：外键引用未校验目标记录存在性
关联 issue：Round 237-240
复发次数：4（role_ids, customer_id, owner_user_id, category_id）
最后复发时间：2026-04-30
高风险模块：所有接受 ID 参数并作为外键的创建/编辑接口

### 固定根因

parse_uuid_or_400 只验证 UUID 格式，不验证目标记录是否存在。不存在的 ID 导致数据库 IntegrityError（500）而非友好的 400。

### 必须遵守的预防规则

1. 创建/编辑接口中，每个外键 ID 参数都必须校验目标记录存在
2. 校验应使用 get_or_404 或自定义校验函数（如 _validate_category_id）
3. 对用户、分类等模型需同时检查 is_active 和 deleted_at

### 开发前检查

- 新增接受外键 ID 的接口时，必须添加目标存在性校验

### 禁止做法

- 仅依赖 parse_uuid_or_400 而不验证目标存在

### 关闭条件

所有外键 ID 参数均有存在性校验。

---

## RECURRING-20260430-003

问题主题：对象级权限（所有权检查）遗漏
关联 issue：Round 239
复发次数：1（文件删除）
最后复发时间：2026-04-30
高风险模块：files.py（文件管理）

### 固定根因

delete 端点未检查资源所有者（created_by），任何认证用户可删除他人资源。

### 必须遵守的预防规则

1. 任何涉及资源修改/删除的端点，必须检查资源所有权
2. 使用 check_owner_or_forbid 或直接比较 created_by/current_user.id
3. 超级管理员可绕过所有权检查

### 开发前检查

- 新增修改/删除端点时，检查是否需要所有权验证

### 禁止做法

- 仅依赖 require_permission 而不检查对象所有权

### 关闭条件

所有修改/删除端点均有所有权或权限校验。
