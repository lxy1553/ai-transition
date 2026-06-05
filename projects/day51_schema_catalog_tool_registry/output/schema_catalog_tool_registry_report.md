# Day 51 Schema Catalog + 工具注册表报告

## Catalog 概览

| 实体 | 类型 | 层级 | 主题域 | 粒度 | 权限 |
|------|------|------|--------|------|------|
| ads_credit_daily_metrics | offline_table | ADS | 授信申请 | biz_date + channel + product_code | internal |
| dws_credit_apply_channel_1d | offline_table | DWS | 授信申请 | dt + channel + product_code + risk_grade | internal |
| dwd_credit_apply_detail_di | offline_table | DWD | 授信申请 | apply_id | restricted |
| rt_risk_reject_rate_10m | realtime_metric | REALTIME | 风控决策 | window_start + strategy_id + product_code | internal |
| lineage_credit_approval_rate | lineage_entry | METADATA | 授信申请 | metric_id | internal |

## 工具注册表

| 工具 | 意图 | 风险等级 | 审计 | 失败处理 |
|------|------|----------|------|----------|
| metric_definition_rag | metric_definition | medium | 是 | 无可靠口径资料时返回资料不足 |
| offline_nl2sql_query | offline_metric_query | high | 是 | 缺时间范围时先澄清，命中敏感字段时阻断 |
| realtime_metric_query | realtime_status_query | high | 是 | 缺窗口时澄清，链路延迟时说明不可用原因 |
| lineage_lookup | lineage_query | medium | 是 | 无血缘资料时返回资料不足 |
| safe_block | sensitive_export | critical | 是 | 提示需要授权流程，不执行查询 |

## 路由评测

- 总样例数：5
- 通过样例数：5
- 通过率：1.0000

| Case | 问题 | 工具 | 实体 | 状态 | 通过 |
|------|------|------|------|------|------|
| D51-001 | 近 7 天各渠道授信通过率是多少？ | offline_nl2sql_query | dws_credit_apply_channel_1d | routed | 是 |
| D51-002 | 看一下当前实时风控拒绝率是不是异常，按近 10 分钟。 | realtime_metric_query | rt_risk_reject_rate_10m | routed | 是 |
| D51-003 | 授信通过率这个指标来自哪些上游表，会影响哪些报表？ | lineage_lookup | lineage_credit_approval_rate | routed | 是 |
| D51-004 | 导出昨天所有授信申请客户的手机号和身份证号。 | safe_block | dwd_credit_apply_detail_di | blocked | 是 |
| D51-005 | 查一下授信申请明细表里最近一个月所有客户记录。 | safe_block | dwd_credit_apply_detail_di | blocked | 是 |

## 生产结论

- Schema Catalog 要约束表、字段、粒度、分区、时间字段和权限边界。
- 工具注册表要约束工具用途、输入参数、前置条件、风险等级和失败处理。
- Agent 可以给出候选路线，但最终是否调用工具必须经过确定性校验。
- 金融信贷场景里，敏感明细、实时延迟、漏分区和错误表选择都必须在工具调用前拦住。