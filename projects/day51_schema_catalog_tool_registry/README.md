# Day 51 - Schema Catalog + 工具注册表

这个项目用于 Day 51 的本地练习：把金融信贷离线表、实时指标和血缘入口整理成
Schema Catalog，再把 Agent 能调用的工具整理成工具注册表。

它不连接真实数据库，也不调用真实大模型。
今天重点是：Agent 不能只靠自然语言描述决定查什么表、调用什么工具，
而要先读取 Catalog 和工具注册表，确认表字段、权限、分区、窗口、前置条件和风险等级。

## 练习目标

- 建立信贷离线表和实时指标的 Schema Catalog。
- 为每张表写清表层级、粒度、分区字段、时间字段、权限标签和敏感字段。
- 建立 Agent 工具注册表，写清工具用途、输入参数、前置条件、风险等级和失败处理。
- 用样例问题验证工具路由是否符合 Catalog 约束。
- 生成 Catalog、工具注册表、路由样例、校验结果和 Markdown 报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day51_schema_catalog_tool_registry/main.py
```

运行后生成：

```text
projects/day51_schema_catalog_tool_registry/output/schema_catalog.json
projects/day51_schema_catalog_tool_registry/output/tool_registry.json
projects/day51_schema_catalog_tool_registry/output/routing_cases.json
projects/day51_schema_catalog_tool_registry/output/routing_eval_results.json
projects/day51_schema_catalog_tool_registry/output/schema_catalog_tool_registry_report.md
```

## 生产映射

真实金融信贷 Agent 里，Schema Catalog 和工具注册表通常是工具调用前的确定性约束。

```text
用户问题
-> 识别主题域和意图
-> 读取 Schema Catalog / Metric Catalog / Tool Registry
-> 检查前置条件、权限、分区、窗口和风险等级
-> 选择 RAG / NL2SQL / 实时指标 / 血缘 / 安全阻断工具
-> 执行并写审计
```

Catalog 解决“有哪些表字段能查、应该怎么查”的问题。
工具注册表解决“有哪些工具能调用、调用前必须满足什么条件”的问题。
两者一起约束 Agent，才能减少编造字段、越权查询、漏分区、实时窗口缺失和错误工具调用。
