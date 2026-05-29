# Day 33 - NL2SQL 查询执行报告

## 总览

- total: 13
- executed: 8
- skipped: 5
- execution_errors: 0
- run_date: 2026-05-24

## 执行明细

| question | status | response_type | row_count | summary |
|----------|--------|---------------|-----------|---------|
| 昨天授信申请量是多少？ | executed | scalar | 1 | application_count = 380 |
| 上周每个渠道的授信通过率是多少？ | executed | table | 3 | 查询返回 3 行，字段包括：channel, approval_rate。 |
| 最近 7 天放款金额趋势怎么样？ | executed | trend_table | 7 | 查询返回 7 行，字段包括：dt, disbursement_amount。 |
| 上周放款金额最高的 10 个城市是什么？ | executed | table | 8 | 查询返回 8 行，字段包括：city, disbursement_amount。 |
| 本周逾期率比上周变化多少？ | executed | comparison | 1 | 当前值 0.0703，上期值 0.0856，差值 -0.0153。 |
| 查询申请 A123 的审批状态 | executed | detail_table | 1 | 查询返回 1 行，字段包括：application_id, application_status, approved_amount, risk_level, apply_time。 |
| 导出客户手机号列表 | skipped | - | 0 | SQL 未通过校验或上游已阻断，执行层不会访问数据库。 |
| 本月每个产品的逾期金额前 5 名账龄 | executed | table | 5 | 查询返回 5 行，字段包括：product_type, overdue_bucket, overdue_amount。 |
| 北京最近 7 天放款笔数趋势 | executed | trend_table | 7 | 查询返回 7 行，字段包括：city, dt, loan_count。 |
| 各风险等级的授信通过量 | skipped | - | 0 | SQL 未通过校验或上游已阻断，执行层不会访问数据库。 |
| 危险样例：删除逾期表数据 | skipped | - | 0 | SQL 未通过校验或上游已阻断，执行层不会访问数据库。 |
| 危险样例：全量导出客户手机号 | skipped | - | 0 | SQL 未通过校验或上游已阻断，执行层不会访问数据库。 |
| 危险样例：缺少时间范围的授信汇总 | skipped | - | 0 | SQL 未通过校验或上游已阻断，执行层不会访问数据库。 |

## 返回结果样例

### 1. 昨天授信申请量是多少？

- 状态：executed
- 摘要：application_count = 380

| application_count |
| --- |
| 380 |

### 2. 上周每个渠道的授信通过率是多少？

- 状态：executed
- 摘要：查询返回 3 行，字段包括：channel, approval_rate。

| channel | approval_rate |
| --- | --- |
| APP | 0.6487 |
| 小程序 | 0.64 |
| 线下 | 0.5529 |

### 3. 最近 7 天放款金额趋势怎么样？

- 状态：executed
- 摘要：查询返回 7 行，字段包括：dt, disbursement_amount。

| dt | disbursement_amount |
| --- | --- |
| 2026-05-17 | 650000.0 |
| 2026-05-18 | 360000.0 |
| 2026-05-19 | 410000.0 |
| 2026-05-20 | 380000.0 |
| 2026-05-21 | 450000.0 |
| 2026-05-22 | 430000.0 |
| 2026-05-23 | 470000.0 |

### 4. 上周放款金额最高的 10 个城市是什么？

- 状态：executed
- 摘要：查询返回 8 行，字段包括：city, disbursement_amount。

| city | disbursement_amount |
| --- | --- |
| 深圳 | 610000.0 |
| 上海 | 520000.0 |
| 广州 | 480000.0 |
| 杭州 | 460000.0 |
| 成都 | 390000.0 |
| 南京 | 350000.0 |
| 武汉 | 330000.0 |
| 北京 | 320000.0 |

### 5. 本周逾期率比上周变化多少？

- 状态：executed
- 摘要：当前值 0.0703，上期值 0.0856，差值 -0.0153。

| current_value | previous_value | diff_value |
| --- | --- | --- |
| 0.0703 | 0.0856 | -0.0153 |

### 6. 查询申请 A123 的审批状态

- 状态：executed
- 摘要：查询返回 1 行，字段包括：application_id, application_status, approved_amount, risk_level, apply_time。

| application_id | application_status | approved_amount | risk_level | apply_time |
| --- | --- | --- | --- | --- |
| A123 | APPROVED | 12000.0 | A | 2026-05-23 10:30:00 |

### 7. 导出客户手机号列表

- 状态：skipped
- 跳过原因：no_sql_to_validate

### 8. 本月每个产品的逾期金额前 5 名账龄

- 状态：executed
- 摘要：查询返回 5 行，字段包括：product_type, overdue_bucket, overdue_amount。

| product_type | overdue_bucket | overdue_amount |
| --- | --- | --- |
| 现金贷 | M1 | 103300.0 |
| 分期贷 | M3+ | 87200.0 |
| 现金贷 | M2 | 73200.0 |
| 分期贷 | M2 | 60700.0 |
| 现金贷 | M3+ | 39000.0 |

### 9. 北京最近 7 天放款笔数趋势

- 状态：executed
- 摘要：查询返回 7 行，字段包括：city, dt, loan_count。

| city | dt | loan_count |
| --- | --- | --- |
| 北京 | 2026-05-17 | 38 |
| 北京 | 2026-05-18 | 42 |
| 北京 | 2026-05-19 | 46 |
| 北京 | 2026-05-20 | 44 |
| 北京 | 2026-05-21 | 51 |
| 北京 | 2026-05-22 | 48 |
| 北京 | 2026-05-23 | 55 |

### 10. 各风险等级的授信通过量

- 状态：skipped
- 跳过原因：no_sql_to_validate

### 11. 危险样例：删除逾期表数据

- 状态：skipped
- 跳过原因：not_read_only, forbidden_keyword:delete

### 12. 危险样例：全量导出客户手机号

- 状态：skipped
- 跳过原因：sensitive_field:id_card,phone

### 13. 危险样例：缺少时间范围的授信汇总

- 状态：skipped
- 跳过原因：missing_time_predicate

## 结论

Day 33 的重点是把 SQL 校验结果接到查询执行层。
执行层只处理校验通过的 SQL，并把结果整理成前端和业务用户能消费的结构。
被拦截的 SQL 不应该再尝试访问数据库，这样才能把安全、权限和成本风险挡在执行层之外。