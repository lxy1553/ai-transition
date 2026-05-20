#!/bin/zsh
set -euo pipefail

# 自动把学习仓库同步到 GitHub。
# 设计成幂等脚本：没有变更就直接退出，有变更才提交和推送，方便 launchd 每天重复调用。

REPO_DIR="/Users/lxy/Documents/ai_transition"
REMOTE_NAME="${GIT_REMOTE_NAME:-origin}"
BRANCH_NAME="${GIT_BRANCH_NAME:-main}"
LOG_DIR="$REPO_DIR/logs"

/bin/mkdir -p "$LOG_DIR"
cd "$REPO_DIR"

timestamp() {
  /bin/date "+%Y-%m-%d %H:%M:%S"
}

log() {
  printf "[%s] %s\n" "$(timestamp)" "$1"
}

if ! /usr/bin/git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  log "Not a git repository: $REPO_DIR"
  exit 1
fi

# 先刷新远端引用，避免本地落后时直接 push 失败。
log "Fetching $REMOTE_NAME/$BRANCH_NAME"
/usr/bin/git fetch "$REMOTE_NAME" "$BRANCH_NAME"

# 只在没有未提交变更时自动 rebase，避免把用户正在改的文件卷进冲突处理。
if /usr/bin/git diff --quiet && /usr/bin/git diff --cached --quiet; then
  log "Working tree is clean before commit; rebasing latest remote changes"
  /usr/bin/git pull --rebase "$REMOTE_NAME" "$BRANCH_NAME"
fi

/usr/bin/git add -A

if /usr/bin/git diff --cached --quiet; then
  log "No local changes to commit"
  exit 0
fi

COMMIT_DATE="$(/bin/date "+%Y-%m-%d")"
COMMIT_MESSAGE="study: auto sync ${COMMIT_DATE}"

log "Creating commit: $COMMIT_MESSAGE"
/usr/bin/git commit -m "$COMMIT_MESSAGE"

log "Rebasing with latest remote before push"
/usr/bin/git pull --rebase "$REMOTE_NAME" "$BRANCH_NAME"

log "Pushing to $REMOTE_NAME/$BRANCH_NAME"
/usr/bin/git push "$REMOTE_NAME" "$BRANCH_NAME"

log "Auto sync completed"
