# 当前工作现场

最后更新时间：2026-04-30
当前阶段：安全加固
当前任务编号：ROUND-213
当前任务名称：main.py 延迟 import 修复
当前 Agent：Claude
任务状态：完成

## 最近完成

- Round 213：main.py lifespan 内延迟 import engine 改为顶层导入，后端 423/423
- Round 212：files.py get_image 延迟 import File 改为顶层导入，后端 423/423
- Round 211：reports.py __import__("decimal") 改为标准 import Decimal，后端 423/423
- Round 210：users.py 3 处 uuid.UUID 改为 parse_uuid_or_400 + 列表推导式优化，后端 423/423
- Round 209：收款导出添加数据范围过滤（非管理员只导出本人订单的收款），后端 423/423
- Round 208：商品列表 sort_by 参数白名单校验（防止任意模型属性访问），后端 423/423
- Round 207：parse_uuid_or_400 统一到 deps.py（消除 4 处重复定义，-50 行 +41 行），后端 423/423
- Round 206：扩展无效 UUID 防护至 products/orders/inventory（7 处 uuid.UUID 调用），后端 423/423
- Round 205：无效 UUID 请求体参数防护（500→400/404），get_or_404 + customers.py，后端 423/423
- Round 204：文档同步测试数至 545（422 后端 + 123 前端），README + testing.md
- Round 203：前端 authApi 新增 changePassword 接口调用 + 测试（+1），前端 123/123
- Round 202：ruff 添加 UP（pyupgrade）规则，修复 4 处现代化（UTC/Generator），后端 422/422
- Round 201：密码修改纯字母拒绝测试（+1），覆盖率恢复 99.81%，后端 422/422
- Round 200：实现记录同步至 Round 192-199（FEAT-58 至 FEAT-62）+ 里程碑总结更新至 Round 95-200
- Round 199：生产 nginx 镜像固定版本 1.27-alpine（避免 latest 不可预测变更）
- Round 198：CI 前端测试添加 --coverage 报告（与后端 --cov 对称）
- Round 197：新增密码修改接口 POST /auth/change-password（验证旧密码+强度校验+审计日志），后端 421/421
- Round 196：文档同步测试数至 540（418 后端 + 122 前端），README + testing.md 全量更新
- Round 195：CORS allow_methods/allow_headers 从通配符缩减为白名单，后端 418/418
- Round 194：密码强度校验（必须包含字母和数字），后端 418/418，ruff 0
- Round 193：ruff 扩展规则 B904/SIM/C4/PERF 修复（8 处异常链 + 2 处列表推导式 + 1 处三元表达式 + 1 处 Yoda 条件），pyproject.toml lint select 新增 B/SIM/C4/PERF，ruff 0，后端 415/415
- Round 192：CI 后端测试添加 --cov 覆盖率检查（阈值 70%），当前实际 99.81%
- Round 191：里程碑总结更新至 Round 95-190，make ci 全量质量验证通过
- Round 190：前端 Dockerfile 运行阶段固定 alpine:3.21（避免 latest 不可预测变更）
- Round 188：移除死代码 MainLayout（已被 AppLayout 取代），-226 行，前端 122/122
- Round 187：AppLayout 用户加载/导航/退出 + ProtectedRoute 重定向（+6），前端 128/128
- Round 185：ErrorBoundary 路由重置 + 返回首页按钮（+2），前端 117/117
- Round 184：冲正收款时关联订单已删除（+1），payments.py 100%，后端 415/415，覆盖率 99.81%
- Round 183：CSV 导入全路径 + 订单号回退 + 取消已删除商品（+11），99.76%，后端 414/414
- Round 182：新增 make ci 本地完整质量门禁 + 修复 ruff lint，后端 403/403
- Round 181：移除 Pydantic 已拦截的防御性死代码（-10 行），orders.py 99%，payments.py 98%，后端 403/403
- Round 180：商品 SKU 更新成功 + SKU 生成非数字回退（+2），products.py 95%，28 行未覆盖，后端 403/403
- Round 179：确认订单商品已删除 404（+1），orders.py 96%→97%，后端覆盖率 99%，401/401
- Round 178：非管理员收款列表数据范围过滤（+1），payments.py 95%→97%，后端 400/400
- Round 177：客户手机号更新 + 商品名称更新 + 创建指定分类（+3），后端 399/399，33 行未覆盖
- Round 176：速率限制窗口清理 + get_logger 单元测试（+2），ratelimit/logging 100%，后端 395/395
- Round 175：商品分类筛选/排序回退/成本价格式/分类更新（+4），products.py 94%，后端 393/393
- Round 174：文件上传校验单元测试（+4）— 扩展名/MIME/大小/正常，file_service 100%，后端 389/389
- Round 173：存储型 XSS 防护 — strip_html 输入消毒 + 5 个 schema 字段校验（+6 测试），385/385
- Round 172：商品价格变更记录 + 客户归属人 + 健康检查降级 + 用户权限（+6），98% 覆盖率，385/385
- Round 171：商品更新字段测试（+3）— 全字段更新/SKU 重复/成本价负数，products.py 90%，后端 374/374
- Round 170：nginx 静态资源安全响应头 — 修复 add_header 继承缺失导致 JS/CSS/图片缺少安全头
- Round 169：客户更新边界测试（+3）— 空名称/手机号重复/全字段更新，customers.py 96%，后端 371/371
- Round 168：订单筛选/边界测试（+5）— 客户筛选/停用商品/收款记录/更换客户/空明细，orders.py 96%，后端 368/368
- Round 167：审计日志筛选测试（+2）— actor_id/date_range 筛选，audit_logs 100%，后端 363/363
- Round 166：导出服务筛选测试（+10）— 商品/客户/订单/收款导出 keyword/status/date/customer/order 筛选覆盖，export_service 100%，后端 361/361
- Round 165：商品列表筛选/排序 + 创建校验测试（+5）— keyword/status/sort/空名称/错误价格，后端 351/351
- Round 164：check_owner_or_forbid 单元测试（+4）— 超管/view_all/所有者/403 分支覆盖，后端 346/346
- Round 163：OrderDetail 操作防重复 — actionLoading 统一管理确认/取消/收款/冲正的 loading 和防重复点击，前端 115/115
- Round 162：前端静默错误修复 + 429 重试测试 — Dashboard/AuditLogs 错误提示 + 拦截器 429 测试（+2），前端 115/115
- Round 161：收款接口对象级权限 — list_payments 数据范围过滤 + create/reverse 归属检查，后端 342/342
- Round 160：对象级权限 + 敏感字段泄露修复 — 7 个 API 文件修复，后端 342/342
- Round 159：X-Response-Time 响应头 + 测试 — request_log 中间件添加耗时头，后端 342/342
- Round 158：CI 数据库迁移一致性检查 + make db-check — PostgreSQL 服务容器 + alembic upgrade head && check
- Round 157：Makefile .PHONY 补全 + get_request_meta 单元测试（+3），后端 341/341
- Round 156：优雅关闭 — lifespan yield 后释放数据库连接池 + 关闭日志，后端 338/338
- Round 155：新增 .dockerignore — 后端和前端排除测试/缓存/IDE/环境文件，Docker 构建验证通过
- Round 154：导出服务辅助函数单元测试（+13）— _dec/_str/_dt CSV 格式化验证，后端 338/338
- Round 153：文档同步测试数至 438（325 后端 + 113 前端）+ testing.md 新增 7 个测试文件条目
- Round 152：ProtectedRoute 组件测试（+4）— 无 token 重定向/加载中/已认证渲染/fetchUser 失败，前端 113/113
- Round 151：JSON 日志格式器 + 审计异常处理测试（+5）— _JsonFormatter/log_action 容错，后端 325/325
- Round 150：商品利润计算函数单元测试（+6）— _calc_profit 纯函数验证，后端 320/320
- Round 149：GitHub Actions CI 工作流 + Makefile install 修正 — push/PR 自动 ruff+pytest+eslint+tsc+vitest+build
- Round 148：前端 vitest 覆盖率报告 + make coverage-frontend — API 层 87%/store 100%，前端 109/109
- Round 147：审计日志服务单元测试（+7）— _mask_sensitive 脱敏/model_to_dict，后端 314/314
- Round 146：pytest-cov 覆盖率报告 + make coverage — 93.87% 行覆盖率，307/307 通过
- Round 145：订单金额计算函数单元测试（+9）— _calc_order_totals/_prepare_item 纯函数验证，后端 307/307
- Round 144：deps.py 权限辅助函数单元测试（+6）— _get_user_permissions/has_permission，后端 298/298
- Round 143：列表页 joinedload 优化 — 商品/客户/订单列表消除 selectin 额外查询，292/292
- Round 142：NotFound 组件测试（+3）— 404 渲染/按钮/导航，前端 109/109
- Round 140：CSV 导入去重 N+1 优化 — 预加载 SKU/手机号集合替代逐行查询，292/292
- Round 139：库存扣减/回滚 N+1 优化 — _deduct/_restore 批量 FOR UPDATE IN 查询，292/292
- Round 138：订单明细校验 N+1 优化 — _validate_and_prepare_items 批量 IN 查询替代逐行 get_or_404，292/292
- Round 137：启动配置摘要日志 — env/pool/rate_limit/log 启动时记录，后端 292/292
- Round 136：前端构建消除 chunk 大小警告 — Ant Design 已最优拆分，build 零警告
- Round 135：Makefile 新增 make quality 命令 — lint + typecheck + test 一键质量检查
- Round 134：文档同步测试数至 398（292 后端 + 106 前端）+ testing.md 新增 pytest 标记分类表
- Round 133：CORS 来源验证测试 — 允许/拒绝 Origin 响应头检查（+2，292/292）
- Round 132：pytest 测试标记分类 — 8 个标记按文件名自动应用，支持 -m 选择性运行，290/290
- Round 131：后端 .env.example — 20 个可配置项分组注释，与前端对称
- Round 130：数据库连接池可配置 — pool_size / max_overflow / pool_recycle，生产环境默认 10/20/1800s，后端 290/290
- Round 129：全局未处理异常处理器 — Exception handler 捕获未处理异常返回一致 JSON，防泄露内部详情，后端 290/290
- Round 128：Makefile 新增 make typecheck 命令（前端 TypeScript 类型检查），验证通过
- Round 127：标准化 422 校验错误响应格式 — 新增 RequestValidationError 全局处理器，前端可正确提取校验消息
- Round 126：文档同步测试数至 395（289 后端 + 106 前端）+ README/testing.md 更新
- Round 125：提取 resp() 响应构造函数，11 个 API 文件 44 处迁移，净减 60 行，后端 289/289
- Round 124：移除未使用的 SuccessResponse / ErrorResponse schema，ruff 0 + 后端 289/289
- Round 123：后端 Dockerfile 以非 root 用户运行（appuser UID 999），Docker 构建和运行验证通过
- Round 122：请求 ID 中间件测试（+3）— 自动生成/透传/日志写入验证，后端 289/289
- Round 121：RequestIDMiddleware 全链路追踪 — X-Request-ID 透传/生成 + contextvars + 日志 + 审计关联
- Round 120：ErrorBoundary 移入 RouterProvider 内部，新增 resetKey（pathname）路由变化自动重置，前端 106/106
- Round 119：提取 useSubmit hook（loading 管理 + ref 防重锁 + 统一错误提示），3 个表单页迁移，5 个测试，前端 105/105
- Round 118：Pydantic field_validator 防御深度 — OrderItemInput.unit_price 非负 + PaymentCreate.amount 正数，6 个测试同步 400→422
- Round 117：新增 frontend/.env.example 和 CONTRIBUTING.md，完善开发者引导体验
- Round 116：文档同步测试数至 386（286 后端 + 100 前端）+ README/testing.md 订单负价测试条目更新
- Round 115：getApiErrorMessage 工具函数测试（+3），前端突破 100 大关（100/100），全量验证通过
- Round 114：修复 docker-compose.prod.yml nginx depends_on 混用 mapping/list 语法错误，dev/prod 配置均已验证通过
- Round 113：后端 Dockerfile 改为多阶段构建，builder 阶段编译依赖，runtime 仅含运行时库
- Round 112：提取 getApiErrorMessage 工具函数，消除 6 个页面 9 处重复错误处理，tsc/ESLint/97 测试/build 全通过
- Round 111：订单负价校验测试（+2），覆盖 create/update 负单价拒绝，后端 286/286
- Round 110：提取 _validate_and_prepare_items，修复 update_order 缺少负价校验 bug（-41 行 +21 行），284/284 通过
- Round 109：提取 get_or_404 辅助函数，消除 19 处重复查询模式（-94 行 +35 行），284/284 通过
- Round 108：文档同步测试数至 381（284 后端 + 97 前端）+ README/testing.md 补齐订单/收款/库存测试条目
- Round 107：库存调整 + 流水查询测试（+10），覆盖手工调整/增加/减少/归零/超量拒绝/零调整拒绝/流水列表筛选，后端 284/284
- Round 106：收款登记 + 冲正测试（+11），覆盖创建/部分收款→完成/超额/零金额/草稿不可收款/列表筛选/冲正/重复冲正，后端 274/274
- Round 105：订单 CRUD + 状态流转测试（+19），覆盖创建/详情/编辑/确认（库存扣减）/取消（库存回滚）/库存不足，后端 263/263
- Round 104：ESLint 清零 — usePaginatedList ref 更新移入 useEffect + 测试文件移除未用变量
- Round 103：前端错误消息路径修正（6 个页面 + 拦截器），修复后端 detail.message 无法正确展示的 bug
- Round 102：Makefile 新增 db-backup/db-restore 命令
- Round 101：前端类型修正，成本价/毛利率标记为可选字段，修复 ProductForm 潜在 NaN bug
- Round 100：文档同步测试数至 341（244+97）+ README/testing.md 补齐新测试文件条目
- Round 99（上轮）：库存流水类型筛选 + 客户列表筛选测试（+3，后端 244/244）
- Round 98（上轮）：客户/商品 CRUD 成功路径测试（+15，后端 241/241）
- Round 97（上轮）：用户管理 CRUD 测试（+10）+ role_ids UUID 转换 bug 修复（后端 226/226）
- Round 96：CSV 导入大小限制测试（+2，后端 216/216）
- Round 95：全量验证通过（214/214 + 97/97 + ruff 0 + tsc 0 + build 通过）

