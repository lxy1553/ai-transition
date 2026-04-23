#!/bin/zsh
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <config-file> <message|morning|evening>" >&2
  exit 64
fi

CONFIG_FILE="$1"
shift
MODE_OR_MESSAGE="$*"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 66
fi

source "$CONFIG_FILE"

if [[ -z "${DINGTALK_WEBHOOK_URL:-}" ]]; then
  echo "DINGTALK_WEBHOOK_URL is missing in $CONFIG_FILE" >&2
  exit 78
fi

PLAN_FILE="${STUDY_PLAN_FILE:-}"
TODAY="${STUDY_PLAN_DATE_OVERRIDE:-$(${DATE_BIN:-/bin/date} '+%Y-%m-%d')}"

build_plan_message() {
  local mode="$1"

  if [[ -z "$PLAN_FILE" || ! -f "$PLAN_FILE" ]]; then
    echo "Study plan file not found: $PLAN_FILE" >&2
    exit 67
  fi

  local first_date
  local last_date
  first_date="$(/usr/bin/awk -F '\t' 'NR==2 {print $1}' "$PLAN_FILE")"
  last_date="$(/usr/bin/awk -F '\t' 'END {print $1}' "$PLAN_FILE")"

  if [[ "$TODAY" > "$last_date" ]]; then
    echo ""
    return 0
  fi

  local selected_date="$TODAY"
  if [[ "$TODAY" < "$first_date" ]]; then
    selected_date="$first_date"
  fi

  local row
  row="$(
    /usr/bin/awk -F '\t' -v date="$selected_date" '
      NR > 1 && $1 == date {
        print $1 "\t" $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6 "\t" $7 "\t" $8
      }
    ' "$PLAN_FILE"
  )"

  if [[ -z "$row" ]]; then
    echo ""
    return 0
  fi

  local study_date day week module focus actions deliverable review
  IFS=$'\t' read -r study_date day week module focus actions deliverable review <<< "$row"

  if [[ "$TODAY" < "$first_date" ]]; then
    if [[ "$mode" == "evening" ]]; then
      printf '%s\n%s\n%s\n%s\n%s' \
        "学习 第${day}天预告（${study_date}）" \
        "主题：${module}" \
        "重点：${focus}" \
        "任务：${actions}" \
        "产出：${deliverable}"
      return 0
    fi

    echo ""
    return 0
  fi

  if [[ "$mode" == "morning" ]]; then
    printf '%s\n%s\n%s\n%s\n%s\n%s' \
      "学习 第${day}天 / 第${week}周（${study_date}）" \
      "主题：${module}" \
      "重点：${focus}" \
      "任务：${actions}" \
      "产出：${deliverable}" \
      "执行要求：先学再写，今天必须有代码或文档产出。"
    return 0
  fi

  printf '%s\n%s\n%s\n%s\n%s' \
    "学习 第${day}天晚间复盘（${study_date}）" \
    "今天主题：${module}" \
    "完成标准：${deliverable}" \
    "复盘动作：${review}" \
    "如果没完成，补齐最小可交付物再休息。"
}

case "$MODE_OR_MESSAGE" in
  morning|evening)
    MESSAGE="$(build_plan_message "$MODE_OR_MESSAGE")"
    if [[ -z "$MESSAGE" ]]; then
      echo "[$TODAY] No scheduled study message to send"
      exit 0
    fi
    ;;
  *)
    MESSAGE="$MODE_OR_MESSAGE"
    ;;
esac

KEYWORD="${DINGTALK_KEYWORD:-}"
if [[ -n "$KEYWORD" && "$MESSAGE" != *"$KEYWORD"* ]]; then
  MESSAGE="$KEYWORD $MESSAGE"
fi

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '%s' "$value"
}

ESCAPED_MESSAGE="$(json_escape "$MESSAGE")"
PAYLOAD="{\"msgtype\":\"text\",\"text\":{\"content\":\"$ESCAPED_MESSAGE\"}}"

TIMESTAMP="$(/bin/date '+%Y-%m-%d %H:%M:%S %Z')"
echo "[$TIMESTAMP] Sending DingTalk message"
echo "$MESSAGE"

RESPONSE="$(
  /usr/bin/curl \
    --silent \
    --show-error \
    --max-time 15 \
    --request POST \
    --header 'Content-Type: application/json' \
    --data "$PAYLOAD" \
    "$DINGTALK_WEBHOOK_URL"
)"

echo "[$TIMESTAMP] Response: $RESPONSE"

if [[ "$RESPONSE" != *'"errcode":0'* ]]; then
  echo "DingTalk webhook returned an error" >&2
  exit 1
fi
