# 测试文档

## 概览

| 指标 | 值 |
|---|---|
| 后端测试总数 | 517 |
| 后端测试文件 | 30 |
| 前端测试总数 | 156 |
| 前端测试文件 | 23 |
| 测试总计 | 673 |
| 后端覆盖率 | 99.79% |
| 覆盖模块 | 认证、商品、客户、订单、库存、收款、报表（含客户/销售人员排行）、审计日志（含手机号/邮箱脱敏）、数据导出（含权限/数据范围/敏感字段边界）、批量导入（含负价格/非法格式/英文表头/批量内去重）、权限校验、速率限制、SQL 注入防护、XSS 防护、请求 ID 中间件、CORS 验证、日志格式器、金额计算、文件服务（含 FILE_TOO_LARGE/FILE_NOT_BOUND 错误码）、密码强度、订单操作日志、支付路径（含已取消/已完成订单拒绝、无权限 403）、派生销售字段、响应体 request_id、报表 period 参数校验、CSV 导入校验（含行数上限+XSS 消毒+commit 回滚）、客户 source/level 枚举校验、生产环境 OpenAPI 禁用、SQL 慢查询日志 |

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
| test_payment_crud.py | test_payment_crud.db | 管理员，收款登记/超额/冲正/列表筛选 |
| test_inventory_crud.py | test_inventory_crud.db | 管理员，库存调整/流水查询/筛选 |
| test_deps.py | （无） | 纯函数测试，权限辅助函数 |
| test_order_calc.py | （无） | 纯函数测试，订单金额计算 |
| test_product_calc.py | （无） | 纯函数测试，商品利润计算 |
| test_audit_service.py | （无） | 纯函数测试，审计脱敏/模型转换 |
| test_logging.py | （无） | 纯函数测试，JSON 日志格式器 |

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
| crud | CRUD 操作测试 | 146 |
| boundary | 边界值和异常路径 | 103 |
| security | 认证/权限/速率限制 | 54 |
| export | 导出功能 | 44 |
| import | 导入功能 | 42 |
| report | 报表和审计日志 | 56 |
| integration | 集成测试 | 44 |
| infra | 基础设施（健康检查/中间件/日志） | 23 |

---

## 后端测试文件详解

### test_health.py（17 个测试）

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

### test_auth.py（13 个测试）

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

### test_integration.py（27 个测试，8 个类）

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

### test_audit_log.py（9 个测试）

审计日志验证。每个测试先执行业务操作，再查询审计日志确认记录正确。

### test_export.py（31 个测试）

CSV 数据导出验证，包括基本导出、多维度筛选（keyword/status/date/customer/order）、认证和 CSV 格式验证（BOM、表头顺序、字段数一致性、状态中文映射、数据值精确匹配）、无权限用户 403、成本价字段按权限隐藏、数据范围过滤。

### test_file_upload.py（16 个测试）

图片上传、类型/大小校验（FILE_INVALID_TYPE/FILE_TOO_LARGE 独立错误码）、获取/删除、认证验证、已绑定商品图片 FILE_NOT_BOUND 拒绝、伪装扩展名拒绝。

### test_permissions.py（9 个测试）

数据范围权限、敏感字段过滤、权限码拦截、导出数据范围过滤。

### test_edge_cases.py（27 个测试）

6 大业务模块异常路径：缺字段、负值、重复、404、状态转换、库存不足、伪造 Token。

### test_validation.py（23 个测试）

refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表、密码强度校验。

### test_boundary.py（37 个测试）

认证边界、订单状态机、收款边界（草稿收款、超额、冲正回退）、用户管理、库存调整、流水类型筛选。

### test_reports_audit.py（28 个测试）

销售汇总（6 种 period）、趋势、排行、预警、审计日志查询/筛选/权限、客户排行（含数据范围过滤和利润可见性）、销售人员排行（含数据范围过滤和利润可见性）。

### test_product_import.py（17 个测试）

