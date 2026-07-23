---
id: Q069
source: interview_core
category: NL2SQL
title: 自然语言时间在 NL2SQL 里怎么处理？
generated: 2026-07-23T15:41:19.818894
---

# 自然语言时间在 NL2SQL 里怎么处理？

> 来源: 核心题库 | 分类: NL2SQL

自然语言时间必须转成结构化时间条件。
比如“昨天”“上周”“最近 7 天”“本月”都要解析成 start_date、end_date、granularity 和 time_field。
生产里不能只把原始时间词塞进 prompt，因为不同业务可能有不同时间口径，
比如申请提交时间、审批完成时间、放款成功时间、还款到期日、分区日期和事件发生时间。
如果时间不清楚，要使用业务默认规则或向用户追问。
同时，大表查询必须限制时间范围，避免生成全表扫描 SQL。