#!/bin/zsh
set -euo pipefail

# 安装每日 GitHub 自动上传任务。
# macOS launchd 会在每天 23:30 调用 scripts/auto_git_push.sh。

SCRIPT_DIR="${0:A:h}"
ROOT_DIR="${SCRIPT_DIR:h}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.lxy.ai-transition.git-autopush.plist"
LABEL="com.lxy.ai-transition.git-autopush"
USER_ID="$(id -u)"

/bin/mkdir -p "$LAUNCH_AGENTS_DIR"
/bin/mkdir -p "$ROOT_DIR/logs"

/bin/chmod 755 "$ROOT_DIR/scripts/auto_git_push.sh"
/usr/bin/install -m 644 "$ROOT_DIR/launchd/$PLIST_NAME" "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

/bin/launchctl bootout "gui/$USER_ID/$LABEL" >/dev/null 2>&1 || true
/bin/launchctl bootstrap "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "Installed LaunchAgent: $LABEL"
echo "Schedule: every day at 23:30"
echo "Log: $ROOT_DIR/logs/git-autopush.log"
