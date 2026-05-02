# 测试文档

## 概览

| 指标 | 值 |
|---|---|
| 后端测试总数 | 832 |
| 后端测试文件 | 40 |
| 前端测试总数 | 382 |
| 前端测试文件 | 37 |
| 测试总计 | 1214 |
| 后端覆盖率 | 99.79% |
| 覆盖模块 | 认证、商品、客户、订单、库存、收款、报表（含客户/销售人员排行）、审计日志（含手机号/邮箱脱敏）、数据导出（含权限/数据范围/敏感字段边界）、批量导入（含负价格/非法格式/英文表头/批量内去重）、权限校验（含导出敏感字段过滤、报表利润权限）、速率限制、SQL 注入防护、XSS 防护、请求 ID 中间件、CORS 验证、日志格式器（JSON/文本/setup_logging）、金额计算、文件服务（含 FILE_TOO_LARGE/FILE_NOT_BOUND 错误码、上传权限 403）、密码强度、订单操作日志、支付路径（含已取消/已完成订单拒绝、无权限 403）、派生销售字段、响应体 request_id、报表 period 参数校验、CSV 导入校验（含行数上限+XSS 消毒+commit 回滚）、客户 source/level 枚举校验、生产环境 OpenAPI 禁用、SQL 慢查询日志、用户管理（含角色列表 API 和权限边界）、安全模块（bcrypt 72 字节截断/JWT token 篡改/过期/错误密钥/iat/jti）、报表辅助函数（_date_range/_apply_data_scope）、导出 API 辅助函数（_csv_filename）、登录速率限制辅助函数（_check_login_rate_limit/_record_login_fail）、商品辅助函数（_batch_sales_stats/_validate_category_id/_get_default_category_id）、客户辅助函数（_validate_owner_user）、订单库存辅助函数（_deduct_inventory/_restore_inventory）、订单明细校验（_validate_and_prepare_items）、收款登记服务（register_payment）、请求体大小限制中间件（BodyLimitMiddleware）、外键验证边界（含无效 UUID/不存在用户/不存在客户/不存在商品）、导出服务软删除过滤（商品/客户/订单/收款排除已删除记录）、中间件（BodyLimit 请求体限制/RequestLog 日志记录） |

## 运行测试

```bash
# 运行全部后端测试
cd backend
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_auth.py -v

# 运行全部前端测试
cd frontend
npx vitest run

# 运行单个前端测试文件
npx vitest run src/__tests__/auth-store.test.ts

# 运行 lint
cd backend && ruff check .
cd frontend && npx eslint src/
```

## 后端测试架构

### 测试数据库

每个测试模块使用独立的 SQLite 文件数据库（非内存），在 `setup_module` 中创建、`teardown_module` 中销毁：

