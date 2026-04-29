# 测试文档

## 概览

| 指标 | 值 |
|---|---|
| 后端测试总数 | 51 |
| 测试文件 | 5 |
| 覆盖模块 | 认证、商品、客户、订单、库存、收款、报表、审计日志、数据导出 |
| 前端测试 | 暂无（后续补齐） |

## 运行测试

```bash
# 运行全部后端测试
cd backend
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_auth.py -v

# 运行指定测试类
pytest tests/test_integration.py::TestOrder -v

# 运行指定测试方法
pytest tests/test_integration.py::TestOrder::test_01_create_draft_order -v
```

## 测试架构

### 测试数据库

每个测试模块使用独立的 SQLite 文件数据库（非内存），在 `setup_module` 中创建、`teardown_module` 中销毁：

| 测试文件 | 数据库文件 | 说明 |
|---|---|---|
| test_auth.py | test.db | 非超级用户，测试 RBAC |
| test_integration.py | test_integration.db | 超级用户，完整业务流程 |
| test_audit_log.py | test_audit_log.db | 超级用户，审计日志验证 |
| test_export.py | test_export.db | 超级用户，CSV 导出 |
| test_health.py | （无） | 健康检查无需数据库 |

### 依赖注入覆盖

所有测试模块通过 `app.dependency_overrides[get_db]` 替换数据库依赖，teardown 时恢复原始覆盖：

```python
def setup_module(module):
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    os.remove("./test_xxx.db")
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]
```

### HTTP 客户端

使用 `fastapi.testclient.TestClient(app)`，同步调用，无需启动服务器。

### 认证方式

测试用户通过 API 登录获取 JWT Token，后续请求通过 `Authorization: Bearer <token>` 头传递。

### 状态共享

模块级全局变量（`_tokens`、`_product_id` 等）在测试间共享，测试按编号顺序执行（`test_01_`、`test_02_`、...）。

---

## 测试文件详解

### test_health.py（2 个测试）

健康检查和版本接口，无需认证。

| 测试 | 说明 |
|---|---|
| test_health_check | GET /health 返回 ok |
| test_version | GET /version 返回版本号 |

### test_auth.py（7 个测试）

认证模块，测试用户为非超级用户（is_superuser=False）。

| 测试 | 说明 |
|---|---|
| test_login_success | 正确用户名密码登录 |
| test_login_wrong_password | 错误密码返回 401 |
| test_login_nonexistent_user | 不存在用户返回 401 |
| test_get_me_authorized | 携带 Token 获取用户信息 |
| test_get_me_unauthorized | 无 Token 返回 401 |
| test_refresh_token | 刷新 Token |
| test_non_admin_forbidden | 非管理员访问 /users 被 403 |

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

| 测试 | 说明 |
|---|---|
| test_01_login_success_log | 登录成功日志 |
| test_02_login_failed_log | 登录失败日志 |
| test_03_product_logs | 商品创建/编辑/停用日志 |
| test_04_customer_logs | 客户创建/编辑日志 |
| test_05_order_logs | 订单创建/确认日志 |
| test_06_payment_log | 收款日志 |
| test_07_inventory_log | 库存调整日志 |
| test_08_filter_by_resource_type | 按资源类型筛选 |
| test_09_actions_list | 操作类型列表 |

### test_export.py（8 个测试）

CSV 数据导出验证。

| 测试 | 说明 |
|---|---|
| test_01_login_and_setup | 登录并准备测试数据 |
| test_02_export_products_csv | 导出商品 CSV |
| test_03_export_products_with_filter | 带筛选条件导出 |
| test_04_export_customers_csv | 导出客户 CSV |
| test_05_export_orders_csv | 导出订单 CSV |
| test_06_export_payments_csv | 导出收款 CSV |
| test_07_export_requires_auth | 导出需要认证 |
| test_08_export_empty_filter | 无匹配数据导出空表头 |

---

## 编写新测试指南

### 基本模板

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

### 注意事项

1. **测试用户必须是 is_superuser=True**，否则权限校验会拦截请求（除非专门测试权限拒绝）。
2. **使用 setup_module/teardown_module** 管理 `dependency_overrides`，不要用 conftest.py fixture。
3. **状态测试按编号排序**：test_01、test_02... 确保执行顺序。
4. **log_action 后抛异常前必须 db.commit()**，否则审计日志回滚。
5. **每个模块用独立的 SQLite 文件**，避免并发冲突。
