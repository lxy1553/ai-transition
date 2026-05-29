# Day 35 - NL2SQL 助手整合演示报告

## 总览

- total: 13
- answered: 8
- safely_blocked: 5
- execution_errors: 0
- incomplete: 0
- demo_ready: True

## 来源产物

- parse: `projects/day30_nl2sql_question_parser/output/question_parse_results.json`
- sql_generation: `projects/day31_nl2sql_sql_generator/output/sql_generation_results.json`
- sql_validation: `projects/day32_nl2sql_sql_validator/output/sql_validation_results.json`
- query_execution: `projects/day33_nl2sql_query_executor/output/query_execution_results.json`
- result_interpretation: `projects/day34_nl2sql_result_interpreter/output/result_interpretation_results.json`

## 演示样例

| question | final_status | pipeline | business_answer |
|----------|--------------|----------|-----------------|
| 昨天授信申请量是多少？ | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 查询结果为：授信申请量 380笔。 |
| 上周每个渠道的授信通过率是多少？ | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 本次按 渠道 分组返回 3 行结果，APP 表现最高。 |
| 最近 7 天放款金额趋势怎么样？ | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 最近 7 天放款金额整体下降，首日为 65.00 万，末日为 47.00 万。 |
| 上周放款金额最高的 10 个城市是什么？ | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 本次返回 8 条排序结果，深圳 排名第一，放款金额为 61.00 万。 |
| 本周逾期率比上周变化多少？ | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 当前周期逾期率为 7.03%，上期为 8.56%，较上期下降 1.53 个百分点。 |
| 查询申请 A123 的审批状态 | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 申请 A123 当前审批状态为审批通过，审批额度为 1.20 万，风险等级为 A。 |
| 导出客户手机号列表 | safely_blocked | parse: available<br>sql_generation: blocked<br>sql_validation: blocked<br>query_execution: skipped<br>result_interpretation: available | 该问题没有执行数据库查询，原因是：no_sql_to_validate。这不是空结果，而是系统安全或校验策略主动拦截。 |
| 本月每个产品的逾期金额前 5 名账龄 | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 本次返回 5 条排序结果，现金贷 / M1 排名第一，逾期金额为 10.33 万。 |
| 北京最近 7 天放款笔数趋势 | answered | parse: available<br>sql_generation: passed<br>sql_validation: passed<br>query_execution: executed<br>result_interpretation: available | 最近 7 天放款笔数整体上升，首日为 38，末日为 55。 |
| 各风险等级的授信通过量 | safely_blocked | parse: available<br>sql_generation: blocked<br>sql_validation: blocked<br>query_execution: skipped<br>result_interpretation: available | 该问题没有执行数据库查询，原因是：no_sql_to_validate。这不是空结果，而是系统安全或校验策略主动拦截。 |
| 危险样例：删除逾期表数据 | safely_blocked | parse: missing<br>sql_generation: missing<br>sql_validation: blocked<br>query_execution: skipped<br>result_interpretation: available | 该问题没有执行数据库查询，原因是：not_read_only, forbidden_keyword:delete。这不是空结果，而是系统安全或校验策略主动拦截。 |
| 危险样例：全量导出客户手机号 | safely_blocked | parse: missing<br>sql_generation: missing<br>sql_validation: blocked<br>query_execution: skipped<br>result_interpretation: available | 该问题没有执行数据库查询，原因是：sensitive_field:id_card,phone。这不是空结果，而是系统安全或校验策略主动拦截。 |
| 危险样例：缺少时间范围的授信汇总 | safely_blocked | parse: missing<br>sql_generation: missing<br>sql_validation: blocked<br>query_execution: skipped<br>result_interpretation: available | 该问题没有执行数据库查询，原因是：missing_time_predicate。这不是空结果，而是系统安全或校验策略主动拦截。 |

## 重点样例拆解

### 1. 昨天授信申请量是多少？

- 最终状态：answered
- 执行摘要：application_count = 380
- 业务回答：查询结果为：授信申请量 380笔。
- 关键发现：授信申请量 = 380笔
- 风险提示：该结果来自本地演示数据，生产环境需要说明数据日期和统计口径。

