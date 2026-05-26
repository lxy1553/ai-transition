# Day 29 - NL2SQL Schema Router 报告

## 总览

- questions: 7
- can_generate_sql: 6
- blocked_or_need_review: 1

## 明细

| question | type | candidate_tables | risk_flags | should_generate_sql |
|----------|------|------------------|------------|---------------------|
| 昨天授信申请量是多少？ | metric | dws_credit_application_daily | - | True |
| 上周每个渠道的授信通过率是多少？ | group_by | dws_credit_application_daily | - | True |
| 最近 7 天放款金额趋势怎么样？ | trend | dws_loan_disbursement_daily | - | True |
| 上周放款金额最高的 10 个城市是什么？ | topn | dws_loan_disbursement_daily | - | True |
| 本周逾期率比上周变化多少？ | comparison | dws_repayment_overdue_daily | - | True |
| 查询申请 A123 的审批状态 | detail | dwd_credit_application_detail | permission:restricted | True |
| 导出客户手机号列表 | sensitive | dim_credit_customer | permission:sensitive, sensitive_query | False |

## 结论

Day 29 的重点是先做 schema 路由，而不是直接生成 SQL。
如果候选表、指标、维度、时间字段和权限边界不清楚，后面的 SQL 生成越自动越危险。
