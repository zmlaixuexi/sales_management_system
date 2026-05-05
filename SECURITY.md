# 安全策略

## 支持的版本

当前仅支持以下版本的安全更新：

| 版本 | 支持状态 |
|---|---|
| main 分支最新提交 | :white_check_mark: 支持 |
| 其他版本 | :x: 不支持 |

## 报告安全漏洞

如果您发现安全漏洞，**请不要在公开的 GitHub Issue 中报告**。

请通过以下方式私下报告：

1. 使用 GitHub 的 [Security Advisories](../../security/advisories/new) 功能
2. 或发送邮件至项目维护者

报告时请包含以下信息：

* 漏洞的类型（如 SQL 注入、XSS、认证绕过等）
* 受影响的代码路径或 API 端点
* 复现步骤
* 潜在影响

我们将在 48 小时内确认收到报告，并在 7 个工作日内提供初步评估和修复计划。

## 已知安全措施

本项目已实施以下安全机制：

* JWT 认证 + 基于角色的访问控制（RBAC）
* API 速率限制和登录失败锁定
* SQL 参数化查询（SQLAlchemy ORM）
* XSS 防护（前端输入清理 + 后端 strip_html）
* CSV 注入防护
* CORS 白名单
* 安全响应头（CSP、X-Frame-Options 等）
* 请求体大小限制
* 密码强度校验 + bcrypt 哈希

## 生产环境部署注意事项

部署前请务必：

1. 修改 `.env` 中的 `JWT_SECRET_KEY`，不要使用默认值 `change-me`
2. 修改 `POSTGRES_PASSWORD`，不要使用默认值 `postgres`
3. 设置 `APP_ENV=production` 以启用生产安全策略
4. 配置正确的 `CORS_ORIGINS`，不要使用通配符
5. 运行 `deploy/pre-deploy-check.sh` 检查配置
