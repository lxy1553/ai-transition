#!/bin/zsh
set -euo pipefail

# 这个脚本负责把钉钉学习提醒安装到 macOS LaunchAgents。
# 安装后系统会按 plist 里的时间自动调用发送脚本，减少每天手动提醒的成本。
# 它会复制脚本、学习计划和配置到运行目录，避免定时任务依赖当前仓库路径。

SCRIPT_DIR="${0:A:h}"
ROOT_DIR="${SCRIPT_DIR:h}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
RUNTIME_ROOT="$HOME/.codex/dingtalk-study"
USER_ID="$(id -u)"

/bin/mkdir -p "$RUNTIME_ROOT/logs"
/bin/mkdir -p "$LAUNCH_AGENTS_DIR"
/bin/chmod 700 "$RUNTIME_ROOT"
/bin/chmod 700 "$RUNTIME_ROOT/logs"

# 把运行所需文件复制到固定目录，launchd 后续只依赖这个目录，不依赖开发目录是否移动。
/usr/bin/install -m 755 "$ROOT_DIR/scripts/send_dingtalk_text.sh" "$RUNTIME_ROOT/send_dingtalk_text.sh"
/usr/bin/install -m 644 "$ROOT_DIR/data/ai_learning_plan_56_days.tsv" "$RUNTIME_ROOT/ai_learning_plan_56_days.tsv"

# webhook 是敏感配置，只写入运行目录的 env 文件，并设置 600 权限，避免被其他用户读取。
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
  # plist 描述定时任务本身，复制到 LaunchAgents 后 macOS 才能加载它。
  SRC="$ROOT_DIR/launchd/$plist_name"
  DST="$LAUNCH_AGENTS_DIR/$plist_name"
  /usr/bin/install -m 644 "$SRC" "$DST"
done

for label in \
  com.longfeiguo.dingtalk.study.morning \
  com.longfeiguo.dingtalk.study.evening
do
  # 先尝试卸载旧任务，避免重复 bootstrap 时失败。任务不存在时忽略错误。
  /bin/launchctl bootout "gui/$USER_ID/$label" >/dev/null 2>&1 || true
done

for plist_name in \
  com.longfeiguo.dingtalk.study.morning.plist \
  com.longfeiguo.dingtalk.study.evening.plist
do
  # 重新加载定时任务，让最新脚本和配置生效。
  /bin/launchctl bootstrap "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/$plist_name"
done

echo "Installed LaunchAgents:"
echo "  com.longfeiguo.dingtalk.study.morning"
echo "  com.longfeiguo.dingtalk.study.evening"
echo "Plists directory: $LAUNCH_AGENTS_DIR"
echo "Runtime directory: $RUNTIME_ROOT"
