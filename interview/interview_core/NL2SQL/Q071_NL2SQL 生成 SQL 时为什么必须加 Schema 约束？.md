---
id: Q071
source: interview_core
category: NL2SQL
title: NL2SQL 生成 SQL 时为什么必须加 Schema 约束？
generated: 2026-07-23T15:41:19.819161
---

# NL2SQL 生成 SQL 时为什么必须加 Schema 约束？

> 来源: 核心题库 | 分类: NL2SQL

NL2SQL 生成 SQL 时必须加 Schema 约束，因为模型本身不知道真实数据库里有什么。

不加约束的典型问题：模型可能编造不存在的字段名（如"approval_rate"实际叫
"approval_rate_pct"），选错事实表（DWD 明细表当成 ADS 汇总表用），
漏掉分区条件（全表扫描三年历史数据），访问手机号、身份证号等敏感字段。

生产里的 Schema 约束包含三层：
第一层，表白名单：只能从 Schema Catalog 中的可用表里选择，提示词里明确列出
候选表的名称、描述和适用场景（如 ads_credit_daily_metrics 适合日报总览，
dws_credit_apply_channel_1d 适合渠道趋势）。
第二层，字段白名单：SQL 中使用的字段必须在 Catalog 的字段列表中，敏感字段标记
为 restricted，生成阶段直接排除。
第三层，指标口径约束：像授信通过率、逾期率这类比例指标，提示词里要写清分子分母
对应的字段和过滤逻辑，不能随便 avg。

生成后 SQL 还要经过 SQL Validator 校验——确认所有字段来源合法、时间范围写死、
limit 存在、没有 restricted 字段。生成器和校验器配合，模型负责"在框里写 SQL"，
校验器负责"检查有没有越框"。