| 测试文件 | 数据库文件 | 说明 |
|---|---|---|
| test_auth.py | test.db | 非超级用户，测试 RBAC |
| test_integration.py | test_integration.db | 超级用户，完整业务流程 |
| test_audit_log.py | test_audit_log.db | 超级用户，审计日志验证 |
| test_export.py | test_export.db | 超级用户，CSV 导出 |
| test_file_upload.py | test_file_upload.db | 超级用户，文件上传 |
| test_permissions.py | test_permissions.db | 管理员+销售员，权限校验 |
| test_edge_cases.py | test_edge.db | 超级用户，异常路径 |
| test_validation.py | test_validation.db | 超级用户，验证补充 |
| test_boundary.py | test_boundary.db | 超级用户，边界测试 |
| test_reports_audit.py | test_reports.db | 管理员+无权限用户 |
| test_product_import.py | test_product_import.db | 超级用户，商品导入 |
| test_customer_import.py | test_customer_import.db | 超级用户，客户导入 |
| test_ratelimit.py | test_ratelimit.db | 速率限制 |
| test_sanitize.py | （无） | 纯函数测试，无需数据库 |
| test_health.py | （无） | 健康检查无需数据库，mock 数据库连接 |
| test_user_management.py | test_user_mgmt.db | 管理员，用户 CRUD |
| test_customer_crud.py | test_customer_crud.db | 管理员，客户详情/编辑/转移/删除 |
| test_product_crud.py | test_product_crud.db | 管理员，商品详情/删除 |
| test_order_crud.py | test_order_crud.db | 管理员，订单创建/详情/编辑/确认/取消/库存联动 |
| test_payment_crud.py | test_payment_crud.db | 管理员，收款登记/超额/冲正/状态回退 |
| test_inventory_crud.py | test_inventory_crud.db | 管理员，库存调整/流水查询/筛选 |
| test_deps.py | （SQLite 内存） | 辅助函数测试（含 DB 依赖函数） |
| test_order_calc.py | （无） | 纯函数测试，订单金额计算 |
| test_product_calc.py | （无） | 纯函数测试，商品利润计算 |
| test_audit_service.py | （无） | 纯函数测试，审计脱敏/模型转换 |
| test_logging.py | （无） | 纯函数测试，JSON/文本日志格式器+setup_logging |
| test_schema_validators.py | （无） | 纯函数测试，Pydantic field_validator |
| test_security.py | （无） | 纯函数测试，bcrypt 哈希/验证+JWT token |
| test_reports_helpers.py | （无） | 纯函数测试，报表 _date_range/_apply_data_scope |
| test_exports_api.py | （无） | 纯函数测试，导出 API _csv_filename |
| test_auth_rate_limit.py | （无） | 纯函数测试，登录速率限制 _check_login_rate_limit/_record_login_fail |
| test_product_helpers.py | （SQLite 内存） | 商品辅助函数 _batch_sales_stats/_validate_category_id/_get_default_category_id |
| test_customer_helpers.py | （SQLite 内存） | 客户辅助函数 _validate_owner_user |
| test_order_inventory.py | （SQLite 内存） | 订单库存辅助函数 _deduct_inventory/_restore_inventory |
| test_order_validate_items.py | （SQLite 内存） | 订单明细校验 _validate_and_prepare_items |
| test_payment_register.py | （SQLite 内存） | 收款登记服务 register_payment |
| test_body_limit.py | test_body_limit.db | 请求体大小限制中间件 |

### 依赖注入覆盖

所有测试模块通过 `app.dependency_overrides[get_db]` 替换数据库依赖，teardown 时恢复原始覆盖。

### 认证方式

测试用户通过 API 登录获取 JWT Token，后续请求通过 `Authorization: Bearer <token>` 头传递。

### 测试执行顺序

`conftest.py` 确保速率限制测试（test_ratelimit.py）始终最后运行，避免影响其他测试。

### 测试标记

`conftest.py` 根据文件名自动应用 pytest 标记，支持选择性运行：

```bash
pytest -m crud        # 仅 CRUD 操作测试
pytest -m security    # 仅安全相关测试
pytest -m boundary    # 仅边界值测试
pytest -m "not slow"  # 排除慢速测试
```

| 标记 | 说明 | 测试数 |
|---|---|---|
| crud | CRUD 操作测试 | 248 |
| boundary | 边界值和异常路径 | 103 |
| security | 认证/权限/速率限制/XSS 防护 | 96 |
| export | 导出功能 | 62 |
| import | 导入功能 | 42 |
| report | 报表和审计日志 | 77 |
| integration | 集成测试 | 52 |
| infra | 基础设施（健康检查/中间件/日志） | 34 |

---

## 后端测试文件详解

### test_health.py（18 个测试）

健康检查、版本接口、中间件验证、异常处理、CORS 和生产环境安全检查，无需认证。

