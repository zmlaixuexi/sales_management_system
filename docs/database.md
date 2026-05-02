# 数据库文档

数据库：PostgreSQL（开发/生产）/ SQLite（测试）
ORM：SQLAlchemy 2.x + Alembic 迁移

## ER 关系概览

```
users ──< user_roles >── roles ──< role_permissions >── permissions
  │
  ├──< customers.owner_user_id
  ├──< products.created_by / updated_by
  ├──< sales_orders.sales_user_id
  ├──< inventory_movements.operator_id
  ├──< payments.operator_id
  └──< audit_logs.actor_id (SET NULL)

product_categories ──< products.category_id
  └──< product_categories.parent_id (自引用)

products ──< product_images (CASCADE)
  │         └── files
  ├──< product_price_history
  ├──< sales_order_items.product_id
  └──< inventory_movements.product_id

customers ──< sales_orders.customer_id
          ├── created_by / updated_by → users

sales_orders ──< sales_order_items (CASCADE)
            └──< payments
            └── created_by / updated_by → users
```

## 数据表

### users — 用户

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK, 自动生成 |
| username | String(50) | NO | UNIQUE, 登录名 |
| hashed_password | String(255) | NO | bcrypt 哈希 |
| display_name | String(100) | YES | 显示名 |
| phone | String(30) | YES | 手机号 |
| email | String(100) | YES | 邮箱 |
| is_active | Boolean | NO | 默认 True |
| is_superuser | Boolean | NO | 默认 False |
| created_at | DateTime(tz) | YES | 服务端 now() |
| updated_at | DateTime(tz) | YES | onupdate now() |
| deleted_at | DateTime(tz) | YES | 软删除标记 |

**索引**：username (UNIQUE), deleted_at

### roles — 角色

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| name | String(50) | NO | UNIQUE |
| display_name | String(100) | YES | 显示名 |
| description | String(255) | YES | 说明 |
| created_at | DateTime(tz) | YES | |
| updated_at | DateTime(tz) | YES | |

### permissions — 权限

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| code | String(100) | NO | UNIQUE, 如 product:list |
| name | String(100) | NO | 权限名称 |
| module | String(50) | NO | 所属模块 |
| description | String(255) | YES | 说明 |
| created_at | DateTime(tz) | YES | |

### user_roles — 用户角色关联

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| user_id | UUID | NO | FK → users.id (CASCADE) |
| role_id | UUID | NO | FK → roles.id (CASCADE) |

### role_permissions — 角色权限关联

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| role_id | UUID | NO | FK → roles.id (CASCADE) |
| permission_id | UUID | NO | FK → permissions.id (CASCADE) |

### product_categories — 商品分类

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| name | String(100) | NO | 分类名 |
| parent_id | UUID | YES | FK → product_categories.id (自引用) |
| sort_order | Integer | YES | 默认 0 |
| created_at | DateTime(tz) | YES | |
| updated_at | DateTime(tz) | YES | |

### products — 商品

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| sku | String(64) | NO | UNIQUE, 自动生成 SPU-YYYYMMDD-XXXX |
| name | String(100) | NO | 商品名 |
| main_image_url | Text | YES | 主图 URL |
| category_id | UUID | YES | FK → product_categories.id |
| sale_price | Numeric(12,2) | NO | 销售价 |
| cost_price | Numeric(12,2) | NO | 成本价 |
| stock_quantity | Integer | NO | 库存数量 |
| status | String(20) | NO | active / inactive / disabled |
| sort_weight | Integer | NO | 排序权重 |
| remark | Text | YES | 备注 |
| created_by | UUID | YES | FK → users.id |
| updated_by | UUID | YES | FK → users.id |
| created_at | DateTime(tz) | YES | |
| updated_at | DateTime(tz) | YES | |
| deleted_at | DateTime(tz) | YES | 软删除 |

**索引**：sku (UNIQUE), name, category_id, status

