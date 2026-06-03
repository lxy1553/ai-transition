# Day 47 - 离线仓库分层与 Agent 离线路由

这个项目用于 Day 47 的本地练习：把金融信贷离线仓库的 ODS、DWD、DWS、ADS 分层，
和 Agent 查询离线指标时的工具路线连起来。

它不连接真实数据库，而是用模拟表结构和模拟用户问题说明生产边界。

## 练习目标

- 梳理信贷离线仓库四层：ODS、DWD、DWS、ADS。
- 明确每一层的粒度、权限风险和 Agent 查询入口。
- 设计 Agent 查询离线指标时的工具路线。
- 生成分层表清单、路由样例、Mermaid 分层图和 Markdown 报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day47_offline_warehouse_routing/main.py
```

运行后生成：

```text
projects/day47_offline_warehouse_routing/output/offline_layer_catalog.json
projects/day47_offline_warehouse_routing/output/offline_agent_routing_cases.json
projects/day47_offline_warehouse_routing/output/offline_warehouse_layering.mmd
projects/day47_offline_warehouse_routing/output/offline_warehouse_routing_report.md
```

## 生产映射

真实金融信贷 Agent 查询离线指标时，不能直接把用户问题交给模型生成 SQL。

更稳的路线是：

```text
intent_classifier
-> offline_layer_router
-> schema_catalog
-> offline_sql_generator
-> sql_validator
-> offline_query_executor
-> result_interpreter
-> audit_logger
```

关键边界：

- 总览指标优先走 ADS；
- 维度趋势优先走 DWS；
- 明细查询必须先过权限校验；
- ODS 默认不作为 Agent 普通查询入口；
- SQL 必须检查分区、limit、只读、敏感字段和扫描成本。
