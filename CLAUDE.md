# Claude 项目工作规则

本项目是销售管理系统。Claude 在本仓库工作时，必须把 `.agent_workspace/` 作为连续开发入口，同时以代码现状和 `docs/销售管理系统开发执行文档.md` 的验收标准校验真实状态。

## 开始前必读

每次开始任务前按顺序读取：

1. `.agent_workspace/handoff/active-session.md`
2. `.agent_workspace/tasks/backlog.md`
3. `.agent_workspace/implementation-records/implemented-features.md`
4. `.agent_workspace/issues/recurring-issues.md`
5. `.agent_workspace/issues/issue-register.md`
6. `.agent_workspace/changelog.md`
7. `docs/销售管理系统开发执行文档.md`

如果用户只说“继续”“开始任务”“恢复任务”或由自动循环脚本启动，优先继续 `active-session.md` 中的下一步第一动作；如果没有正在进行的任务，则从阶段路线图和首批 Backlog 中选择最高优先级、依赖已满足的未完成任务。

如果 `.agent_workspace/` 记录与开发文档 Definition of Done 或代码现状冲突，必须先修正状态记录，再继续开发。不能只因为测试通过或功能主流程可运行，就把阶段标记为严格完成。

## 自动执行规则

- 尽量自主完成任务，不因为可合理假设的小问题打断用户。
- 每轮聚焦一个可验证的任务或一个小型纵向切片，避免同时改太多不相关模块。
- 修改代码后运行相关测试、构建或启动检查；失败时先自行修复。
- 注释和用户可见文案使用中文。
- 如果执行 `git commit`，提交记录描述必须使用中文，推荐格式为 `类型：简短说明`，例如 `工程：初始化后端服务骨架`。
- 金额、权限、订单状态、库存、迁移相关逻辑必须保持后端为准。
- 不删除或覆盖 `.agent_workspace/` 中已有记录，只追加或按现状更新。
- 不要回滚用户或其他 agent 的无关改动。

## 每轮结束必须更新

根据实际进展更新：

- `.agent_workspace/handoff/active-session.md`
- `.agent_workspace/changelog.md`
- `.agent_workspace/implementation-records/implemented-features.md`
- `.agent_workspace/issues/issue-register.md`
- `.agent_workspace/issues/recurring-issues.md`

阶段完成时还要更新测试报告，路径按执行文档第 17 节要求。

## 自动循环输出协议

当由 `scripts/claude-agent-loop.sh` 启动时，最终回复最后一行必须包含且只包含以下三种之一：

```text
AGENT_LOOP_STATUS: CONTINUE
AGENT_LOOP_STATUS: DONE
AGENT_LOOP_STATUS: BLOCKED
```

含义：

- `CONTINUE`：本轮有进展，但还有下一步任务，循环可以继续。
- `DONE`：当前目标或 MVP Backlog 已全部完成，并且验证与交接记录已更新。
- `BLOCKED`：需要用户提供账号、密钥、产品决策、外部服务或无法安全假设的信息。

如果脚本启用了 `--keep-going`，即使 MVP 已完成也继续做后续扩展 Backlog、测试补强、代码质量、异常路径、文档完善、安全加固、可观测性和部署体验；除非遇到必须用户决策的问题，否则不要用 `DONE` 停止循环。
