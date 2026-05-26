# Day 31 - NL2SQL SQL 生成报告

## 总览

- total: 10
- generated: 8
- blocked: 2
- validation_failed: 0

## 明细

| question | type | table | can_generate_sql | blocking_reasons | validation_issues |
|----------|------|-------|------------------|------------------|-------------------|
| 昨天授信申请量是多少？ | metric | dws_credit_application_daily | True | - | - |
| 上周每个渠道的授信通过率是多少？ | group_by | dws_credit_application_daily | True | - | - |
| 最近 7 天放款金额趋势怎么样？ | trend | dws_loan_disbursement_daily | True | - | - |
| 上周放款金额最高的 10 个城市是什么？ | topn | dws_loan_disbursement_daily | True | - | - |
| 本周逾期率比上周变化多少？ | comparison | dws_repayment_overdue_daily | True | - | - |
| 查询申请 A123 的审批状态 | detail | dwd_credit_application_detail | True | - | - |
| 导出客户手机号列表 | sensitive | - | False | sensitive_field, sensitive_query | blocked_before_generation |
| 本月每个产品的逾期金额前 5 名账龄 | topn | dws_repayment_overdue_daily | True | - | - |
| 北京最近 7 天放款笔数趋势 | trend | dws_loan_disbursement_daily | True | - | - |
| 各风险等级的授信通过量 | group_by | - | False | missing_time_range | blocked_before_generation |

## SQL 草稿

### 1. 昨天授信申请量是多少？

```sql
select
  sum(application_count) as application_count
from dws_credit_application_daily
where dt = current_date - interval '1' day;
```

### 2. 上周每个渠道的授信通过率是多少？

```sql
select
  channel,
  sum(approval_count) / nullif(sum(application_count), 0) as approval_rate
from dws_credit_application_daily
where dt between date_trunc('week', current_date) - interval '7' day and date_trunc('week', current_date) - interval '1' day
group by channel;
```

### 3. 最近 7 天放款金额趋势怎么样？

```sql
select
  dt,
  sum(disbursement_amount) as disbursement_amount
from dws_loan_disbursement_daily
where dt between current_date - interval '7' day and current_date - interval '1' day
group by dt;
```

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

### 7. 导出客户手机号列表

未生成 SQL：sensitive_field, sensitive_query

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

### 10. 各风险等级的授信通过量

未生成 SQL：missing_time_range

## 结论

Day 31 的重点不是让 SQL 直接上线执行，而是把解析结果、Schema Catalog 和只读约束结合起来，
生成一份可审查、可校验、可追踪的 SQL 草稿。
生产环境里还必须接 Day 32 的 SQL 校验层，继续检查权限、字段白名单、时间范围、扫描成本和危险关键字。
