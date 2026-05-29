---
doc_id: repayment_overdue
title: 还款逾期与贷后口径说明
domain: repayment
security_level: internal
allowed_roles: credit_dev,risk_analyst,collection_operator,admin
warehouse_tables: dwd_repayment_plan,dwd_overdue_detail,dws_repayment_overdue_daily
---

# 还款逾期与贷后口径说明

DPD 表示逾期天数，含义是当前日期距离应还日期超过的天数。
常见 bucket 包括 `M0`、`M1`、`M2`、`M3+`。
M1 通常表示逾期 1 到 30 天，M2 通常表示逾期 31 到 60 天。

还款计划查询优先使用 `dwd_repayment_plan`。
逾期明细查询优先使用 `dwd_overdue_detail`。
按产品和逾期阶段看趋势时，优先使用 `dws_repayment_overdue_daily`。

逾期率常见口径是逾期金额除以应还金额。
在汇总层可使用 `overdue_amount / nullif(due_amount, 0)`。
分析逾期趋势必须带 `dt` 分区条件，通常按 `product_code` 和 `bucket` 分组。

贷后和催收角色可以查看还款计划、逾期阶段和汇总指标。
客户身份明细、联系方式和完整催收记录属于敏感信息，不应通过普通 RAG 问答返回。