| 测试 | 说明 |
|---|---|
| test_health_check | GET /health 返回 ok |
| test_version | GET /version 返回版本号 |
| test_security_headers | 安全响应头验证（CSP、X-Frame-Options 等） |
| test_request_log_records_api_calls | API 请求被请求日志中间件记录 |
| test_request_log_ignores_non_api | 非 API 路径不被记录 |
| test_request_id_generated_when_missing | 请求无 X-Request-ID 时自动生成 UUID |
| test_request_id_passthrough | 请求带 X-Request-ID 时透传回响应 |
| test_request_id_in_log | request_id 写入请求日志 extra_fields |
| test_production_env_rejects_default_secret | 生产环境 JWT 默认密钥拒绝启动 |
| test_unhandled_exception_returns_json | 未处理异常返回一致 JSON 格式 |
| test_cors_allowed_origin | 允许的 Origin 返回 CORS 响应头 |
| test_cors_disallowed_origin | 不允许的 Origin 不返回 CORS 响应头 |
| test_request_id_in_response_body | 响应体包含 request_id 字段 |
| test_request_id_in_response_body_passthrough | 响应体透传请求中的 request_id |
| test_openapi_disabled_in_production | 生产环境 OpenAPI 文档端点配置为 None |

### test_auth.py（16 个测试）

认证模块，测试用户为非超级用户。

| 测试 | 说明 |
|---|---|
| test_login_success | 正确用户名密码登录 |
| test_login_wrong_password | 错误密码返回 401 |
| test_get_me_authorized | 携带 Token 获取用户信息 |
| test_get_me_unauthorized | 无 Token 返回 401 |
| test_refresh_token | 刷新 Token |
| test_non_admin_forbidden | 非管理员访问 /users 被 403 |
| test_login_nonexistent_user | 不存在用户返回 401 |
| test_refresh_rejected_for_inactive_user | 禁用用户刷新 Token 被拒绝 |

### test_integration.py（28 个测试，8 个类）

完整业务流程端到端测试。

| 类 | 测试数 | 覆盖功能 |
|---|---|---|
| TestAuth | 2 | 登录、获取用户信息 |
| TestProduct | 3 | 创建商品、列表、创建第二个商品 |
| TestCustomer | 3 | 创建客户、列表、手机号重复检测 |
| TestOrder | 6 | 创建草稿、详情、列表、空明细校验、确认、重复确认 |
| TestInventory | 2 | 库存流水查询、手工调整 |
| TestPayment | 4 | 登记收款、部分收款、超额收款、冲正 |
| TestReport | 4 | 销售汇总、趋势、商品排行、库存预警 |
| TestOrderLogs | 3 | 订单日志查询、分页、404 |

### test_audit_log.py（19 个测试）

审计日志验证。每个测试先执行业务操作，再查询审计日志确认记录正确。新增：未认证 401（列表/操作类型）、无效 actor_id 422、分页参数越界 422。

### test_export.py（37 个测试）

CSV 数据导出验证，包括基本导出、多维度筛选（keyword/status/date/customer/order）、认证和 CSV 格式验证（BOM、表头顺序、字段数一致性、状态中文映射、数据值精确匹配）、无权限用户 403、成本价字段按权限隐藏、数据范围过滤、未认证 401（客户/订单/收款）、无效 UUID 422。

### test_file_upload.py（24 个测试）

图片上传、类型/大小校验（FILE_INVALID_TYPE/FILE_TOO_LARGE 独立错误码）、获取/删除、认证验证、已绑定商品图片 FILE_NOT_BOUND 拒绝、伪装扩展名拒绝、GET/DELETE 未认证 401、无效 UUID 422、缺少 file 字段 422、跨用户文件查看/删除权限验证、上传/删除审计日志。

### test_permissions.py（9 个测试）

数据范围权限、敏感字段过滤、权限码拦截、导出数据范围过滤。

### test_edge_cases.py（31 个测试）

6 大业务模块异常路径：缺字段、负值、重复、404、状态转换、库存不足、伪造 Token。

### test_validation.py（25 个测试）

refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表、密码强度校验。

### test_boundary.py（47 个测试）

认证边界、订单状态机、收款边界（草稿收款、超额、冲正回退）、用户管理、库存调整、流水类型筛选。

