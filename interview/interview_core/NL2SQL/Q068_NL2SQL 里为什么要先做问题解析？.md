---
id: Q068
source: interview_core
category: NL2SQL
title: NL2SQL 里为什么要先做问题解析？
generated: 2026-07-23T15:41:19.818757
---

# NL2SQL 里为什么要先做问题解析？

> 来源: 核心题库 | 分类: NL2SQL

NL2SQL 先做问题解析，是为了把用户自然语言拆成 SQL 生成需要的结构化信息。
用户自然语言里通常混合了指标、维度、时间、过滤条件、排序、TopN 和业务口径，
如果直接塞给模型生成 SQL，模型容易漏掉关键信息。

问题解析要提取的结构化字段包括：
- metric（指标）：要算什么，如授信通过率、放款金额、逾期率
- dimensions（维度）：按什么分组，如渠道、城市名、产品编码、日期
- time_range（时间范围）：昨天/近 7 天/上月，必须解析成 start_date、end_date
- filters（过滤条件）：只算渠道 X、只看产品 Y
- query_type（查询类型）：指标查询/趋势查询/TopN/对比/明细
- risk_flags（风险标记）：missing_time_range（缺时间范围）、
  sensitive_field（涉及敏感字段）、bulk_export（大量导出请求）

为什么这样设计：解析结果是结构化的，可以被后续 SQL 生成层、校验层、执行层和
审计层稳定消费。出错时也可以精确定位是解析漏了时间，还是生成错选了字段。
如果跳过解析直接生成 SQL，出错时你只能看到一段错误 SQL，不知道是哪层的问题。