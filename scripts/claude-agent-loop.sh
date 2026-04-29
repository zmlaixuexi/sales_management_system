#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$ROOT_DIR/.agent_workspace"
LOOP_DIR="$WORKSPACE_DIR/loop"
LOG_DIR="$LOOP_DIR/logs"
LATEST_LOG="$LOOP_DIR/latest.log"

TASK=""
MAX_ROUNDS=50
BUDGET_USD=""
MODEL=""
EFFORT="high"
PERMISSION_MODE="bypassPermissions"
CONTINUE_SESSION=0
AUTO_COMMIT=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage:
  scripts/claude-agent-loop.sh [options]

Options:
  --task TEXT                 Specific goal for the loop. Defaults to project backlog continuation.
  --max-rounds N              Maximum Claude rounds before stopping. Default: 50.
  --budget-usd N              Per-round Claude --max-budget-usd value.
  --model NAME                Claude model alias or full model name.
  --effort LEVEL              Claude effort: low, medium, high, xhigh, max. Default: high.
  --permission-mode MODE      Claude permission mode. Default: bypassPermissions.
  --continue-session          Add --continue after the first round.
  --auto-commit               Commit changes after rounds that report progress. Commit messages are Chinese.
  --dry-run                   Print the generated prompt and exit.
  -h, --help                  Show this help.

Examples:
  scripts/claude-agent-loop.sh --task "完成阶段 1 工程基础设施" --max-rounds 20 --budget-usd 10
  scripts/claude-agent-loop.sh --max-rounds 50 --budget-usd 20 --auto-commit
USAGE
}

die() {
  echo "error: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK="${2:-}"
      shift 2
      ;;
    --max-rounds)
      MAX_ROUNDS="${2:-}"
      shift 2
      ;;
    --budget-usd)
      BUDGET_USD="${2:-}"
      shift 2
      ;;
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --effort)
      EFFORT="${2:-}"
      shift 2
      ;;
    --permission-mode)
      PERMISSION_MODE="${2:-}"
      shift 2
      ;;
    --continue-session)
      CONTINUE_SESSION=1
      shift
      ;;
    --auto-commit)
      AUTO_COMMIT=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

[[ "$MAX_ROUNDS" =~ ^[0-9]+$ ]] || die "--max-rounds must be a positive integer"
[[ "$MAX_ROUNDS" -gt 0 ]] || die "--max-rounds must be greater than 0"
command -v claude >/dev/null 2>&1 || die "claude command not found"
[[ -d "$WORKSPACE_DIR" ]] || die ".agent_workspace not found"

if [[ "$AUTO_COMMIT" -eq 1 ]]; then
  existing_changes="$(cd "$ROOT_DIR" && git status --porcelain)"
  if [[ -n "$existing_changes" ]]; then
    die "--auto-commit requires a clean git worktree before the loop starts. Commit, stash, or run without --auto-commit."
  fi
fi

mkdir -p "$LOG_DIR"

build_prompt() {
  local round="$1"
  local goal="$TASK"
  if [[ -z "$goal" ]]; then
    goal="继续推进本仓库销售管理系统，从 active-session 和 Backlog 中选择下一步，直到 MVP 或当前可执行目标完成。"
  fi

  cat <<PROMPT
你是本仓库的 autonomous Claude Code agent。当前是自动循环第 ${round}/${MAX_ROUNDS} 轮。

目标：
${goal}

执行要求：
1. 先读取根目录 CLAUDE.md，并按其中顺序读取 .agent_workspace 的交接、backlog、实现记录、问题台账和重复问题台账。
2. 如果 active-session.md 有明确下一步，优先继续；否则从 docs/销售管理系统开发执行文档.md 第 15 节和第 20 节选择最高优先级、依赖已满足的未完成任务。
3. 本轮完成一个可验证任务或一个小型纵向切片。需要代码就直接修改，需要文档就直接更新。
4. 运行相关测试、构建、语法检查或启动检查；失败后先自行修复。确实无法运行时，在交接记录写明原因。
5. 更新 .agent_workspace/handoff/active-session.md、changelog.md、implementation-records/implemented-features.md、issues/issue-register.md；如果同类问题第二次出现，更新 recurring-issues.md。
6. 如果本轮执行 git commit，提交记录描述必须使用中文，推荐格式为“类型：简短说明”。
7. 如果任务完成且仍有下一步，最后输出 AGENT_LOOP_STATUS: CONTINUE。
8. 如果目标或 MVP Backlog 已全部完成，且测试和交接记录已更新，最后输出 AGENT_LOOP_STATUS: DONE。
9. 如果必须等待用户提供密钥、账号、产品决策或外部权限，记录阻塞原因，最后输出 AGENT_LOOP_STATUS: BLOCKED。

最后一行必须且只能是：
AGENT_LOOP_STATUS: CONTINUE
或
AGENT_LOOP_STATUS: DONE
或
AGENT_LOOP_STATUS: BLOCKED
PROMPT
}