### test_reports_audit.py（42 个测试）

销售汇总（6 种 period）、趋势、排行、预警、审计日志查询/筛选/权限、客户排行（含数据范围过滤和利润可见性）、销售人员排行（含数据范围过滤和利润可见性）、未认证 401（6 端点 parametrize）、排行 limit 边界值 422、库存预警负数阈值 422、无效 period 错误码验证。

### test_product_import.py（17 个测试）

商品 CSV 批量导入：成功、SKU 自动生成、重复 SKU、空名称、非 CSV、认证、中文表头、大小限制、行数上限、XSS 消毒、commit 回滚失败、负价格拒绝、非法销售价/成本价格式、英文表头、批量内 SKU 重复。

### test_customer_import.py（16 个测试）

客户 CSV 批量导入：成功、手机号重复、批量内去重、空名称、非 CSV、认证、大小限制、行数上限、XSS 消毒、source/level 枚举校验、commit 回滚失败、英文表头、无电话号码可选。

### test_ratelimit.py（5 个测试）

速率限制响应头验证、429 触发验证（含响应头）、窗口清理。

### test_sanitize.py（14 个测试）

`escape_like()` 函数特殊字符转义（%、_、\\）、`strip_html()` XSS 防护（script 标签/事件属性/style 标签/嵌套标签/正常 HTML 保留）、schema 字段消毒（商品名称/客户名称/客户邮箱/用户邮箱）。

### test_user_management.py（25 个测试）

用户管理 CRUD + 角色列表：列表/搜索、创建（含重复用户名）、编辑、禁用切换、角色变更、编辑时无效角色 ID 返回 400、403 权限校验、分页参数、未认证 401、弱密码 422、创建时无效角色 ID 400、角色列表 GET /users/roles（正常返回/非管理员 403/未认证 401）、管理员不能停用自身账号、非管理员查看用户列表 403。

### test_customer_crud.py（28 个测试）

客户 CRUD 成功路径 + 认证边界：详情获取、编辑验证、归属转移、软删除验证、列表按来源/关键词/归属筛选、手机号更新/重复检测、CSV 导入编码/空表头、未认证获取/编辑/删除 401、无效 UUID 422。

### test_product_crud.py（44 个测试）

商品 CRUD 成功路径 + CSV 导入：详情获取、软删除、删除后不可见、列表排除已删除、分类筛选/排序、SKU 更新、CSV 导入（成功/编码错误/空表头/行错误/SKU 重复/大小限制）。

### test_order_crud.py（43 个测试）

订单 CRUD + 状态流转全生命周期：创建（正常/空明细/客户不存在/商品不存在/零数量/负价拒绝/低于成本价拒绝）、详情/404/列表/状态筛选/客户筛选、编辑草稿（修改明细+金额重算+负价拒绝/低于成本价拒绝）、确认（库存扣减验证）、取消（库存回滚/商品已删除跳过）、库存不足确认失败、低于成本价阻止下单、订单号后缀回退。

### test_payment_crud.py（27 个测试）

收款登记 + 冲正：创建（部分收款→partially_paid、全额→completed）、超额收款、零金额、草稿不可收款、订单不存在、列表全量/按 order_id 筛选/非管理员数据范围过滤/分页、冲正/重复冲正/不存在/关联订单已删除、已取消订单收款拒绝、已完成订单收款拒绝、负数金额、无权限用户收款/冲正 403、冲正后 completed→partially_paid 回退、冲正全部金额后→confirmed 回退。路径已对齐规范文档 POST /sales-orders/{id}/payments。

### test_inventory_crud.py（21 个测试）

库存调整 + 流水查询：手工调整（增加/减少/归零）、零调整拒绝、超量扣减拒绝、商品不存在、流水列表/按 product_id 筛选/按 movement_type 筛选、字段完整性校验、无调整权限 403、无列表权限 403、已删除商品调整 404、流水分页、order_confirm 类型筛选、未认证访问 401（流水/调整）、无效商品 UUID 400、调整响应字段验证、不存在 product_id 筛选空列表、备注 XSS strip_html。