### files — 文件

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| storage_type | String(20) | NO | 默认 local |
| bucket | String(100) | YES | 存储桶 |
| object_key | Text | YES | 对象键 |
| original_name | String(255) | NO | 原始文件名 |
| content_type | String(100) | NO | MIME 类型 |
| size_bytes | Integer | NO | 文件大小 |
| checksum | String(128) | YES | 校验和 |
| public_url | Text | YES | 访问 URL |
| created_by | UUID | YES | FK → users.id |
| created_at | DateTime(tz) | YES | |

### product_images — 商品图片

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| product_id | UUID | NO | FK → products.id (CASCADE) |
| file_id | UUID | NO | FK → files.id |
| is_primary | Boolean | NO | 是否主图 |
| sort_order | Integer | NO | 排序 |

### product_price_history — 价格历史

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| product_id | UUID | NO | FK → products.id |
| old_sale_price | Numeric(12,2) | YES | |
| new_sale_price | Numeric(12,2) | YES | |
| old_cost_price | Numeric(12,2) | YES | |
| new_cost_price | Numeric(12,2) | YES | |
| changed_by | UUID | YES | FK → users.id |
| created_at | DateTime(tz) | YES | |

### customers — 客户

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| name | String(100) | NO | 客户名 |
| contact_name | String(100) | YES | 联系人 |
| phone | String(30) | YES | 手机号 |
| email | String(100) | YES | 邮箱 |
| source | String(50) | YES | 来源 |
| level | String(20) | YES | 等级 |
| owner_user_id | UUID | YES | FK → users.id, 归属销售 |
| follow_status | String(30) | YES | 跟进状态 |
| remark | Text | YES | 备注 |
| created_by | UUID | YES | FK → users.id |
| updated_by | UUID | YES | FK → users.id |
| created_at | DateTime(tz) | YES | |
| updated_at | DateTime(tz) | YES | |
| deleted_at | DateTime(tz) | YES | 软删除 |

**索引**：name, phone, owner_user_id, deleted_at

### sales_orders — 销售订单

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| order_no | String(64) | NO | UNIQUE, ORD-YYYYMMDD-XXXX |
| customer_id | UUID | NO | FK → customers.id |
| sales_user_id | UUID | NO | FK → users.id |
| status | String(30) | NO | draft / confirmed / cancelled / partially_paid / completed |
| total_amount | Numeric(12,2) | NO | 销售总额 |
| total_cost | Numeric(12,2) | NO | 成本总额 |
| gross_profit | Numeric(12,2) | NO | 毛利 |
| gross_margin | Numeric(8,4) | NO | 毛利率 |
| paid_amount | Numeric(12,2) | NO | 已收金额 |
| remark | Text | YES | 备注 |
| created_by | UUID | YES | FK → users.id |
| updated_by | UUID | YES | FK → users.id |
| created_at | DateTime(tz) | YES | |
| updated_at | DateTime(tz) | YES | |
| deleted_at | DateTime(tz) | YES | 软删除 |

**索引**：order_no (UNIQUE), customer_id, sales_user_id, status, created_at, deleted_at

**状态机**：draft → confirmed → partially_paid → completed（或任意阶段 → cancelled，但有收款记录时需先冲正）

### sales_order_items — 订单明细

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| order_id | UUID | NO | FK → sales_orders.id (CASCADE) |
| product_id | UUID | NO | FK → products.id |
| product_sku_snapshot | String(64) | YES | 下单时 SKU 快照 |
| product_name_snapshot | String(100) | NO | 下单时商品名快照 |
| product_image_url_snapshot | Text | YES | 下单时图片快照 |
| quantity | Integer | NO | 数量 |
| unit_price | Numeric(12,2) | NO | 成交单价 |
| discount_amount | Numeric(12,2) | NO | 折扣金额 |
| discount_rate | Numeric(8,4) | NO | 折扣率 |
| cost_price_snapshot | Numeric(12,2) | NO | 下单时成本价快照 |
| subtotal_amount | Numeric(12,2) | NO | 小计金额 |
| subtotal_cost | Numeric(12,2) | NO | 小计成本 |

