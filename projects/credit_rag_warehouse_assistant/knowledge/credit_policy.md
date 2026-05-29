---
doc_id: credit_policy
title: 授信政策与额度审批说明
domain: credit
security_level: internal
allowed_roles: credit_dev,risk_analyst,admin
warehouse_tables: dwd_credit_application,dws_credit_application_daily,ads_credit_risk_dashboard
---

# 授信政策与额度审批说明

授信申请从渠道进入后，会经历资料校验、反欺诈检查、风险评分、额度计算、自动审批或人工复核。
核心状态包括 `submitted`、`auto_approved`、`manual_review`、`rejected` 和 `expired`。

授信通过率用于衡量申请转化质量，口径是通过申请数除以有效申请数。
在数仓汇总层中，优先使用 `dws_credit_application_daily.approval_rate`。
如果需要重新计算，可使用 `approval_count / nullif(application_count, 0)`。

授信通过率分析通常按 `dt`、`channel`、`product_code`、`risk_level` 分组。
生产查询必须带 `dt` 分区条件，避免扫描全量申请明细。

额度审批需要结合申请金额、风险等级、历史逾期、收入稳定性和产品策略。
普通问答可以解释额度审批流程，但不能返回客户级明细、身份证、手机号或完整审批流水。