### test_deps.py（26 个测试）

权限辅助函数 + DB 依赖函数单元测试：`_get_user_permissions` 多角色收集/空角色/跨角色去重，`has_permission` 超级用户/有权限/无权限，`check_owner_or_forbid` 超管/view_all/所有者/403，`parse_uuid_or_400` 有效/无效，`resp` 默认/自定义，`paginated_resp` 结构/自定义消息，`get_or_404` 存在/不存在/无效 UUID/软删除/无 deleted_at，`generate_sequential_code` 首次/递增，`paginate` 首页/末页/空表。

### test_export_helpers.py（22 个测试）

CSV 导出辅助函数 + 行构建函数单元测试：`_dec` Decimal/None/零/负数，`_str` 字符串/None，`_dt` datetime/None/ISO 格式，`_product_row` 有/无成本权限/状态映射，`_order_row` 有/无成本权限/订单状态映射，`_customer_row` 基础，`_payment_row` 正常/冲正状态。

### test_file_service.py（13 个测试）

文件上传校验单元测试：扩展名白名单、MIME 类型、文件大小、正常通过、webp 格式、大写扩展名、扩展名与 MIME 独立校验、边界大小（恰好等于限制/超限 1 字节）、魔数字节校验（JPEG/PNG 有效头、无效头、空文件）。

### test_order_calc.py（10 个测试）

订单金额计算纯函数测试：`_calc_order_totals` 基本金额/零金额/空明细/毛利率精度/缺失字段，`_prepare_item` 默认价格/自定义价格/除零保护/快照字段/低于成本价阻止。

### test_product_calc.py（6 个测试）

商品利润计算纯函数测试：`_calc_profit` 基本利润/零售价除零保护/亏损/零利润/精度/高毛利率。

### test_audit_service.py（11 个测试）

审计服务内部函数测试：`_mask_sensitive` None/空字典/密码脱敏/token 脱敏/手机号脱敏/邮箱脱敏/无匹配，`model_to_dict` UUID 转字符串/None 跳过。

### test_logging.py（16 个测试）

日志模块测试：`_JsonFormatter` 基本 JSON/异常信息/extra_fields 合并/无异常字段，request_id/user_id contextvar 自动注入/空值跳过/优先级，`log_action` 数据库失败返回 None，`get_logger` 返回命名 logger，`_TextFormatter` 文本格式/ISO 日期格式，`setup_logging` root logger 级别/第三方库抑制/json/text 格式器选择。

### test_csv_import.py（9 个测试）

CSV 导入校验共享函数测试：文件扩展名验证、BOM 检测、UTF-8 编码校验、大小限制、空文件、仅有表头、缺少表头、非 CSV 扩展名、正常通过。

### test_schema_validators.py（23 个测试）

Schema 校验器单元测试，覆盖全部 Pydantic field_validator：OrderItemInput 单价非负，OrderCreate/Update 备注 strip_html，PaymentCreate 金额正数+备注 strip_html，InventoryAdjust 备注 strip_html，ProductCreate/Update 名称+备注 strip_html，CustomerCreate/Update 名称/邮箱/联系人 strip_html，UserCreate 密码强度+邮箱 strip_html，UserUpdate 显示名 strip_html，ChangePasswordRequest 密码强度+长度。

### test_slow_query.py（5 个测试）

SQL 慢查询日志测试：监听器注册（超过阈值时日志记录）、低于阈值不记录、禁用时不注册监听器、模拟慢查询完整日志路径（含 request_id 关联）、长 SQL 截断。

### test_security.py（14 个测试）

安全模块纯函数测试：`hash_password` bcrypt 格式/不同盐值，`verify_password` 正确/错误/空密码/hash_password 联动，`create_access_token` 解码/type=access/exp/自定义过期，`create_refresh_token` 解码/type=refresh/exp/过期时间晚于 access。

