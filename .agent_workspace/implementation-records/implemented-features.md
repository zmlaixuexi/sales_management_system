# 已实现功能记录

本文件记录已经实现并验证过的功能。

## 功能编号：FEAT-20260430-02

功能名称：商品管理、文件上传和客户管理后端 API
所属模块：商品管理、文件管理、客户管理
关联任务编号：DB-PRODUCT-001 / DB-FILE-001 / BE-PRODUCT-001 / BE-FILE-001 / DB-CUSTOMER-001 / BE-CUSTOMER-001
实现日期：2026-04-30
实现 Agent：Claude
当前状态：已测试

### 实现范围

- 商品模型：Product、ProductCategory、File、ProductImage、ProductPriceHistory。
- 客户模型：Customer。
- 商品 CRUD API：列表（搜索/筛选/排序/分页）、创建（SKU 自动生成、默认分类、利润计算）、详情、编辑（价格变更记录）、软删除、停用、价格历史。
- 文件上传 API：图片上传（类型/大小校验）、文件信息查询、删除。
- 客户 CRUD API：列表（搜索/筛选/分页）、创建（手机号重复检测）、详情、编辑、软删除、归属转移。
- 静态文件服务（/uploads）。
- 数据库迁移和种子数据。

### 不包含范围

- 前端页面（FE-PRODUCT-001、FE-FILE-001、FE-CUSTOMER-001 待实现）。
- 操作日志记录。
- 细粒度权限校验（目前仅验证登录）。
- 数据范围权限（销售只能看本人客户）。

### 涉及文件

| 文件 | 变更说明 |
|---|---|
| backend/app/models/product.py | 新建：商品相关模型 |
| backend/app/models/customer.py | 新建：客户模型 |
| backend/app/api/v1/products.py | 新建：商品 CRUD API |
| backend/app/api/v1/files.py | 新建：文件上传 API |
| backend/app/api/v1/customers.py | 新建：客户 CRUD API |
| backend/app/services/file_service.py | 新建：文件上传服务 |
| backend/app/main.py | 更新：静态文件挂载 |
| backend/app/core/config.py | 更新：UPLOAD_DIR 默认值 |
| backend/alembic/env.py | 修复：导入模型 |
| backend/alembic/versions/6800eb76fb83_*.py | 新建：全部初始表迁移 |
| backend/alembic/versions/67fdb7b8db27_*.py | 新建：客户表迁移 |

### 数据库变更

迁移文件：
- 6800eb76fb83：全部初始表（users, roles, permissions, user_roles, role_permissions, product_categories, products, files, product_images, product_price_history）
- 67fdb7b8db27：客户表（customers）

### API 变更

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | /api/v1/products | 商品列表 | 登录 |
| POST | /api/v1/products | 新增商品 | 登录 |
| GET | /api/v1/products/{id} | 商品详情 | 登录 |
| PUT | /api/v1/products/{id} | 编辑商品 | 登录 |
| DELETE | /api/v1/products/{id} | 删除商品 | 登录 |
| POST | /api/v1/products/{id}/disable | 停用商品 | 登录 |
| GET | /api/v1/products/{id}/price-history | 价格历史 | 登录 |
| POST | /api/v1/files/images | 上传图片 | 登录 |
| GET | /api/v1/files/images/{id} | 获取图片信息 | 登录 |
| DELETE | /api/v1/files/images/{id} | 删除图片 | 登录 |
| GET | /api/v1/customers | 客户列表 | 登录 |
| POST | /api/v1/customers | 新增客户 | 登录 |
| GET | /api/v1/customers/{id} | 客户详情 | 登录 |
| PUT | /api/v1/customers/{id} | 编辑客户 | 登录 |
| DELETE | /api/v1/customers/{id} | 删除客户 | 登录 |
| POST | /api/v1/customers/{id}/transfer | 转移归属 | 登录 |

### 自动处理逻辑

- SKU 自动生成：SPU-YYYYMMDD-四位序号
- 默认分类：自动归入"未分类"
- 利润/毛利率自动计算：unit_profit = sale_price - cost_price，gross_margin = unit_profit / sale_price
- 价格变更自动记录

### 已执行测试

测试命令：`pytest tests/ -v`
测试结果：10/10 通过
API 实测：商品创建/列表/详情通过

### 已知限制

- 权限校验仅验证登录状态，未做角色/数据范围校验。
- 文件上传未做文件头校验（仅校验扩展名和 MIME）。
- 无缩略图生成。
- 客户数据范围权限未实现。

### 后续任务

- FE-PRODUCT-001：商品列表页和编辑页
- FE-FILE-001：图片上传交互
- FE-CUSTOMER-001：客户列表页和详情页
- 操作日志
- 权限和数据范围校验细化

---

## 功能编号：FEAT-20260429-001

功能名称：FastAPI 后端工程骨架
所属模块：后端基础设施
关联任务编号：BE-001、DB-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- FastAPI 应用入口，含 CORS 中间件、API 路由。
- 健康检查接口 GET /api/v1/health。
- 版本信息接口 GET /api/v1/version。
- 配置管理（pydantic-settings），支持环境变量。
- JWT 和密码工具（python-jose + bcrypt）。
- 数据库会话管理（SQLAlchemy 2.x sync session）。
- Alembic 迁移环境配置。
- 后端 Dockerfile。
- 测试基础设施（pytest + httpx）。

### 已执行测试

测试命令：pytest tests/test_health.py -v
测试结果：2/2 通过

---

## 功能编号：FEAT-20260429-002

功能名称：React + TypeScript + Vite 前端工程
所属模块：前端基础设施
关联任务编号：FE-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- Vite + React + TypeScript 脚手架。
- Ant Design、react-router-dom、axios 依赖。
- 基础布局（侧边栏导航）。
- API 请求层和类型定义。
- Vite 路径别名和 API 代理配置。

### 已执行测试

测试命令：cd frontend && npm run build
测试结果：构建成功

---

## 功能编号：FEAT-20260429-003

功能名称：Docker Compose 开发环境
所属模块：DevOps
关联任务编号：DEVOPS-001
实现日期：2026-04-29
实现 Agent：Claude Code
当前状态：已测试

### 实现范围

- Docker Compose 开发环境（postgres 17、backend、frontend）。
- 环境变量示例文件。
- 编辑器配置。

### 已执行测试

测试命令：docker compose up -d
测试结果：三服务全部运行，API 代理正常
