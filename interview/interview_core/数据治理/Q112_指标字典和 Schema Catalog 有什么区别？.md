---
id: Q112
source: interview_core
category: 数据治理
title: 指标字典和 Schema Catalog 有什么区别？
generated: 2026-07-23T15:41:19.824331
---

# 指标字典和 Schema Catalog 有什么区别？

> 来源: 核心题库 | 分类: 数据治理

指标字典和 Schema Catalog 解决的是两个不同问题。
指标字典回答“这个数怎么算”，Schema Catalog 回答“这个数从哪些表字段查”。
前者管业务口径，后者管数据结构。

指标字典关注指标含义、计算公式、分子、分母、过滤条件、时间口径、统计粒度、可用维度、适用范围和负责人。
例如审批通过率的指标字典要写清：分子是审批通过申请数，分母是进入审批流程申请数，
时间口径按申请完成时间，过滤条件要剔除测试渠道和撤销申请。
它主要用于口径解释、指标校验、结果解释和 RAG 问答，防止 Agent 把指标讲错或混用。

Schema Catalog 关注表名、表描述、字段名、字段类型、主键、分区字段、表粒度、表关系、权限标签和可查询范围。
例如 `ads_credit_daily_metrics` 这张表要写清字段包括 `biz_date`、`channel`、`product_code`、
`apply_cnt`、`approved_cnt`、`approval_rate`，分区字段是 `biz_date`，不包含客户手机号和身份证号。
它主要用于 NL2SQL 的表选择、字段选择、SQL 生成、SQL 校验和权限控制，防止 Agent 选错表、编造字段、漏分区或越权查询。

在金融信贷 Agent 链路里，用户问“审批通过率怎么算”，应该优先查指标字典或 RAG 口径文档；
用户问“近 7 天各渠道审批通过率是多少”，才需要先根据指标字典确认口径，再通过 Schema Catalog 找到合适的 ADS/DWS 表和字段，
生成 SQL 并校验执行。

一句面试总结是：指标字典保证“算得对”，Schema Catalog 保证“查得对”。
生产级数据问答必须同时具备这两类元数据，否则要么口径错，要么 SQL 查错。