### test_reports_helpers.py（11 个测试）

报表辅助函数纯函数测试：`_date_range` 全分支（today/7d/30d/this_month/last_month/无效 period）+ 边界（跨月/跨年/月初），`_apply_data_scope` 管理员不过滤/销售只看自己。

### test_exports_api.py（3 个测试）

导出 API 辅助函数纯函数测试：`_csv_filename` 文件名格式（前缀_时间戳.csv）/不同前缀/始终以 .csv 结尾。

### test_auth_rate_limit.py（5 个测试）

登录速率限制辅助函数测试：`_check_login_rate_limit` 阈值通过（9 次）、阈值拒绝（10 次 429）、不同 IP 独立计数、过期记录清理。`_record_login_fail` 时间戳追加。使用 autouse fixture 重置模块级计数器。

### test_product_helpers.py（10 个测试）

商品辅助函数测试（SQLite 内存，fixture 隔离）：`_validate_category_id` 存在/不存在，`_get_default_category_id` 已存在/自动创建，`_batch_sales_stats` 空列表/无订单/已确认订单/排除草稿和已取消/排除软删除/多订单汇总。

### test_customer_helpers.py（4 个测试）

客户辅助函数测试（SQLite 内存，fixture 隔离）：`_validate_owner_user` 活跃通过/不存在/已禁用/软删除。

### test_order_inventory.py（10 个测试）

订单库存辅助函数测试（SQLite 内存，fixture 隔离）：`_deduct_inventory` 正常扣减/库存不足/商品不存在/软删除商品/多明细同时扣减/库存恰好等于需求。`_restore_inventory` 正常回滚/商品不存在静默跳过/软删除跳过/多明细同时回滚。验证 InventoryMovement 记录。

### test_order_validate_items.py（10 个测试）

订单明细校验函数测试（SQLite 内存，fixture 隔离）：`_validate_and_prepare_items` 单个/多个活跃商品、商品不存在(404)、软删除商品(404)、已停用商品(400)、已禁用商品(400)、自定义成交单价、空明细列表、无效 UUID 格式(400)、混合有效无效商品。

### test_payment_register.py（10 个测试）

收款登记服务测试（SQLite 内存，fixture 隔离）：`register_payment` 已确认订单部分收款→部分收款状态、全额收款→已完成、分两次收款→订单完成、订单不存在(404)、草稿/已取消/已完成订单不可收款(400)、超额收款拒绝(400)、恰好等于剩余通过、操作人和更新人记录。

### test_body_limit.py（7 个测试）

请求体大小限制中间件测试（TestClient + SQLite 文件）：正常 POST 通过、GET 请求不受限、超限请求体返回 413 PAYLOAD_TOO_LARGE、multipart/form-data 文件上传豁免、OPTIONS 请求不受限、恰好等于限制大小通过。

---

## 前端测试架构

### 测试框架

Vitest 4.x + @testing-library/react + @testing-library/jest-dom + jsdom 环境。

### 测试模式

- **纯函数测试**：直接调用函数验证返回值（utils、statusMaps、sanitize）
- **API 模块测试**：mock request/client 层，验证 API 调用参数和路径
- **Hook 测试**：使用 `renderHook` 测试自定义 React Hook
- **组件测试**：使用 `@testing-library/react` 渲染组件验证行为

## 前端测试文件详解

### 纯函数和工具

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| utils.test.ts | 19 | formatAmount / formatPercent / getApiErrorMessage（含 error.message 新格式、负数/大数/零/空字符串边界） |
| statusMaps.test.ts | 10 | 商品/客户来源/客户等级/订单（含 partially_paid/completed）/收款状态映射完整性（导入共享常量） |

