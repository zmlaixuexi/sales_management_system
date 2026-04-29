# API 接口文档

基础路径：`/api/v1`

## 认证

除健康检查和登录接口外，所有接口均需在请求头携带 JWT Token：

```
Authorization: Bearer <access_token>
```

## 通用响应格式

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

错误响应：

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

分页响应的 `data` 结构：

```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

## 错误码

| HTTP 状态码 | code | 说明 |
|---|---|---|
| 400 | VALIDATION_FAILED | 参数校验失败 |
| 400 | ORDER_EMPTY_ITEMS | 订单明细为空 |
| 400 | ORDER_INVALID_STATUS | 订单状态不允许此操作 |
| 400 | INVENTORY_NOT_ENOUGH | 库存不足 |
| 400 | PAYMENT_AMOUNT_EXCEEDED | 收款金额超过剩余应收 |
| 400 | PRODUCT_SKU_DUPLICATED | 商品编码重复 |
| 401 | AUTH_UNAUTHORIZED | 未认证或 Token 无效 |
| 403 | AUTH_FORBIDDEN | 无权限执行此操作 |
| 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| 409 | CUSTOMER_DUPLICATED_WARNING | 客户手机号重复 |
| 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁，请稍后再试 |

## 速率限制

所有 `/api/` 路径受 IP 级速率限制保护（滑动窗口算法）。

- 默认限制：1000 请求 / 60 秒（可通过 `RATE_LIMIT_MAX` 和 `RATE_LIMIT_WINDOW` 环境变量配置）
- 正常响应头：`X-RateLimit-Limit`（窗口上限）、`X-RateLimit-Remaining`（剩余次数）
- 超限返回 429 + `RATE_LIMIT_EXCEEDED` 错误码

## 安全响应头

所有 API 响应自动附加以下安全头：

| 响应头 | 值 | 说明 |
|---|---|---|
| X-Content-Type-Options | nosniff | 防止 MIME 类型嗅探 |
| X-Frame-Options | DENY | 禁止 iframe 嵌入 |
| X-XSS-Protection | 1; mode=block | XSS 过滤 |
| Referrer-Policy | strict-origin-when-cross-origin | 限制 Referer 泄露 |
| Content-Security-Policy | default-src 'none'; frame-ancestors 'none' | API 严格 CSP |
| Permissions-Policy | camera=(), microphone=(), geolocation=() | 禁用浏览器特性 |

## 请求日志

所有 `/api/` 请求自动记录结构化日志，包含：

- `method`：请求方法（GET/POST/PUT/DELETE）
- `path`：请求路径
- `status`：响应状态码
- `duration_ms`：请求耗时（毫秒）
- `client_ip`：客户端 IP 地址

JSON 日志格式示例：

```json
{"timestamp":"2026-04-30T12:00:00Z","level":"INFO","logger":"app.request","message":"GET /api/v1/health 200 3.5ms","method":"GET","path":"/api/v1/health","status":200,"duration_ms":3.5,"client_ip":"127.0.0.1"}
```

---

## 健康检查

### GET /health

健康检查，无需认证。包含数据库连接探测。

**响应**（正常）：`{"status": "ok"}`
**响应**（数据库不可用）：`{"status": "degraded"}`

### GET /version

查询系统版本号，无需认证。

**响应**：`{"version": "0.1.0"}`

---

## 认证模块

### POST /auth/login

用户名密码登录。

**请求体**：
```json
{ "username": "admin", "password": "password123" }
```

**响应**：
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

### POST /auth/refresh

刷新 Token。

**请求体**：`{ "refresh_token": "eyJ..." }`

**响应**：同登录接口。

### POST /auth/logout

退出登录（前端清除 Token）。

### GET /auth/me

获取当前用户信息，含角色和权限列表。

**响应**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "username": "admin",
    "display_name": "管理员",
    "is_active": true,
    "is_superuser": false,
    "roles": [{"id": "uuid", "name": "admin", "display_name": "管理员"}],
    "permissions": ["product:list", "product:create", ...]
  }
}
```

---

## 用户管理

> 以下接口仅超级管理员可用。

### GET /users

用户列表。

**查询参数**：`page`, `page_size`, `keyword`

### POST /users

新增用户。

**请求体**：
```json
{
  "username": "sale01",
  "password": "password123",
  "display_name": "销售员A",
  "phone": "13800000001",
  "role_ids": ["uuid"]
}
```

### PUT /users/{user_id}

编辑用户信息。

---

