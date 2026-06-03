# Day 48 - 实时仓库基础与 Agent 实时路由

这个项目用于 Day 48 的本地练习：把金融信贷实时事件、实时指标、告警和 Agent 实时路由连起来。

它不连接真实 Kafka、Flink 或数据库，而是用模拟目录说明生产边界。

## 练习目标

- 梳理实时事件、事件时间、处理时间、窗口和延迟。
- 建立信贷实时指标目录。
- 设计 Agent 查询实时状态和解释告警时的工具路线。
- 生成实时链路图、实时事件目录、实时指标目录和路由报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day48_realtime_warehouse_routing/main.py
```

运行后生成：

```text
projects/day48_realtime_warehouse_routing/output/realtime_event_catalog.json
projects/day48_realtime_warehouse_routing/output/realtime_metric_catalog.json
projects/day48_realtime_warehouse_routing/output/realtime_agent_routing_cases.json
projects/day48_realtime_warehouse_routing/output/realtime_warehouse_routing.mmd
projects/day48_realtime_warehouse_routing/output/realtime_warehouse_routing_report.md
```

## 生产映射

实时问题的标准路线：

```text
intent_classifier
-> realtime_router
-> realtime_metric_catalog / alert_query_tool
-> realtime_metric_tool
-> delay_checker
-> result_interpreter
-> audit_logger
```

关键边界：

- 近 5 分钟、实时、告警、事件流这类问题不能误走离线 SQL；
- 缺少窗口、业务线或策略维度时先澄清；
- 实时链路延迟超过阈值时返回异常或降级说明；
- 实时事件流里的敏感明细不能导出。
