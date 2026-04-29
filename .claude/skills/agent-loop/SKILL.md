---
name: agent-loop
description: Use when the user wants Claude Code to work autonomously across repeated coding rounds until a project task, backlog, or MVP is complete, using .agent_workspace handoff files, tests, progress logs, and the scripts/claude-agent-loop.sh harness.
---

# Agent Loop

Use this skill to run or maintain the autonomous Claude work loop for this repository.

## Workflow

1. Read `CLAUDE.md` and `.agent_workspace/README.md`.
2. Inspect `.agent_workspace/handoff/active-session.md` and `.agent_workspace/tasks/backlog.md`.
3. Start the external loop when the user wants hands-off execution:

```bash
scripts/claude-agent-loop.sh --max-rounds 50 --budget-usd 20
```

For a specific goal:

```bash
scripts/claude-agent-loop.sh --task "完成阶段 1 工程基础设施" --max-rounds 20 --budget-usd 10
```

For unattended execution with automatic Chinese git commit messages, start from a clean worktree and use:

```bash
scripts/claude-agent-loop.sh --task "完成阶段 1 工程基础设施" --max-rounds 999999 --budget-usd 10 --continue-session --auto-commit
```

4. Watch `.agent_workspace/loop/latest.log` and `.agent_workspace/handoff/active-session.md`.
5. If the loop stops with `BLOCKED`, read the last log and ask the user only for the missing decision or credential.

## Loop Contract

Each round must:

- Continue from `.agent_workspace/handoff/active-session.md`.
- Pick one high-priority unfinished task if no active task exists.
- Implement, test, and fix failures.
- Update handoff, changelog, implementation records, and issue records.
- Use Chinese commit messages for any `git commit`.
- End with `AGENT_LOOP_STATUS: CONTINUE`, `DONE`, or `BLOCKED`.

Prefer bounded rounds over one huge prompt. The harness provides persistence through files and logs, not by relying on one never-ending model response.