## 文件上传

### POST /files/images

上传图片，`multipart/form-data` 格式，字段名 `file`。

**响应**：`{ "id": "uuid", "url": "/uploads/xxx.jpg" }`

### GET /files/images/{file_id}

获取图片信息。

### DELETE /files/images/{file_id}

删除未被引用的图片。

---

## 商品管理

### GET /products

商品列表。

**查询参数**：`page`, `page_size`, `keyword`, `status`, `category_id`, `sort_by`, `sort_order`

**权限**：`product:list`。无 `product:view_cost` 权限时不返回 cost_price、unit_profit、gross_margin。

### POST /products

新增商品。

**请求体**：
```json
{
  "name": "商品A",
  "cost_price": "50.00",
  "sale_price": "100.00",
  "stock_quantity": 100,
  "category_id": "uuid",
  "status": "active"
}
```

**权限**：`product:create`

### GET /products/{product_id}

商品详情，含图片列表。

**权限**：`product:list`

### PUT /products/{product_id}

编辑商品。价格变更时自动记录价格历史。

**权限**：`product:update`

### DELETE /products/{product_id}

软删除商品。

**权限**：`product:delete`

### POST /products/{product_id}/disable

停用商品。

**权限**：`product:update`

### GET /products/{product_id}/price-history

价格变更历史。

**权限**：`product:list`

---

## 客户管理

### GET /customers

客户列表。

**查询参数**：`page`, `page_size`, `keyword`, `source`, `owner_user_id`

**权限**：`customer:list`。无 `customer:view_all` 权限时只返回本人客户。

### POST /customers

新增客户，含手机号重复检测。

**请求体**：
```json
{
  "name": "客户A",
  "contact_name": "张三",
  "phone": "13800000001",
  "source": "referral",
  "level": "vip",
  "owner_user_id": "uuid"
}
```

**权限**：`customer:create`

### GET /customers/{customer_id}

客户详情。

**权限**：`customer:list`

### PUT /customers/{customer_id}

编辑客户。

**权限**：`customer:update`

### DELETE /customers/{customer_id}

软删除客户。

**权限**：`customer:delete`

### POST /customers/{customer_id}/transfer

转移客户归属销售。

**请求体**：`{ "owner_user_id": "uuid" }`

**权限**：`customer:update`

---

## 订单管理

### GET /sales-orders

订单列表。

**查询参数**：`page`, `page_size`, `keyword`, `status`, `customer_id`

**权限**：`order:list`。无 `order:view_all` 权限时只返回本人订单。

### POST /sales-orders

创建草稿订单。

**请求体**：
```json
{
  "customer_id": "uuid",
  "items": [
    { "product_id": "uuid", "quantity": 5, "unit_price": "100.00" }
  ],
  "remark": "备注"
}
```

**权限**：`order:create`

### GET /sales-orders/{order_id}

订单详情，含明细和收款记录。

**权限**：`order:list`

### PUT /sales-orders/{order_id}

编辑草稿订单（仅 draft 状态可编辑）。

**权限**：`order:update`

### POST /sales-orders/{order_id}/confirm

确认订单，自动扣减库存。

**权限**：`order:confirm`

### POST /sales-orders/{order_id}/cancel

取消订单。已确认订单自动回滚库存。

**权限**：`order:cancel`

**状态流转**：draft → confirmed → cancelled（draft 也可直接取消）

---

## 收款管理

### GET /payments

收款列表。

**查询参数**：`page`, `page_size`, `order_id`

**权限**：`payment:list`

### POST /payments/orders/{order_id}/payments

登记收款。收款金额达到订单总额时自动标记为 completed。

**请求体**：
```json
{
  "amount": "500.00",
  "payment_method": "cash",
  "remark": "首期款"
}
```

**权限**：`payment:create`

### POST /payments/{payment_id}/reverse

冲正（撤销）收款。

**权限**：`payment:reverse`

---

## 库存管理

### GET /inventory/movements

库存流水。

**查询参数**：`page`, `page_size`, `product_id`, `movement_type`

**权限**：`inventory:list`

### POST /inventory/adjustments

手工调整库存。

**请求体**：
```json
{
  "product_id": "uuid",
  "quantity_change": 10,
  "remark": "盘点调整"
}
```

**权限**：`inventory:adjust`

---

## 报表

### GET /reports/sales-summary

销售汇总。

**查询参数**：`period`（可选，默认 `30d`，可选值：`today`/`7d`/`30d`/`this_month`/`last_month`）