商品 CSV 批量导入：成功、SKU 自动生成、重复 SKU、空名称、非 CSV、认证、中文表头、大小限制、行数上限、XSS 消毒、commit 回滚失败、负价格拒绝、非法销售价/成本价格式、英文表头、批量内 SKU 重复。

### test_customer_import.py（16 个测试）

客户 CSV 批量导入：成功、手机号重复、批量内去重、空名称、非 CSV、认证、大小限制、行数上限、XSS 消毒、source/level 枚举校验、commit 回滚失败、英文表头、无电话号码可选。

### test_ratelimit.py（4 个测试）

速率限制响应头验证、429 触发验证、窗口清理。

### test_sanitize.py（12 个测试）

`escape_like()` 函数特殊字符转义（%、_、\\）、`strip_html()` XSS 防护（script 标签/事件属性/style 标签/嵌套标签/正常 HTML 保留）。

### test_user_management.py（16 个测试）

用户管理 CRUD：列表/搜索、创建（含重复用户名）、编辑、禁用切换、角色变更、编辑时无效角色 ID 返回 400、403 权限校验、分页参数、未认证 401、弱密码 422、创建时无效角色 ID 400。

### test_customer_crud.py（19 个测试）

客户 CRUD 成功路径：详情获取、编辑验证、归属转移、软删除验证、列表按来源/关键词筛选、手机号更新、CSV 导入编码/空表头。

### test_product_crud.py（30 个测试）

商品 CRUD 成功路径 + CSV 导入：详情获取、软删除、删除后不可见、列表排除已删除、分类筛选/排序、SKU 更新、CSV 导入（成功/编码错误/空表头/行错误/SKU 重复/大小限制）。

### test_order_crud.py（29 个测试）

订单 CRUD + 状态流转全生命周期：创建（正常/空明细/客户不存在/商品不存在/零数量/负价拒绝）、详情/404/列表/状态筛选/客户筛选、编辑草稿（修改明细+金额重算+负价拒绝）、确认（库存扣减验证）、取消（库存回滚/商品已删除跳过）、库存不足确认失败、订单号后缀回退。

### test_payment_crud.py（20 个测试）

收款登记 + 冲正：创建（部分收款→partially_paid、全额→completed）、超额收款、零金额、草稿不可收款、订单不存在、列表全量/按 order_id 筛选/非管理员数据范围过滤/分页、冲正/重复冲正/不存在/关联订单已删除、已取消订单收款拒绝、已完成订单收款拒绝、负数金额、无权限用户收款/冲正 403。路径已对齐规范文档 POST /sales-orders/{id}/payments。

### test_inventory_crud.py（15 个测试）

库存调整 + 流水查询：手工调整（增加/减少/归零）、零调整拒绝、超量扣减拒绝、商品不存在、流水列表/按 product_id 筛选/按 movement_type 筛选、字段完整性校验、无调整权限 403、无列表权限 403、已删除商品调整 404、流水分页、order_confirm 类型筛选。

### test_deps.py（10 个测试）

权限辅助函数单元测试：`_get_user_permissions` 多角色收集/空角色/跨角色去重，`has_permission` 超级用户/有权限/无权限，`check_owner_or_forbid` 超管/view_all/所有者/403。

### test_export_helpers.py（13 个测试）

CSV 导出辅助函数单元测试：`_dec` Decimal/None/零/负数，`_str` 字符串/None，`_dt` datetime/None/ISO 格式。

### test_file_service.py（4 个测试）

文件上传校验单元测试：扩展名白名单、MIME 类型、文件大小、正常通过。

### test_order_calc.py（10 个测试）

订单金额计算纯函数测试：`_calc_order_totals` 基本金额/零金额/空明细/毛利率精度/缺失字段，`_prepare_item` 默认价格/自定义价格/除零保护/快照字段/低于成本价阻止。

### test_product_calc.py（6 个测试）

商品利润计算纯函数测试：`_calc_profit` 基本利润/零售价除零保护/亏损/零利润/精度/高毛利率。

### test_audit_service.py（8 个测试）