```sql
select
  sum(application_count) as application_count
from dws_credit_application_daily
where dt = current_date - interval '1' day;
```

### 2. 上周每个渠道的授信通过率是多少？

- 最终状态：answered
- 执行摘要：查询返回 3 行，字段包括：channel, approval_rate。
- 业务回答：本次按 渠道 分组返回 3 行结果，APP 表现最高。
- 关键发现：APP 的授信通过率最高，为 64.87%。<br>线下 的授信通过率最低，为 55.29%。
- 风险提示：分组结果只能说明当前查询周期内的表现，不能直接代表长期趋势。

```sql
select
  channel,
  sum(approval_count) / nullif(sum(application_count), 0) as approval_rate
from dws_credit_application_daily
where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
group by channel;
```

### 3. 最近 7 天放款金额趋势怎么样？

- 最终状态：answered
- 执行摘要：查询返回 7 行，字段包括：dt, disbursement_amount。
- 业务回答：最近 7 天放款金额整体下降，首日为 65.00 万，末日为 47.00 万。
- 关键发现：累计放款金额为 315.00 万。<br>最高点出现在 2026-05-17，数值为 65.00 万。<br>最低点出现在 2026-05-18，数值为 36.00 万。
- 风险提示：趋势解释只基于当前查询窗口，生产分析还需要结合节假日、渠道活动和样本量。

```sql
select
  dt,
  sum(disbursement_amount) as disbursement_amount
from dws_loan_disbursement_daily
where dt between current_date - interval '7' day and current_date - interval '1' day
group by dt;
```

### 4. 上周放款金额最高的 10 个城市是什么？

- 最终状态：answered
- 执行摘要：查询返回 8 行，字段包括：city, disbursement_amount。
- 业务回答：本次返回 8 条排序结果，深圳 排名第一，放款金额为 61.00 万。
- 关键发现：深圳 的放款金额最高，为 61.00 万。<br>北京 的放款金额最低，为 32.00 万。
- 风险提示：分组结果只能说明当前查询周期内的表现，不能直接代表长期趋势。

```sql
select
  city,
  sum(disbursement_amount) as disbursement_amount
from dws_loan_disbursement_daily
where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
group by city
order by disbursement_amount desc
limit 10;
```

### 5. 本周逾期率比上周变化多少？

- 最终状态：answered
- 执行摘要：当前值 0.0703，上期值 0.0856，差值 -0.0153。
- 业务回答：当前周期逾期率为 7.03%，上期为 8.56%，较上期下降 1.53 个百分点。
- 关键发现：当前值：7.03%。<br>上期值：8.56%。<br>变化值：-1.53 个百分点。
- 风险提示：比例指标必须说明分子分母口径，不能只看差值判断风险已经改善。

```sql
with current_period as (
  select sum(overdue_amount) / nullif(sum(due_amount), 0) as current_value
  from dws_repayment_overdue_daily
  where dt >= date_trunc('week', current_date) and dt < current_date + interval '1' day
),
previous_period as (
  select sum(overdue_amount) / nullif(sum(due_amount), 0) as previous_value
  from dws_repayment_overdue_daily
  where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
)
select
  current_value,
  previous_value,
  current_value - previous_value as diff_value
from current_period
cross join previous_period;
```

### 6. 查询申请 A123 的审批状态

- 最终状态：answered
- 执行摘要：查询返回 1 行，字段包括：application_id, application_status, approved_amount, risk_level, apply_time。
- 业务回答：申请 A123 当前审批状态为审批通过，审批额度为 1.20 万，风险等级为 A。
- 关键发现：审批状态：审批通过。<br>审批额度：1.20 万。<br>申请时间：2026-05-23 10:30:00。
- 风险提示：明细结果涉及单个申请，生产环境需要确认当前用户是否有查看该申请的权限。

```sql
select
  application_id,
  application_status,
  approved_amount,
  risk_level,
  apply_time
from dwd_credit_application_detail
where application_id = 'A123'
limit 50;
```

