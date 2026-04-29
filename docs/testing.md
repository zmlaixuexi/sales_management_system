# 测试文档

## 概览

| 指标 | 值 |
|---|---|
| 后端测试总数 | 244 |
| 后端测试文件 | 18 |
| 前端测试总数 | 97 |
| 前端测试文件 | 16 |
| 测试总计 | 341 |
| 覆盖模块 | 认证、商品、客户、订单、库存、收款、报表、审计日志、数据导出、批量导入、权限校验、速率限制、SQL 注入防护 |

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
| test_health.py | （无） | 健康检查无需数据库 |
| test_user_management.py | test_user_mgmt.db | 管理员，用户 CRUD |
| test_customer_crud.py | test_customer_crud.db | 管理员，客户详情/编辑/转移/删除 |
| test_product_crud.py | test_product_crud.db | 管理员，商品详情/删除 |

### 依赖注入覆盖

所有测试模块通过 `app.dependency_overrides[get_db]` 替换数据库依赖，teardown 时恢复原始覆盖。

### 认证方式

测试用户通过 API 登录获取 JWT Token，后续请求通过 `Authorization: Bearer <token>` 头传递。

### 测试执行顺序

`conftest.py` 确保速率限制测试（test_ratelimit.py）始终最后运行，避免影响其他测试。

---

## 后端测试文件详解

### test_health.py（6 个测试）

健康检查、版本接口、中间件验证和生产环境安全检查，无需认证。

| 测试 | 说明 |
|---|---|
| test_health_check | GET /health 返回 ok |
| test_version | GET /version 返回版本号 |
| test_security_headers | 安全响应头验证（CSP、X-Frame-Options 等） |
| test_request_log_records_api_calls | API 请求被请求日志中间件记录 |
| test_request_log_ignores_non_api | 非 API 路径不被记录 |
| test_production_env_rejects_default_secret | 生产环境 JWT 默认密钥拒绝启动 |

### test_auth.py（9 个测试）

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

### test_integration.py（24 个测试，7 个类）

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

### test_audit_log.py（9 个测试）

审计日志验证。每个测试先执行业务操作，再查询审计日志确认记录正确。

### test_export.py（18 个测试）

CSV 数据导出验证，包括基本导出、筛选、认证和 CSV 格式验证（BOM、表头顺序、字段数一致性、状态中文映射、数据值精确匹配）。

### test_file_upload.py（9 个测试）

图片上传、类型/大小校验、获取/删除、认证验证。

### test_permissions.py（9 个测试）

数据范围权限、敏感字段过滤、权限码拦截、导出数据范围过滤。

### test_edge_cases.py（27 个测试）

6 大业务模块异常路径：缺字段、负值、重复、404、状态转换、库存不足、伪造 Token。

### test_validation.py（20 个测试）

refresh_token 异常、价格/库存/名称校验、CSV 边界、用户列表。

### test_boundary.py（37 个测试）

认证边界、订单状态机、收款边界（草稿收款、超额、冲正回退）、用户管理、库存调整、流水类型筛选。

### test_reports_audit.py（22 个测试）

销售汇总（6 种 period）、趋势、排行、预警、审计日志查询/筛选/权限。

### test_product_import.py（9 个测试）

商品 CSV 批量导入：成功、SKU 自动生成、重复 SKU、空名称、非 CSV、认证、中文表头、大小限制。

### test_customer_import.py（9 个测试）

客户 CSV 批量导入：成功、手机号重复、批量内去重、空名称、非 CSV、认证、大小限制。

### test_ratelimit.py（3 个测试）

速率限制响应头验证、429 触发验证。

### test_sanitize.py（6 个测试）

`escape_like()` 函数特殊字符转义（%、_、\\）。

### test_user_management.py（10 个测试）

用户管理 CRUD：列表/搜索、创建（含重复用户名）、编辑、禁用切换、角色变更、403 权限校验。

### test_customer_crud.py（11 个测试）

客户 CRUD 成功路径：详情获取、编辑验证、归属转移、软删除验证、列表按来源/关键词筛选。

### test_product_crud.py（6 个测试）

商品 CRUD 成功路径：详情获取、软删除、删除后不可见、列表排除已删除。

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
| utils.test.ts | 8 | formatAmount / formatPercent 纯函数 |
| statusMaps.test.ts | 6 | 商品/客户/订单状态映射完整性 |

### 基础设施

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| client.test.ts | 3 | API 客户端 baseURL、token 附加、无 token |
| request.test.ts | 5 | get/post/put/del/upload 封装函数 |
| ErrorBoundary.test.tsx | 2 | 正常渲染 + 错误捕获 |
| usePaginatedList.test.ts | 8 | 初始加载、错误处理、筛选、分页切换、刷新 |
| client-interceptor.test.ts | 7 | 401 刷新、403/404/500 错误消息、网络错误、重试保护 |

### API 模块（全部 7 个 API 模块已覆盖）

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| products-api.test.ts | 8 | fetchProducts/fetchProduct/create/update/delete/disable/uploadImage/priceHistory |
| customers-api.test.ts | 7 | fetchCustomers/fetchCustomer/create/update/delete/transfer/import |
| orders-api.test.ts | 6 | fetchOrders/fetchOrder/create/update/confirm/cancel |
| payments-api.test.ts | 5 | fetchPayments/筛选/createPayment/备注/reversePayment |
| reports-api.test.ts | 6 | fetchSalesSummary/Trend/ProductRanking/InventoryWarning |
| auditLogs-api.test.ts | 5 | fetchAuditLogs/筛选/日期范围/数据解析/fetchAuditActions |
| auth-api.test.ts | 4 | login/refresh/logout/getMe 路径验证 |

### 状态管理和工具

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| auth-store.test.ts | 11 | login/logout/fetchUser/hasPermission/loading 状态 |
| downloadCsv.test.ts | 6 | 成功下载、查询参数、过滤、错误、文件名提取 |

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
