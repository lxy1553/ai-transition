---
doc_id: risk_rules
title: 风控规则与反欺诈策略
domain: risk
security_level: restricted
allowed_roles: credit_dev,risk_analyst,admin
warehouse_tables: dwd_credit_decision_log,dws_risk_rule_hit_daily
---

# 风控规则与反欺诈策略

风控规则分为硬拒绝、人工复核和提示类规则。
硬拒绝规则命中后，申请不能进入自动通过流程。
人工复核规则命中后，需要风控运营或审批人员查看补充材料。
提示类规则只用于模型解释和风险提示，不直接决定拒绝。

常见规则包括设备异常、黑名单命中、多头申请、短期频繁申请、历史严重逾期、身份核验失败和反欺诈分过低。

规则命中明细保存在 `dwd_credit_decision_log`。
按天汇总后的规则命中情况保存在 `dws_risk_rule_hit_daily`。
分析某条规则的拒绝率时，应使用 `reject_count / nullif(hit_count, 0)`。

风控规则属于 restricted 资料。
客服和外部用户不能查看完整规则逻辑、阈值、模型分或黑名单来源。
RAG 回答可以解释规则分类和处理流程，但不能泄露精确阈值和绕过策略。

