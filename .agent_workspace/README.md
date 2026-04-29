# Agent 协作入口

这个目录用于保证项目开发可以被连续接手。任何 agent 在开始工作前，必须先阅读：

1. `handoff/active-session.md`
2. `tasks/backlog.md`
3. `implementation-records/implemented-features.md`
4. `issues/recurring-issues.md`
5. `issues/issue-register.md`
6. `changelog.md`
7. `../docs/销售管理系统开发执行文档.md`
8. `../CLAUDE.md`

当用户发送“继续”“开始任务”“恢复任务”时，优先以 `handoff/active-session.md` 作为恢复现场。

## 状态判断规则

- `docs/销售管理系统开发执行文档.md` 是需求、验收标准和 Definition of Done 的最高依据。
- `.agent_workspace/tasks/backlog.md` 是执行状态索引，但不能替代开发文档的验收标准。
- `implementation-records/implemented-features.md` 中的“已知限制”必须视为未完成风险，不能因为功能主流程通过测试就忽略。
- 开始开发前必须先执行 `git status --short`，确认是否存在其他 agent 或用户留下的未提交改动。
- 如果 backlog、handoff、实现记录、代码现状互相矛盾，应以“代码现状 + 开发文档 DoD”为准，并先修正文档状态再继续开发。

## 当前重要提醒

截至 2026-04-30，MVP 主业务链路和若干扩展功能已经实现并通过现有测试，但严格对照开发文档仍存在 P0/P1 缺口：权限细化、数据范围、敏感字段控制、生产部署交付物、阶段测试报告和 API/数据库/测试文档尚未全部完成。