## 当前测试状态

- 后端：423/423 通过
- 前端：123/123 通过
- ruff：0 issues
- ESLint：0 warnings
- build：通过
- tsc：通过
- 后端覆盖率：99.81%

## 下一步第一动作

后端 99.81%（4 行不可测），前端 122/122。ruff 扩展规则已修复，密码强度校验+修改接口已添加，CORS 已收紧。建议继续安全加固或可观测性改进。

## 当前里程碑总结（Round 95-200）

- 后端测试：214 → 421（+207）
- 前端测试：97 → 122（+25）
- 总计 543 测试，全部通过
- 后端覆盖率：99.81%（421 测试，仅 deps.py get_db 4 行不可测）
- 代码质量：ruff 0（含 B904/SIM/C4/PERF 扩展规则）+ ESLint 0 + build 零警告 + tsc 通过 + 代码分割 + 列表页统一 hook + get_or_404 + resp() 响应函数 + useSubmit hook + ErrorBoundary 路由感知 + Pydantic schema 校验 + 死代码清除 + 死代码组件移除（MainLayout）
- 性能：10 个复合索引 + 3 个 N+1 查询修复（订单明细校验/库存扣减回滚/CSV 导入去重）
- 安全：权限码全量审计 + RBAC + 数据范围 + 速率限制 + 敏感字段 + LIKE 转义 + 安全响应头（含静态资源补全）+ Token 刷新校验 + JWT 密钥启动检查 + CSV 导入大小限制 + CORS 白名单（方法+头精确指定）+ XSS 输入消毒（strip_html）+ 密码强度校验（字母+数字）+ 密码修改接口
- 可观测性：健康检查 + degraded + 请求日志 + 慢请求警告 + 请求 ID 全链路追踪 + 启动配置摘要日志 + 全局未处理异常处理器 + X-Response-Time
- 部署：Docker Compose + Nginx + 备份恢复 + Makefile（ci/quality/typecheck/coverage/db-backup/restore）+ 环境变量完整同步 + 多阶段 Docker 构建 + 非 root 用户 + DB 连接池可配置 + GitHub Actions CI（含覆盖率）+ Dockerfile/nginx 版本固定
- 测试工程：pytest 8 类标记自动分类 + .env.example 前后端对称 + CONTRIBUTING.md + pytest-cov 覆盖率报告 99.81% + 前端 vitest 覆盖率 + CI 前后端覆盖率对称
- 文档：README + testing.md + database.md + architecture.md + api.md + deployment.md 全部完成

## 阻塞问题

暂无。

## 需要优先避免的重复问题

1-13 条（同前）

## 恢复检查清单

- [x] 已阅读 active-session
- [x] 已确认下一步第一动作
