---
doc_id: warehouse_dictionary
title: 金融信贷数仓数据字典
domain: warehouse
security_level: internal
allowed_roles: credit_dev,risk_analyst,collection_operator,admin
warehouse_tables: ods_credit_apply,dwd_credit_application,dwd_credit_decision_log,dwd_loan_account,dwd_repayment_plan,dwd_overdue_detail,dws_credit_application_daily,dws_risk_rule_hit_daily,dws_repayment_overdue_daily,ads_credit_risk_dashboard
---

# 金融信贷数仓数据字典

信贷数仓采用 ODS、DWD、DWS、ADS 分层。
ODS 保留业务系统贴源数据，DWD 负责清洗后的明细事实，DWS 负责指标汇总，ADS 面向看板和应用。

`dwd_credit_application` 是授信申请明细事实表，粒度是 `apply_id`。
常用字段包括 `dt`、`apply_id`、`customer_id`、`channel`、`product_code`、`apply_amount`、`apply_status`、`risk_level`。

`dws_credit_application_daily` 是授信申请按天汇总表，粒度是 `dt + channel + product_code`。
常用指标包括 `application_count`、`approval_count`、`reject_count`、`manual_review_count` 和 `approval_rate`。

`dwd_loan_account` 是借据账户明细表，粒度是 `loan_id`。
常用字段包括 `loan_amount`、`loan_status`、`disburse_time` 和 `loan_term`。

`dwd_repayment_plan` 是还款计划明细表，粒度是 `loan_id + period_no`。
它适合查询单笔借据每一期应还本金、利息、到期日和还款状态。

`dwd_overdue_detail` 是逾期明细表，粒度是 `loan_id + dt`。
常用字段包括 `dpd`、`overdue_principal`、`overdue_interest` 和 `bucket`。

客户手机号、身份证、银行卡、精确住址等字段不进入普通问答上下文。
如果必须用于审计或排查，应通过后台权限流程查询，不能由 RAG 直接返回。