### 7. 导出客户手机号列表

- 最终状态：safely_blocked
- 执行摘要：SQL 未通过校验或上游已阻断，执行层不会访问数据库。
- 业务回答：该问题没有执行数据库查询，原因是：no_sql_to_validate。这不是空结果，而是系统安全或校验策略主动拦截。
- 关键发现：执行层未访问数据库。
- 风险提示：被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。

### 8. 本月每个产品的逾期金额前 5 名账龄

- 最终状态：answered
- 执行摘要：查询返回 5 行，字段包括：product_type, overdue_bucket, overdue_amount。
- 业务回答：本次返回 5 条排序结果，现金贷 / M1 排名第一，逾期金额为 10.33 万。
- 关键发现：现金贷 / M1 的逾期金额最高，为 10.33 万。<br>现金贷 / M3+ 的逾期金额最低，为 3.90 万。
- 风险提示：分组结果只能说明当前查询周期内的表现，不能直接代表长期趋势。

```sql
select
  product_type,
  overdue_bucket,
  sum(overdue_amount) as overdue_amount
from dws_repayment_overdue_daily
where dt >= date_trunc('month', current_date) and dt < current_date + interval '1' day
group by product_type, overdue_bucket
order by overdue_amount desc
limit 5;
```

### 9. 北京最近 7 天放款笔数趋势

- 最终状态：answered
- 执行摘要：查询返回 7 行，字段包括：city, dt, loan_count。
- 业务回答：最近 7 天放款笔数整体上升，首日为 38，末日为 55。
- 关键发现：累计放款笔数为 324。<br>最高点出现在 2026-05-23，数值为 55。<br>最低点出现在 2026-05-17，数值为 38。
- 风险提示：趋势解释只基于当前查询窗口，生产分析还需要结合节假日、渠道活动和样本量。

```sql
select
  city,
  dt,
  sum(loan_count) as loan_count
from dws_loan_disbursement_daily
where dt between current_date - interval '7' day and current_date - interval '1' day
  and city = '北京'
group by city, dt;
```

### 10. 各风险等级的授信通过量

- 最终状态：safely_blocked
- 执行摘要：SQL 未通过校验或上游已阻断，执行层不会访问数据库。
- 业务回答：该问题没有执行数据库查询，原因是：no_sql_to_validate。这不是空结果，而是系统安全或校验策略主动拦截。
- 关键发现：执行层未访问数据库。
- 风险提示：被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。

### 11. 危险样例：删除逾期表数据

- 最终状态：safely_blocked
- 执行摘要：SQL 未通过校验或上游已阻断，执行层不会访问数据库。
- 业务回答：该问题没有执行数据库查询，原因是：not_read_only, forbidden_keyword:delete。这不是空结果，而是系统安全或校验策略主动拦截。
- 关键发现：执行层未访问数据库。
- 风险提示：被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。

### 12. 危险样例：全量导出客户手机号

- 最终状态：safely_blocked
- 执行摘要：SQL 未通过校验或上游已阻断，执行层不会访问数据库。
- 业务回答：该问题没有执行数据库查询，原因是：sensitive_field:id_card,phone。这不是空结果，而是系统安全或校验策略主动拦截。
- 关键发现：执行层未访问数据库。
- 风险提示：被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。

### 13. 危险样例：缺少时间范围的授信汇总

- 最终状态：safely_blocked
- 执行摘要：SQL 未通过校验或上游已阻断，执行层不会访问数据库。
- 业务回答：该问题没有执行数据库查询，原因是：missing_time_predicate。这不是空结果，而是系统安全或校验策略主动拦截。
- 关键发现：执行层未访问数据库。
- 风险提示：被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。

## 结论

Day 35 已把 NL2SQL 的主要链路串成一个可演示版本：
自然语言问题先被解析，再生成 SQL、校验 SQL、执行安全查询，最后输出业务解释。
这个版本保留了成功查询和安全阻断两类样例，能说明项目不只是能查数，
还具备 Schema 约束、权限安全、成本控制和结果解释能力。