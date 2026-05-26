# Day 30 - NL2SQL 问题解析报告

## 总览

- total: 10
- passed: 10
- accuracy: 1.0
- risk_cases: 2

## 明细

| question | type | metrics | dimensions | time_range | filters | risks | passed |
|----------|------|---------|------------|------------|---------|-------|--------|
| 昨天授信申请量是多少？ | metric | application_count | - | yesterday | - | - | True |
| 上周每个渠道的授信通过率是多少？ | group_by | approval_rate | channel | last_week | - | - | True |
| 最近 7 天放款金额趋势怎么样？ | trend | disbursement_amount | dt | last_7_days | - | - | True |
| 上周放款金额最高的 10 个城市是什么？ | topn | disbursement_amount | city | last_week | - | - | True |
| 本周逾期率比上周变化多少？ | comparison | overdue_rate | - | this_week_vs_last_week | - | - | True |
| 查询申请 A123 的审批状态 | detail | - | application_status | - | {"application_id": "A123"} | - | True |
| 导出客户手机号列表 | sensitive | - | phone | - | - | sensitive_field | True |
| 本月每个产品的逾期金额前 5 名账龄 | topn | overdue_amount | product_type, overdue_bucket | this_month | - | - | True |
| 北京最近 7 天放款笔数趋势 | trend | loan_count | city, dt | last_7_days | {"city": "北京"} | - | True |
| 各风险等级的授信通过量 | group_by | approval_count | risk_level | - | - | missing_time_range | True |

## 结论

Day 30 的重点是先把自然语言问题解析成结构化字段，再交给 Schema Router 和 SQL 生成。
问题解析越清楚，后面的 SQL 生成、权限校验、成本控制和错误排查越稳定。
