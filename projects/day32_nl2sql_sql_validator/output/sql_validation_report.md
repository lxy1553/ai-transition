# Day 32 - NL2SQL SQL 校验报告

## 总览

- total: 13
- passed: 8
- failed: 3
- blocked_before_generation: 2
- warnings: 0

## 明细

| question | source_status | can_execute | risk_level | issues | warnings |
|----------|---------------|-------------|------------|--------|----------|
| 昨天授信申请量是多少？ | generated | True | low | - | - |
| 上周每个渠道的授信通过率是多少？ | generated | True | low | - | - |
| 最近 7 天放款金额趋势怎么样？ | generated | True | low | - | - |
| 上周放款金额最高的 10 个城市是什么？ | generated | True | low | - | - |
| 本周逾期率比上周变化多少？ | generated | True | low | - | - |
| 查询申请 A123 的审批状态 | generated | True | low | - | - |
| 导出客户手机号列表 | blocked_before_generation | False | blocked | no_sql_to_validate | - |
| 本月每个产品的逾期金额前 5 名账龄 | generated | True | low | - | - |
| 北京最近 7 天放款笔数趋势 | generated | True | low | - | - |
| 各风险等级的授信通过量 | blocked_before_generation | False | blocked | no_sql_to_validate | - |
| 危险样例：删除逾期表数据 | manual_risk_case | False | high | not_read_only, forbidden_keyword:delete | - |
| 危险样例：全量导出客户手机号 | manual_risk_case | False | high | sensitive_field:id_card,phone | - |
| 危险样例：缺少时间范围的授信汇总 | manual_risk_case | False | high | missing_time_predicate | - |

## SQL 校验样例

### 1. 昨天授信申请量是多少？

```sql
select
  sum(application_count) as application_count
from dws_credit_application_daily
where dt = current_date - interval '1' day;
```

校验通过：可进入查询执行层。

### 2. 上周每个渠道的授信通过率是多少？

```sql
select
  channel,
  sum(approval_count) / nullif(sum(application_count), 0) as approval_rate
from dws_credit_application_daily
where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
group by channel;
```

校验通过：可进入查询执行层。

### 3. 最近 7 天放款金额趋势怎么样？

```sql
select
  dt,
  sum(disbursement_amount) as disbursement_amount
from dws_loan_disbursement_daily
where dt between current_date - interval '7' day and current_date - interval '1' day
group by dt;
```

校验通过：可进入查询执行层。

### 4. 上周放款金额最高的 10 个城市是什么？

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

校验通过：可进入查询执行层。

### 5. 本周逾期率比上周变化多少？

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

校验通过：可进入查询执行层。

### 6. 查询申请 A123 的审批状态

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

校验通过：可进入查询执行层。

### 7. 导出客户手机号列表

未进入 SQL 校验：上游 SQL 生成阶段已经阻断。

阻断原因：no_sql_to_validate

### 8. 本月每个产品的逾期金额前 5 名账龄

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

校验通过：可进入查询执行层。

### 9. 北京最近 7 天放款笔数趋势

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

校验通过：可进入查询执行层。

### 10. 各风险等级的授信通过量

未进入 SQL 校验：上游 SQL 生成阶段已经阻断。

阻断原因：no_sql_to_validate

### 11. 危险样例：删除逾期表数据

```sql
delete from dws_repayment_overdue_daily where dt < current_date - interval '365' day;
```

阻断原因：not_read_only, forbidden_keyword:delete

### 12. 危险样例：全量导出客户手机号

```sql
select customer_id, phone, id_card from dim_credit_customer;
```

阻断原因：sensitive_field:id_card,phone

### 13. 危险样例：缺少时间范围的授信汇总

```sql
select risk_level, sum(approval_count) as approval_count from dws_credit_application_daily group by risk_level;
```

阻断原因：missing_time_predicate

## 结论

Day 32 的重点是把 SQL 生成层和查询执行层隔开。
生产环境里，NL2SQL 生成的 SQL 必须先经过只读、权限、字段、时间范围、敏感信息和成本校验，
再决定是否允许执行、要求用户补充信息，或进入人工审批流程。