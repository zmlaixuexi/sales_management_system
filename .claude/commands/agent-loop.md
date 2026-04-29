启动或维护本仓库的 Claude 自动开发循环。

请按以下步骤执行：

1. 读取 `CLAUDE.md`、`.agent_workspace/README.md`、`.agent_workspace/handoff/active-session.md` 和 `.agent_workspace/tasks/backlog.md`。
2. 如果用户给了具体目标，把目标传给脚本的 `--task`。
3. 如果没有具体目标，从当前交接记录和 Backlog 继续。
4. 推荐命令：

```bash
scripts/claude-agent-loop.sh --max-rounds 50 --budget-usd 20
```

5. 结束后汇总 `.agent_workspace/loop/latest.log` 中的最终状态、已完成任务和下一步。
