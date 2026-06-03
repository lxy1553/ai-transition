# 运维与故障排查

## 数据质量错误

现象：`data_quality_report.md` 出现错误。

处理：

1. 检查 `app_id`、`customer_id`、`dt` 是否缺失。
2. 检查 `app_id` 或 `event_id` 是否重复。
3. 检查 `overdue_days` 是否为负数。
4. 修复源数据后重新运行 `--run-all`。

## Agent 返回权限阻断

现象：`final_status=safely_blocked`。

处理：

1. 查看用户角色是否有对应业务域权限。
2. 检查问题是否包含手机号、身份证、导出、客户明细等敏感词。
3. 如果确实需要明细，走安全审批和脱敏流程。

## 实时告警没有输出

现象：`realtime_alerts.json` 为空。

处理：

1. 检查 `data/realtime/risk_events.jsonl` 是否有 high 风险事件。
2. 检查同一分钟同一事件类型是否达到告警阈值。
3. 检查 `rt_risk_minute_metrics` 是否成功写入。

## 评测失败

现象：`evaluation_report.md` 通过率低于预期。

处理：

1. 看失败原因是 status、route、citation 还是 SQL 暴露。
2. 如果是 route 错误，检查 `answer_question` 的意图判断顺序。
3. 如果是 citation 缺失，检查指标口径和实时回答是否返回 citations。
4. 如果是 SQL 暴露，检查角色的 `can_view_sql`。

## 审计缺失

现象：`audit_log.jsonl` 没有记录。

处理：

1. 确认 Agent 问答确实经过 `answer_question`。
2. 确认 `output/` 目录可写。
3. 如果 SQLite 审计表还没初始化，先运行 `--run-all`。
