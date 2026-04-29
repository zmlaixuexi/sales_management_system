# 当前工作现场

最后更新时间：2026-04-30
当前阶段：阶段 3，商品与客户（后端 API 已完成，前端页面待实现）
当前任务编号：BE-PRODUCT-001 / BE-FILE-001 / BE-CUSTOMER-001
当前任务名称：商品、文件上传、客户管理后端 API
当前 Agent：Claude
任务状态：后端已完成，前端页面待实现

## 本次目标

完成阶段 3 后端 API：商品 CRUD、文件上传、客户管理。同时补全前端基础结构。

## 最近完成

- 创建 Product/ProductCategory/File/ProductImage/ProductPriceHistory/Customer 六个 SQLAlchemy 模型。
- 生成并执行两条 Alembic 迁移（全部初始表 + 客户表），数据库共 12 张表。
- 修复 Alembic env.py 未导入模型导致自动生成空迁移的问题。
- 实现文件上传 API（POST /files/images），含类型/大小校验和本地存储。
- 实现商品 CRUD API（列表/创建/详情/编辑/删除/停用/价格历史），含 SKU 自动生成、利润/毛利率计算。
- 实现客户 CRUD API（列表/创建/详情/编辑/删除/转移归属），含手机号重复检测。
- 静态文件服务（/uploads）挂载到 FastAPI。
- 修复配置：UPLOAD_DIR 默认值从绝对路径改为相对于 backend 的路径。
- 前端：安装 Ant Design / react-router-dom / axios / zustand / dayjs。
- 前端：创建 API 请求层、类型定义、工具函数、404 页面、侧边栏布局。
- 前端：配置 Vite 路径别名 @/、API 代理（本地 + Docker）、TypeScript 路径别名。
- 修复 Docker 前端 API 代理 502（使用 VITE_PROXY_TARGET + Docker 服务名 backend:8000）。
- 后端测试 10/10 通过。
- 商品创建 API 实测通过：自动生成 SKU、默认分类、利润指标正确。
- 已执行种子数据：管理员 admin/admin123、6 角色、32 权限、默认分类。

## 当前正在做

阶段 3 后端 API 全部完成。前端页面（FE-PRODUCT-001 / FE-FILE-001 / FE-CUSTOMER-001）待下一轮实现。

## 下一步第一动作

实现阶段 3 前端页面：
1. 在 `frontend/src/pages/Products.tsx` 实现商品列表页（Ant Design Table + 搜索/筛选/分页）。
2. 创建 `frontend/src/pages/ProductForm.tsx` 实现商品新增/编辑页（4 必填字段 + 折叠高级字段）。
3. 在 `frontend/src/pages/Customers.tsx` 实现客户列表页。
4. 创建 `frontend/src/pages/CustomerForm.tsx` 实现客户新增/编辑页。
5. 在 `frontend/src/api/` 创建 products.ts 和 customers.ts API 调用。
6. 更新路由配置添加商品和客户页面路由。

## 涉及文件

| 文件 | 状态 | 说明 |
|---|---|---|
| backend/app/models/product.py | 新建 | 商品、分类、文件、图片、价格历史模型 |
| backend/app/models/customer.py | 新建 | 客户模型 |
| backend/app/api/v1/products.py | 新建 | 商品 CRUD API |
| backend/app/api/v1/files.py | 新建 | 文件上传 API |
| backend/app/api/v1/customers.py | 新建 | 客户 CRUD API |
| backend/app/services/file_service.py | 新建 | 文件上传服务 |
| backend/app/api/v1/router.py | 已更新 | 注册新路由 |
| backend/app/main.py | 已更新 | 添加静态文件挂载 |
| backend/app/core/config.py | 已更新 | UPLOAD_DIR 默认值改为相对路径 |
| backend/app/db/session.py | 已验证 | 数据库会话 |
| backend/alembic/env.py | 已修复 | 导入所有模型 |
| backend/alembic/versions/6800eb76fb83_*.py | 新建 | 全部初始表迁移 |
| backend/alembic/versions/67fdb7b8db27_*.py | 新建 | 客户表迁移 |
| frontend/vite.config.ts | 已更新 | 路径别名 + API 代理 |
| frontend/tsconfig.app.json | 已更新 | 路径别名 |
| frontend/src/routes/index.tsx | 已更新 | 路由配置 |
| frontend/src/routes/AppLayout.tsx | 新建 | Ant Design 侧边栏布局 |
| frontend/src/api/request.ts | 新建 | Axios 请求封装 |
| frontend/src/types/index.ts | 新建 | TypeScript 类型定义 |
| frontend/src/utils/index.ts | 新建 | 金额/百分比格式化 |
| deploy/docker-compose.dev.yml | 已更新 | VITE_PROXY_TARGET |

## 已执行命令

| 命令 | 结果 | 备注 |
|---|---|---|
| pytest tests/ -v | 10/10 通过 | 健康检查 + 认证测试 |
| npm run build | 通过 | 前端构建成功 |
| docker compose up -d | 通过 | 三服务全部运行 |
| curl POST /products | 通过 | 商品创建成功，SKU 自动生成 |
| curl GET /products | 通过 | 商品列表返回正确 |
| curl GET /products/{id} | 通过 | 商品详情返回正确 |
| alembic upgrade head | 通过 | 12 张表已创建 |
| seed_all() | 通过 | 管理员+角色+权限+默认分类 |

## 未完成事项

- FE-PRODUCT-001：商品列表页和编辑页前端实现。
- FE-FILE-001：商品图片上传交互。
- FE-CUSTOMER-001：客户列表页和详情页前端实现。
- 操作日志记录（阶段 3 的通用功能）。
- 权限校验细化（目前仅 admin 角色）。

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1. passlib 与 bcrypt 5.x 不兼容 → 使用 bcrypt 直接调用。
2. JWT 存储用户 ID 是 string → 查询时需 uuid.UUID(user_id) 转换。
3. Alembic env.py 必须导入所有模型 → 否则自动生成空迁移。

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已阅读任务文件
- [x] 已阅读实现记录
- [x] 已阅读重复问题记录
- [x] 已确认下一步第一动作