### 基础设施

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| client.test.ts | 7 | API 客户端 baseURL、token 附加、无 token、timeout 15s、默认 Content-Type、X-Request-ID 生成和唯一性 |
| request.test.ts | 8 | get/post/put/del/upload 封装函数（含无参数 get、无 body post/put） |
| ErrorBoundary.test.tsx | 5 | 正常渲染 + 错误捕获 + 重试恢复 + 路由变化重置 + 返回首页 |
| AppLayout.test.tsx | 8 | 用户加载/显示名称/角色、菜单导航、退出清除 Token、getMe 失败、用户名回退、系统标题、菜单项数、路径高亮 |
| usePaginatedList.test.ts | 11 | 初始加载、错误处理、筛选、分页切换、刷新、空结果、_toastDisplayed 跳过、error 状态 |
| useSubmit.test.ts | 11 | 成功调用/提交中状态/错误提示/Ant Design 校验静默/防重/_toastDisplayed 跳过/默认 fallback/非 Error 异常/错误恢复/error.message/detail.message 提取 |
| client-interceptor.test.ts | 14 | 401 刷新、403/404/500 错误消息、网络错误、重试保护、429 重试、_toastDisplayed 标记、error.message 提取（新格式）、旧格式兼容、409 业务错误 |
| NotFound.test.tsx | 3 | 404 状态渲染/返回首页按钮/按钮点击导航 |
| ProtectedRoute.test.tsx | 5 | 无 token 重定向/加载中 Spin（large 尺寸）/已认证渲染子组件/fetchUser 失败/异步重定向 |

### API 模块（全部 9 个 API 模块已覆盖）

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| products-api.test.ts | 16 | fetchProducts（分类筛选/排序/派生字段）/fetchProduct（完整详情+图片列表）/create（可选字段）/update（价格）/delete/disable/priceHistory/uploadImage（文件信息） |
| customers-api.test.ts | 12 | fetchCustomers（完整数据）/fetchCustomer/create（可选字段）/update（联系方式）/delete/transfer（不同目标） |
| orders-api.test.ts | 14 | fetchOrders（关键词/客户ID/分页/无参数）/fetchOrder（完整明细+收款）/create（多商品）/update（明细）/confirm/cancel |
| payments-api.test.ts | 11 | fetchPayments（分页/完整记录）/createPayment（现金/微信/支付宝/备注）/reversePayment |
| reports-api.test.ts | 8 | fetchSalesSummary（含无参数）/Trend/ProductRanking/InventoryWarning（含无阈值）/CustomerRanking/SalespersonRanking |
| auditLogs-api.test.ts | 11 | fetchAuditLogs（筛选/日期/分页/关键词/完整条目/actor_id）/fetchAuditActions（空列表） |
| auth-api.test.ts | 8 | login（token 返回）/refresh/logout/getMe（权限列表）/changePassword |
| users-api.test.ts | 11 | fetchUsers（分页/完整数据）/create（最少/完整参数）/update（角色）/fetchRoles |
| inventory-api.test.ts | 10 | fetchInventory（分页/完整流水/无参数）/adjust（正负数/备注） |

### 状态管理和工具

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| auth-store.test.ts | 14 | login/logout/fetchUser/hasPermission/loading 状态、login success:false 不存 token、fetchUser success:false 不设 user、空权限数组 |
| downloadCsv.test.ts | 9 | 成功下载、查询参数、过滤、错误、文件名提取、attachment 前缀、全空参数、全有效参数 |

