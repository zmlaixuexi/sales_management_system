# Changelog

## 2026-04-30

### 阶段 2：认证、用户、权限

- **BE-AUTH-001** 实现后端认证系统：
  - 创建 User/Role/Permission/UserRole/RolePermission 五张表的 SQLAlchemy 模型。
  - 实现登录、Token 刷新、退出、当前用户信息 API。
  - 实现用户列表和用户管理 API（含权限校验）。
  - 创建权限依赖注入（get_current_user、get_db）。
  - 创建种子数据脚本（管理员 admin/admin123、6 种角色、32 项权限）。
  - 后端测试 10/10 通过。
- **FE-AUTH-001** 实现前端认证系统：
  - 配置 Ant Design、react-router-dom、zustand、axios。
  - 实现登录页、受保护路由、主布局。
  - 创建 API 请求层和认证 store。
  - 前端构建成功。

## 2026-04-29

### 阶段 1：工程基础设施

- **BE-001** 初始化 FastAPI 后端工程骨架。
- **DB-001** 配置 Alembic 迁移环境。
- **FE-001** 初始化 React + TypeScript + Vite 前端工程。
- **DEVOPS-001** 创建 Docker Compose 开发环境、.env.example、.editorconfig。
