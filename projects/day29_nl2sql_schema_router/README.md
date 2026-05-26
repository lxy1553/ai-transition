# Day 29 - NL2SQL Schema Router

这个项目用于练习 NL2SQL 的第一步：Schema 准备和问题类型分类。

它不会直接生成 SQL。
它先判断用户问题属于哪类查询，再根据本地 `schema_catalog.json` 推荐候选表、候选指标、候选维度和时间字段，
同时识别敏感查询和权限风险。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day29_nl2sql_schema_router/main.py
```

## 输出文件

```text
projects/day29_nl2sql_schema_router/output/schema_routing_results.json
projects/day29_nl2sql_schema_router/output/schema_routing_report.md
```

## 生产映射

生产级 NL2SQL 不能直接让模型自由生成 SQL。
更稳的方式是先做 schema 路由和问题分类，再把候选表字段、指标口径、权限规则和 SQL 约束交给生成环节。

这样可以减少模型编造字段、误选表、漏分区、越权查询和扫描大表的风险。

