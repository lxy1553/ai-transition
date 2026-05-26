# Day 29 - 金融信贷 NL2SQL 场景分类表

这个表用于把金融信贷业务里的自然语言问题，先拆成问题类型、候选表和主要风险。
Day 29 只做 Schema 准备和路由，不直接生成 SQL。

| 场景 | 用户问题例子 | 需要识别的信息 | 候选表 | 主要风险 |
|------|--------------|----------------|--------|----------|
| 指标查询 | 昨天授信申请量是多少？ | 指标、时间范围 | `dws_credit_application_daily` | 申请口径不清，是否包含重复申请 |
| 维度分组 | 上周每个渠道的授信通过率是多少？ | 指标、时间、渠道维度 | `dws_credit_application_daily` | 渠道字段选错，通过率口径错误 |
| 趋势查询 | 最近 7 天放款金额趋势怎么样？ | 指标、日期粒度 | `dws_loan_disbursement_daily` | 时间字段和分区条件缺失 |
| TopN 查询 | 上周放款金额最高的 10 个城市是什么？ | 指标、城市维度、排序和 limit | `dws_loan_disbursement_daily` | 没有限制 limit 或排序字段错误 |
| 对比查询 | 本周逾期率比上周变化多少？ | 两个时间窗口、同一指标 | `dws_repayment_overdue_daily` | 逾期口径、账龄口径和时间窗口混淆 |
| 明细查询 | 查询申请 A123 的审批状态 | 精确条件、申请字段 | `dwd_credit_application_detail` | 明细权限和客户隐私 |
| 敏感查询 | 导出客户手机号列表 | 敏感字段、权限等级 | `dim_credit_customer` | 越权和隐私泄露 |

## 结构化输出字段

| 字段 | 含义 |
|------|------|
| `question` | 原始用户问题 |
| `question_type` | metric、group_by、trend、topn、comparison、detail、sensitive |
| `candidate_tables` | 候选表 |
| `candidate_metrics` | 候选指标 |
| `candidate_dimensions` | 候选维度 |
| `time_fields` | 可用时间字段 |
| `risk_flags` | 权限、敏感字段、缺少时间字段等风险 |
| `should_generate_sql` | 是否建议进入 SQL 生成 |