### 页面组件

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| Dashboard.test.tsx | 11 | 标题/期间选择器渲染、loading 状态、统计卡片显示、API 调用参数、数值正确性、表格数据、API 失败错误提示、期间切换 |
| Products.test.tsx | 11 | 搜索/筛选器渲染、新增按钮、商品数据表格、SKU/名称显示、停用按钮条件显示、状态标签、表格列字段 |
| Customers.test.tsx | 11 | 搜索/来源筛选器渲染、新增按钮、客户数据表格、名称/联系人/电话显示、来源中文映射、等级标签、空值占位符、表格列字段 |
| Orders.test.tsx | 11 | 搜索/状态筛选器渲染、新建订单按钮、订单数据表格、订单号/明细数显示、状态标签、金额货币符号、空创建时间占位符、表格列字段 |
| AuditLogs.test.tsx | 11 | 页面标题渲染、筛选器、审计表格、操作标签中文映射、资源类型中文映射、空值占位符、表格列字段、fetchAuditActions 挂载调用 |
| OrderDetail.test.tsx | 9 | 订单号显示、返回按钮、草稿编辑/确认按钮、状态标签、明细表格、收款记录、fetchOrder ID 调用、加载失败提示 |
| ProductForm.test.tsx | 12 | 新增标题、返回按钮、表单字段、必填校验、提交/取消按钮、图片上传、新增模式不加载商品 |
| CustomerForm.test.tsx | 12 | 新增标题、返回按钮、表单字段、必填校验、提交/取消按钮、来源/等级/跟进状态下拉、新增模式不加载客户 |
| OrderForm.test.tsx | 11 | 新建标题、返回按钮、客户选择字段、添加商品按钮、创建订单/取消按钮、备注字段、新建模式不加载订单 |
| CustomerDetail.test.tsx | 9 | 客户名称、返回按钮、编辑/删除按钮、等级标签、关联订单表格、fetchCustomer ID 调用、fetchOrders customer_id 筛选、加载失败提示 |
| ReportsCenter.test.tsx | 11 | 页面标题和周期选择器、五个标签页（销售概览/商品排行/客户排行/销售排行/库存预警）、统计卡片、趋势表格、商品排行数据、API 默认周期 30d 调用、库存预警标签、概览加载失败提示 |
| Payments.test.tsx | 12 | 页面标题、总记录数、收款数据行、金额格式化、收款方式中文、状态标签（正常/已冲正）、订单 ID 跳转、空状态 |
| Users.test.tsx | 14 | 用户数据行、用户名和显示名、角色标签、超级管理员标记、新建按钮、编辑按钮、空值占位符、新建弹窗打开 |
| Inventory.test.tsx | 11 | 页面标题、总记录数、库存变动行、变动类型标签（订单扣减/手动调整）、正数绿色 + 号、负数红色、关联类型、空状态 |

---

## 编写新测试指南

### 后端测试模板

```python
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.main import app
from app.api.deps import get_db
from app.core.security import hash_password
from app.models.user import User

TEST_DB_URL = "sqlite:///./test_xxx.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_original_override = None

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

def setup_module(module):
    global _original_override
    _original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        user = User(
            id=uuid.uuid4(),
            username="test_user",
            hashed_password=hash_password("testpass123"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_xxx.db"):
        os.remove("./test_xxx.db")
    if _original_override is not None:
        app.dependency_overrides[get_db] = _original_override
    elif get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

client = TestClient(app)
```

### 前端 API 测试模板

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

import { get, post } from '@/api/request'
import { fetchItems } from '@/api/items'

const mockGet = get as ReturnType<typeof vi.fn>

beforeEach(() => { vi.clearAllMocks() })

describe('items API', () => {
  it('fetchItems 调用 GET', async () => {
    mockGet.mockResolvedValue({ data: { items: [] } })
    await fetchItems()
    expect(mockGet).toHaveBeenCalledWith('/items', { params: { page: 1 } })
  })
})
```

### 注意事项

1. **后端测试用户必须是 is_superuser=True**，除非专门测试权限拒绝。
2. **使用 setup_module/teardown_module** 管理 `dependency_overrides`，不要用 conftest.py fixture。
3. **状态测试按编号排序**：test_01、test_02... 确保执行顺序。
4. **log_action 后抛异常前必须 db.commit()**，否则审计日志回滚。
5. **每个模块用独立的 SQLite 文件**，避免并发冲突。
6. **前端 API 测试 mock 路径使用 `@/api/request`**，不要 mock 底层 axios。
7. **ruff lint 必须在 `backend/` 目录下运行**，不是项目根目录。
