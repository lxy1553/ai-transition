# 指标口径

指标配置来源：`config/metrics_catalog.json`

## 授信申请量

- 指标 ID：`credit_apply_cnt`
- 口径：统计时间范围内提交授信申请的申请单数量。
- 公式：`count(app_id)`
- 来源表：`dws_credit_daily_metrics`
- 常用维度：日期、渠道、产品、城市。

## 授信通过率

- 指标 ID：`credit_approval_rate`
- 口径：审批通过申请数占授信申请数的比例，分母不剔除拒绝和待处理申请。
- 公式：`approved_cnt / apply_cnt`
- 来源表：`dws_credit_daily_metrics`
- 血缘：`ods_credit_applications -> dwd_credit_applications -> dws_credit_daily_metrics`

## 放款金额

- 指标 ID：`loan_amount`
- 口径：审批通过并成功放款的金额总和，按放款成功金额统计。
- 公式：`sum(loan_amount)`
- 来源表：`dws_credit_daily_metrics`

## M1 逾期率

- 指标 ID：`m1_overdue_rate`
- 口径：到期贷款中逾期天数大于等于 30 天的贷款笔数占比。
- 公式：`m1_overdue_cnt / due_loan_cnt`
- 来源表：`dws_repayment_overdue_metrics`
- 血缘：`ods_repayment_snapshots -> dwd_repayment_snapshots -> dws_repayment_overdue_metrics`

## 实时风险事件数

- 指标 ID：`realtime_risk_event_cnt`
- 口径：实时窗口内风控事件数量，按分钟、风险等级和事件类型聚合。
- 公式：`count(event_id)`
- 来源表：`rt_risk_minute_metrics`

## 口径治理原则

- 指标必须有 ID、名称、定义、公式、来源表、血缘、密级和 owner。
- Agent 回答指标时必须返回 citation，不能只给自然语言。
- 指标口径变化必须版本化，历史评测集要重新回归。