**索引**：order_id

### inventory_movements — 库存流水

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| product_id | UUID | NO | FK → products.id |
| movement_type | String(30) | NO | order_confirm / order_cancel / manual_adjust |
| quantity_before | Integer | NO | 变动前数量 |
| quantity_change | Integer | NO | 变动量（正=入库，负=出库） |
| quantity_after | Integer | NO | 变动后数量 |
| related_type | String(30) | YES | 关联类型（多态） |
| related_id | UUID | YES | 关联 ID |
| operator_id | UUID | YES | FK → users.id |
| remark | Text | YES | 备注 |
| created_at | DateTime(tz) | YES | |

**索引**：product_id

### payments — 收款

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| order_id | UUID | NO | FK → sales_orders.id |
| amount | Numeric(12,2) | NO | 收款金额 |
| payment_method | String(30) | NO | cash / transfer / wechat / alipay |
| paid_at | DateTime(tz) | YES | 收款时间 |
| operator_id | UUID | YES | FK → users.id |
| status | String(20) | NO | normal / reversed |
| remark | Text | YES | 备注 |
| created_at | DateTime(tz) | YES | |

**索引**：order_id

### audit_logs — 审计日志

| 列 | 类型 | 可空 | 说明 |
|---|---|---|---|
| id | UUID | NO | PK |
| actor_id | UUID | YES | FK → users.id (SET NULL) |
| actor_name | String(100) | YES | 冗余存储操作人名 |
| action | String(50) | NO | 操作类型 |
| resource_type | String(50) | YES | 资源类型 |
| resource_id | String(64) | YES | 资源 ID |
| before_data | Text | YES | 变更前 JSON 快照 |
| after_data | Text | YES | 变更后 JSON 快照 |
| ip_address | String(45) | YES | 请求 IP |
| user_agent | String(500) | YES | 浏览器 UA |
| request_id | String(64) | YES | 请求追踪 ID |
| created_at | DateTime(tz) | YES | |

**索引**：actor_id, action, resource_type, created_at, 复合索引 (action, resource_type)

## 字段约束

Schema 验证层（Pydantic `max_length`）和数据库层（`String(N)`）的约束关系：

### 完全一致（Schema = Model）

| 表 | 字段 | 长度 |
|---|---|---|
| users | username | 50 |
| users | display_name | 100 |
| users | email | 100 |
| users | phone | 30 |
| customers | name | 100 |
| customers | contact_name | 100 |
| customers | email | 100 |
| customers | phone | 30 |
| products | name | 100 |

### Schema 更严格（安全差异）

| 表 | 字段 | Schema | Model | 说明 |
|---|---|---|---|---|
| products | sku | 50 | 64 | 自动生成 SKU 约 18 字符，50 已充裕 |
| products | main_image_url | 500 | Text | Schema 限制输入长度 |
| *（多表）* | remark | 500 | Text | Schema 限制输入长度，DB 无上限 |
| users | password | 100 | 255 | 原始密码 vs 哈希存储，逻辑不同 |

### 验证规则

| 字段 | 规则 |
|---|---|
| phone（客户） | 正则 `^1[3-9]\d{9}$`，仅接受中国大陆手机号 |
| email | 正则 `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| password | 至少 6 位，必须含字母和数字 |
| sku | 自动生成 `SPU-YYYYMMDD-XXXX`，唯一 |
| order_no | 自动生成 `ORD-YYYYMMDD-XXXX`，唯一 |

## 种子数据

系统初始化时（`python -m app.db.seed`）创建：

- 默认管理员：`admin` / `admin123`（is_superuser=True）
- 6 个角色：超级管理员、销售经理、销售员、财务、仓库、客服
- 33 个权限码，覆盖 9 个模块
- 默认商品分类："未分类"

## 迁移

```bash
# 生成迁移
cd backend && alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```
