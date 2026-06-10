# Day 56 仓库 Agent 端到端评测报告

## 汇总

- 总样例数：10
- 通过样例数：10
- 失败样例数：0
- 通过率：1.0000

## 样例明细

| Case | 类别 | 路由 | 状态 | 通过 |
|------|------|------|------|------|
| D56-001 | success | daily_alert_agent | answered | 是 |
| D56-002 | empty_partition | offline_nl2sql_query | no_data | 是 |
| D56-003 | realtime_delay | realtime_metric_query | degraded | 是 |
| D56-004 | sensitive_export | safe_block | blocked | 是 |
| D56-005 | metric_conflict | metric_definition_rag | need_clarification | 是 |
| D56-006 | alert_false_positive | alert_validation_tool | answered | 是 |
| D56-007 | lineage | lineage_lookup | answered | 是 |
| D56-008 | sql_safety | offline_nl2sql_query | need_clarification | 是 |
| D56-009 | tool_error | realtime_metric_query | tool_error | 是 |
| D56-010 | bounded_explanation | bounded_explanation | answered | 是 |

## 生产结论

- 端到端评测要同时检查最终回答、工具路线、证据、审计和安全状态。
- 空分区、实时延迟、告警误报、口径冲突和敏感导出都必须进入固定回归集。
- 不能只看回答文字是否像样；如果路线错、证据缺失或该拒答未拒答，都应判失败。
- 每次修复 bad case 后要跑全量回归，防止新改动破坏旧能力。