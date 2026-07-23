---
id: Q067
source: interview_core
category: NL2SQL
title: NL2SQL 问题分类有什么价值？
generated: 2026-07-23T15:41:19.818637
---

# NL2SQL 问题分类有什么价值？

> 来源: 核心题库 | 分类: NL2SQL

NL2SQL 问题分类能降低 SQL 生成难度。
指标查询、维度分组、趋势查询、TopN、对比查询和明细查询，对应的 SQL 结构不一样。
先识别问题类型，可以决定是否需要聚合、group by、order by、limit、时间窗口或精确过滤。
如果问题涉及敏感信息或权限不足，还可以在生成 SQL 前拦截。
这比直接生成 SQL 更容易控制质量、成本和安全风险。