run_claude_round() {
  local prompt_file="$1"
  local round="$2"
  local log_file="$3"
  local args=(-p --permission-mode "$PERMISSION_MODE" --effort "$EFFORT")

  if [[ -n "$MODEL" ]]; then
    args+=(--model "$MODEL")
  fi
  if [[ -n "$BUDGET_USD" ]]; then
    args+=(--max-budget-usd "$BUDGET_USD")
  fi
  if [[ "$CONTINUE_SESSION" -eq 1 && "$round" -gt 1 ]]; then
    args+=(--continue)
  fi

  (
    cd "$ROOT_DIR"
    claude "${args[@]}" < "$prompt_file"
  ) 2>&1 | tee "$log_file"
}

extract_status() {
  local log_file="$1"
  grep -Eo 'AGENT_LOOP_STATUS: (CONTINUE|DONE|BLOCKED)' "$log_file" | tail -n 1 | awk '{print $2}'
}

commit_if_requested() {
  local round="$1"
  [[ "$AUTO_COMMIT" -eq 1 ]] || return 0
  (
    cd "$ROOT_DIR"
    if [[ -n "$(git status --porcelain)" ]]; then
      git add -A
      git commit -m "自动循环：完成第 ${round} 轮开发推进"
    fi
  )
}

if [[ "$DRY_RUN" -eq 1 ]]; then
  build_prompt 1
  exit 0
fi

: > "$LATEST_LOG"
echo "Claude agent loop started at $(date -Is)" | tee -a "$LATEST_LOG"
echo "Root: $ROOT_DIR" | tee -a "$LATEST_LOG"
echo "Max rounds: $MAX_ROUNDS" | tee -a "$LATEST_LOG"

for round in $(seq 1 "$MAX_ROUNDS"); do
  prompt_file="$LOOP_DIR/prompt-round-${round}.md"
  log_file="$LOG_DIR/round-${round}-$(date +%Y%m%d-%H%M%S).log"

  build_prompt "$round" > "$prompt_file"
  echo "" | tee -a "$LATEST_LOG"
  echo "===== Round $round/$MAX_ROUNDS =====" | tee -a "$LATEST_LOG"

  if ! run_claude_round "$prompt_file" "$round" "$log_file"; then
    echo "Claude command failed in round $round; see $log_file" | tee -a "$LATEST_LOG"
  fi

  status="$(extract_status "$log_file" || true)"
  if [[ -z "$status" ]]; then
    status="CONTINUE"
    echo "No explicit loop status found; defaulting to CONTINUE." | tee -a "$LATEST_LOG"
  fi

  echo "Round $round status: $status" | tee -a "$LATEST_LOG"
  commit_if_requested "$round" | tee -a "$LATEST_LOG"

  case "$status" in
    DONE)
      echo "Claude agent loop completed." | tee -a "$LATEST_LOG"
      exit 0
      ;;
    BLOCKED)
      echo "Claude agent loop blocked. Read $log_file for the blocking question." | tee -a "$LATEST_LOG"
      exit 2
      ;;
    CONTINUE)
      ;;
  esac
done

echo "Claude agent loop stopped after reaching --max-rounds=$MAX_ROUNDS." | tee -a "$LATEST_LOG"
exit 3
