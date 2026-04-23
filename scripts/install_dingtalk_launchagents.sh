#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
ROOT_DIR="${SCRIPT_DIR:h}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
RUNTIME_ROOT="$HOME/.codex/dingtalk-study"
USER_ID="$(id -u)"

/bin/mkdir -p "$RUNTIME_ROOT/logs"
/bin/mkdir -p "$LAUNCH_AGENTS_DIR"
/bin/chmod 700 "$RUNTIME_ROOT"
/bin/chmod 700 "$RUNTIME_ROOT/logs"

/usr/bin/install -m 755 "$ROOT_DIR/scripts/send_dingtalk_text.sh" "$RUNTIME_ROOT/send_dingtalk_text.sh"
/usr/bin/install -m 644 "$ROOT_DIR/data/ai_learning_plan_56_days.tsv" "$RUNTIME_ROOT/ai_learning_plan_56_days.tsv"

source "$ROOT_DIR/config/dingtalk.env"
cat > "$RUNTIME_ROOT/dingtalk.env" <<EOF
DINGTALK_WEBHOOK_URL='${DINGTALK_WEBHOOK_URL}'
DINGTALK_KEYWORD='${DINGTALK_KEYWORD}'
STUDY_PLAN_FILE='${RUNTIME_ROOT}/ai_learning_plan_56_days.tsv'
EOF
/bin/chmod 600 "$RUNTIME_ROOT/dingtalk.env"

for plist_name in \
  com.longfeiguo.dingtalk.study.morning.plist \
  com.longfeiguo.dingtalk.study.evening.plist
do
  SRC="$ROOT_DIR/launchd/$plist_name"
  DST="$LAUNCH_AGENTS_DIR/$plist_name"
  /usr/bin/install -m 644 "$SRC" "$DST"
done

for label in \
  com.longfeiguo.dingtalk.study.morning \
  com.longfeiguo.dingtalk.study.evening
do
  /bin/launchctl bootout "gui/$USER_ID/$label" >/dev/null 2>&1 || true
done

for plist_name in \
  com.longfeiguo.dingtalk.study.morning.plist \
  com.longfeiguo.dingtalk.study.evening.plist
do
  /bin/launchctl bootstrap "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/$plist_name"
done

echo "Installed LaunchAgents:"
echo "  com.longfeiguo.dingtalk.study.morning"
echo "  com.longfeiguo.dingtalk.study.evening"
echo "Plists directory: $LAUNCH_AGENTS_DIR"
echo "Runtime directory: $RUNTIME_ROOT"
