# Day 54 - 实时指标查询 + 告警解释

这个项目用于 Day 54 的本地练习：模拟金融信贷实时指标查询和告警解释。

它不连接真实 Flink、Kafka 或告警平台，而是用本地数据演示生产 Agent 的实时工具调用约束：

- 实时指标必须带窗口；
- 查询前必须检查链路延迟；
- 延迟超阈值时不能给确定结论；
- 告警解释必须返回指标值、阈值、窗口、延迟和证据来源；
- 敏感明细导出必须安全阻断。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day54_realtime_metric_alert_explanation/main.py
```

运行后生成：

```text
projects/day54_realtime_metric_alert_explanation/output/realtime_metrics.json
projects/day54_realtime_metric_alert_explanation/output/realtime_alerts.json
projects/day54_realtime_metric_alert_explanation/output/realtime_query_cases.json
projects/day54_realtime_metric_alert_explanation/output/realtime_eval_results.json
projects/day54_realtime_metric_alert_explanation/output/realtime_metric_alert_report.md
```

## 生产映射

真实金融信贷 Agent 里，实时查询链路一般是：

```text
用户问题
-> 识别实时状态或告警解释意图
-> 检查窗口、产品、渠道等必要参数
-> 查询实时指标或告警平台
-> 检查事件时间、处理时间和链路延迟
-> 返回指标值、阈值、告警等级、证据和可用性状态
-> 写审计
```

实时链路的关键不是“查到一个数”，而是判断这个数在当前窗口内是否可信。
