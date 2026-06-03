# 数据接入与数仓契约

## 批量数据：授信申请

文件：`data/batch/credit_applications.csv`

| 字段 | 含义 | 质量要求 |
|------|------|----------|
| app_id | 授信申请单号 | 必填、唯一 |
| customer_id | 客户编号 | 必填、敏感字段，不直接暴露 |
| channel | 申请渠道 | 必填 |
| product | 信贷产品 | 必填 |
| city | 城市 | 可用于维度分析 |
| apply_time | 申请提交时间 | 必填 |
| decision_time | 审批完成时间 | 可为空 |
| status | 审批状态 | `APPROVED` / `REJECTED` / `PENDING` |
| approved_amount | 审批额度 | 数值 |
| loan_amount | 放款金额 | 数值，不能大于审批额度 |
| risk_level | 风险等级 | low / medium / high |
| reject_reason | 拒绝原因 | 拒绝样例必填 |
| is_new_customer | 是否新客 | 0 / 1 |
| dt | 分区日期 | 必填 |

## 批量数据：还款快照

文件：`data/batch/repayment_snapshots.csv`

| 字段 | 含义 | 质量要求 |
|------|------|----------|
| loan_id | 借据号 | 必填 |
| customer_id | 客户编号 | 必填、敏感字段 |
| product | 产品 | 必填 |
| due_date | 应还日期 | 必填 |
| repay_date | 实还日期 | 可为空 |
| overdue_days | 逾期天数 | 不能小于 0 |
| principal_balance | 剩余本金 | 数值 |
| paid_amount | 已还金额 | 数值 |
| collection_queue | 催收队列 | none / D1_D29 / M1 / M2 |
| dt | 分区日期 | 必填 |

## 实时数据：风控事件

文件：`data/realtime/risk_events.jsonl`

| 字段 | 含义 |
|------|------|
| event_id | 事件编号 |
| event_time | 事件时间 |
| app_id | 授信申请单号 |
| customer_id | 客户编号 |
| event_type | 事件类型 |
| risk_level | 风险等级 |
| channel | 渠道 |
| decision | 风控结果 |
| rule_code | 规则编号 |

## 数仓分层

| 层级 | 表 | 说明 |
|------|----|------|
| ODS | `ods_credit_applications` | 授信原始接入 |
| ODS | `ods_repayment_snapshots` | 还款快照原始接入 |
| ODS_RT | `ods_risk_events` | 实时风控事件原始层 |
| DWD | `dwd_credit_applications` | 清洗后的授信申请明细 |
| DWD | `dwd_repayment_snapshots` | 清洗后的还款快照明细 |
| DWS | `dws_credit_daily_metrics` | 授信日渠道指标 |
| DWS | `dws_repayment_overdue_metrics` | 贷后逾期指标 |
| RT_DWS | `rt_risk_minute_metrics` | 风控事件分钟聚合 |