审计服务内部函数测试：`_mask_sensitive` None/空字典/密码脱敏/token 脱敏/手机号脱敏/邮箱脱敏/无匹配，`model_to_dict` UUID 转字符串/None 跳过。

### test_logging.py（5 个测试）

日志模块测试：`_JsonFormatter` 基本 JSON/异常信息/extra_fields 合并/无异常字段，`log_action` 数据库失败返回 None。

### test_csv_import.py（9 个测试）

CSV 导入校验共享函数测试：文件扩展名验证、BOM 检测、UTF-8 编码校验、大小限制、空文件、仅有表头、缺少表头、非 CSV 扩展名、正常通过。

### test_slow_query.py（5 个测试）

SQL 慢查询日志测试：监听器注册（超过阈值时日志记录）、低于阈值不记录、禁用时不注册监听器、模拟慢查询完整日志路径（含 request_id 关联）、长 SQL 截断。

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
| utils.test.ts | 11 | formatAmount / formatPercent / getApiErrorMessage 纯函数 |
| statusMaps.test.ts | 6 | 商品/客户/订单状态映射完整性 |

### 基础设施

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| client.test.ts | 3 | API 客户端 baseURL、token 附加、无 token |
| request.test.ts | 5 | get/post/put/del/upload 封装函数 |
| ErrorBoundary.test.tsx | 5 | 正常渲染 + 错误捕获 + 重试恢复 + 路由变化重置 + 返回首页 |
| AppLayout.test.tsx | 6 | 用户加载/显示名称/角色、菜单导航、退出清除 Token、getMe 失败、用户名回退 |
| usePaginatedList.test.ts | 10 | 初始加载、错误处理、筛选、分页切换、刷新、空结果、_toastDisplayed 跳过 |
| useSubmit.test.ts | 6 | 成功调用/提交中状态/错误提示/Ant Design 校验静默/防重/_toastDisplayed 跳过 |
| client-interceptor.test.ts | 14 | 401 刷新、403/404/500 错误消息、网络错误、重试保护、429 重试、_toastDisplayed 标记、error.message 提取（新格式）、旧格式兼容、409 业务错误 |
| NotFound.test.tsx | 3 | 404 状态渲染/返回首页按钮/按钮点击导航 |
| ProtectedRoute.test.tsx | 5 | 无 token 重定向/加载中 Spin/已认证渲染子组件/fetchUser 失败/异步重定向 |

### API 模块（全部 7 个 API 模块已覆盖）

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| products-api.test.ts | 8 | fetchProducts/fetchProduct/create/update/delete/disable/uploadImage/priceHistory |
| customers-api.test.ts | 7 | fetchCustomers（含无参数）/fetchCustomer/create/update/delete/transfer |
| orders-api.test.ts | 6 | fetchOrders/fetchOrder/create/update/confirm/cancel |
| payments-api.test.ts | 5 | fetchPayments/筛选/createPayment/备注/reversePayment |
| reports-api.test.ts | 6 | fetchSalesSummary/Trend/ProductRanking/InventoryWarning |
| auditLogs-api.test.ts | 5 | fetchAuditLogs/筛选/日期范围/数据解析/fetchAuditActions |
| auth-api.test.ts | 5 | login/refresh/logout/getMe/changePassword 路径验证 |

### 状态管理和工具

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| auth-store.test.ts | 11 | login/logout/fetchUser/hasPermission/loading 状态 |
| downloadCsv.test.ts | 6 | 成功下载、查询参数、过滤、错误、文件名提取 |

### 页面组件

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| Dashboard.test.tsx | 8 | 标题/期间选择器渲染、loading 状态、统计卡片显示、API 调用参数、数值正确性、表格数据、API 失败错误提示、期间切换 |
| Products.test.tsx | 8 | 搜索/筛选器渲染、新增按钮、商品数据表格、SKU/名称显示、停用按钮条件显示、状态标签、表格列字段 |
| Customers.test.tsx | 8 | 搜索/来源筛选器渲染、新增按钮、客户数据表格、名称/联系人/电话显示、来源中文映射、等级标签、空值占位符、表格列字段 |

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
