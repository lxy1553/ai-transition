---
id: Q113
source: interview_core
category: Agent
title: 金融信贷 Agent 的 Schema Catalog 应该包含哪些信息？
generated: 2026-07-23T15:41:19.824431
---

# 金融信贷 Agent 的 Schema Catalog 应该包含哪些信息？

> 来源: 核心题库 | 分类: Agent

生产级 Schema Catalog 不能只记录表名和字段名。
它应该同时记录表描述、业务主题域、仓库层级、表粒度、主键、分区字段、时间字段、字段类型、字段含义、
可用维度、指标字段、敏感字段、权限等级、数据更新频率、owner、查询约束和下游使用场景。

在金融信贷 Agent 里，Catalog 的作用是约束 NL2SQL 和工具路由。
例如 `ads_credit_daily_metrics` 适合日报总览，`dws_credit_apply_channel_1d` 适合渠道趋势，
`dwd_credit_apply_detail_di` 含客户手机号和身份证号，只能在授权排查时访问。
Agent 生成 SQL 前要根据 Catalog 判断应该选 ADS、DWS 还是 DWD，必须带时间范围和分区条件，
不得编造字段，不得访问无权限的敏感字段。

一句面试总结是：Schema Catalog 保证 Agent “查得对、查得安全、查得可控成本”。