**响应**：总销售额、总成本、毛利、毛利率、订单数。

**权限**：`report:sales`

### GET /reports/sales-trend

按日销售趋势（自动填充空缺日期）。

**查询参数**：`period`（同上）

**权限**：`report:sales`

### GET /reports/product-ranking

商品销售排行（按销售额降序）。

**查询参数**：`period`（同上）、`limit`（可选，默认 10，最大 50）

**权限**：`report:sales`

### GET /reports/inventory-warning

库存预警（低于阈值的活跃商品）。

**查询参数**：`threshold`（可选，默认从 `INVENTORY_WARNING_THRESHOLD` 环境变量读取，默认 10）

**响应**：`items`（商品列表）、`threshold`（使用的阈值）、`total`（预警数量）

**权限**：`report:sales`

---

## 审计日志

### GET /audit-logs

操作日志列表。

**查询参数**：`page`, `page_size`, `action`, `resource_type`, `actor_id`, `start_date`, `end_date`, `keyword`

**响应字段**：每条日志包含 `ip_address`、`user_agent`、`request_id`（请求元数据）。

**权限**：`audit:view`

**操作类型**：`login_success`/`login_failed`/`product_create`/`product_update`/`product_delete`/`product_disable`/`customer_create`/`customer_update`/`customer_delete`/`customer_transfer`/`order_create`/`order_update`/`order_confirm`/`order_cancel`/`payment_create`/`payment_reverse`/`inventory_adjust`/`export_products`/`export_customers`/`export_orders`/`export_payments`

### GET /audit-logs/actions

获取所有操作类型和资源类型列表（用于筛选下拉框）。

**权限**：`audit:view`

---

## 数据导出

所有导出接口返回 CSV 文件流（`text/csv; charset=utf-8`，含 BOM 头），响应头包含 `Content-Disposition` 文件名。

每次导出自动生成审计日志记录。

### GET /exports/products

导出商品。查询参数同商品列表（`keyword`、`status`、`category_id`）。

**权限**：`product:list`

### GET /exports/customers

导出客户。无 `customer:view_all` 时只导出本人客户。查询参数：`keyword`、`source`。

**权限**：`customer:list`

### GET /exports/orders

导出订单。无 `order:view_all` 时只导出本人订单。查询参数：`keyword`、`status`、`customer_id`、`start_date`、`end_date`。

**权限**：`order:list`

### GET /exports/payments

导出收款记录。查询参数：`order_id`、`start_date`、`end_date`。

**权限**：`payment:list`

---

## 权限码一览

| 权限码 | 说明 |
|---|---|
| product:list | 商品列表和详情 |
| product:create | 新增商品 |
| product:update | 编辑和停用商品 |
| product:delete | 删除商品 |
| product:view_cost | 查看成本价、利润、毛利率 |
| customer:list | 客户列表和详情 |
| customer:create | 新增客户 |
| customer:update | 编辑和转移客户 |
| customer:delete | 删除客户 |
| customer:view_all | 查看所有客户（否则只看本人） |
| order:list | 订单列表和详情 |
| order:create | 创建订单 |
| order:update | 编辑订单 |
| order:confirm | 确认订单 |
| order:cancel | 取消订单 |
| order:view_all | 查看所有订单（否则只看本人） |
| payment:list | 收款列表 |
| payment:create | 登记收款 |
| payment:reverse | 冲正收款 |
| inventory:list | 库存流水 |
| inventory:adjust | 手工调整库存 |
| report:sales | 查看报表 |
| audit:view | 查看审计日志 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | 应用环境 |
| `DATABASE_URL` | (localhost) | 数据库同步连接 |
| `JWT_SECRET_KEY` | `change-me` | JWT 签名密钥（生产必须修改） |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | 访问令牌有效期（分钟） |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌有效期（天） |
| `CORS_ORIGINS` | `http://localhost:5173` | CORS 允许的前端地址（逗号分隔） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `LOG_FORMAT` | `text` | 日志格式（`text` 或 `json`） |
| `UPLOAD_DIR` | `uploads` | 上传文件目录 |
| `MAX_IMAGE_SIZE_MB` | `5` | 图片上传大小限制 |
| `INVENTORY_WARNING_THRESHOLD` | `10` | 库存预警默认阈值 |
| `RATE_LIMIT_MAX` | `1000` | API 速率限制（每窗口请求数） |
| `RATE_LIMIT_WINDOW` | `60` | 速率限制窗口（秒） |
