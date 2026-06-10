# Day 55 - 日报 + 实时告警 Agent

这个项目用于 Day 55 的本地练习：把离线日报指标、实时告警、指标口径和审计记录组合成一个
金融信贷日报 + 告警摘要 Agent。

它不调用真实大模型，也不连接真实数据平台。
脚本用本地 JSON 数据和规则编排演示生产 Agent 的多工具链路：

- 离线日报工具读取昨日经营指标；
- 实时告警工具读取近 1 小时告警；
- 指标口径工具解释指标含义；
- 结果解释层合成日报摘要；
- 审计工具记录每一步调用。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day55_daily_report_realtime_alert_agent/main.py
```

运行后生成：

```text
projects/day55_daily_report_realtime_alert_agent/output/daily_metrics.json
projects/day55_daily_report_realtime_alert_agent/output/realtime_alerts.json
projects/day55_daily_report_realtime_alert_agent/output/agent_audit_log.jsonl
projects/day55_daily_report_realtime_alert_agent/output/daily_alert_agent_result.json
projects/day55_daily_report_realtime_alert_agent/output/daily_alert_agent_report.md
```

## 生产映射

真实金融信贷数据 Agent 的日报/告警摘要链路一般是：

```text
用户请求日报摘要
-> 识别为日报 + 实时告警综合意图
-> 查离线日报 ADS 指标
-> 查近 1 小时实时告警
-> 查指标字典解释关键指标
-> 合成摘要、风险提示和建议排查项
-> 写审计记录
```

关键边界：Agent 可以解释查到的指标和告警证据，但不能编造根因；
涉及手机号、身份证号、客户名单时必须阻断。
