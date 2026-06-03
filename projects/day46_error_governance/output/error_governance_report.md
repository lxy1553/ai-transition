# Day 46 错误治理与修复回归报告

## 修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 测试集数量 | 24 | 24 |
| 通过数量 | 20 | 24 |
| 失败数量 | 4 | 0 |
| 通过率 | 0.8333 | 1.0 |

## 修复计划

| Case | 责任层 | 修复类型 | 修复内容 | 回归保护 |
|------|--------|----------|----------|----------|
| D45-003 | tool_routing | realtime_routing_rule | 问题包含近 5 分钟、实时指标或窗口状态时，必须路由到 realtime_metric_tool，禁止继续 offline_sql_generator 和 offline_query_executor。 | 实时窗口样例不能出现 offline_query_executor。 |
| D45-011 | clarification | missing_time_range_guard | 离线指标查询缺少日期、月份或明确时间范围时，必须先进入 clarification，禁止继续 offline_sql_generator 和 offline_query_executor。 | 缺少时间范围样例必须保持 clarification_required。 |
| D45-014 | rag_retrieval | grounding_guardrail | RAG 检索没有 citation 或引用置信度不足时，最终状态必须是 insufficient_evidence，不能让模型补全规则内容。 | 需要引用的规则解释样例不能出现 missing_citation。 |
| D45-021 | realtime_status_check | realtime_delay_taxonomy | 实时指标工具返回链路延迟、窗口不可用或状态过期时，最终状态必须是 execution_failed，结果解释层不能把延迟数据改写成正常结论。 | 实时延迟样例必须保留 execution_failed 状态。 |

## 修复后明细

| Case | 预期状态 | 实际状态 | 通过 | 失败原因 | 工具路线 |
|------|----------|----------|------|----------|----------|
| D45-001 | answered | answered | 是 | 无 | intent_classifier -> schema_catalog -> offline_sql_generator -> sql_validator -> offline_query_executor -> result_interpreter -> audit_logger |
| D45-002 | answered | answered | 是 | 无 | intent_classifier -> schema_catalog -> offline_sql_generator -> sql_validator -> offline_query_executor -> result_interpreter -> audit_logger |
| D45-003 | answered | answered | 是 | 无 | intent_classifier -> realtime_metric_tool -> result_interpreter -> audit_logger |
| D45-004 | answered | answered | 是 | 无 | intent_classifier -> alert_query_tool -> result_interpreter -> audit_logger |
| D45-005 | answered | answered | 是 | 无 | intent_classifier -> rag_retriever -> result_interpreter -> audit_logger |
| D45-006 | answered | answered | 是 | 无 | intent_classifier -> lineage_tool -> result_interpreter -> audit_logger |
| D45-007 | answered | answered | 是 | 无 | intent_classifier -> schema_catalog -> rag_retriever -> offline_sql_generator -> sql_validator -> offline_query_executor -> alert_query_tool -> result_interpreter -> audit_logger |
| D45-008 | answered | answered | 是 | 无 | intent_classifier -> alert_query_tool -> result_interpreter -> audit_logger |
| D45-009 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-010 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-011 | clarification_required | clarification_required | 是 | 无 | intent_classifier -> clarification -> audit_logger |
| D45-012 | clarification_required | clarification_required | 是 | 无 | intent_classifier -> clarification -> audit_logger |
| D45-013 | unsupported | unsupported | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-014 | insufficient_evidence | insufficient_evidence | 是 | 无 | intent_classifier -> rag_retriever -> audit_logger |
| D45-015 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-016 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-017 | answered | answered | 是 | 无 | intent_classifier -> rag_retriever -> result_interpreter -> audit_logger |
| D45-018 | clarification_required | clarification_required | 是 | 无 | intent_classifier -> clarification -> audit_logger |
| D45-019 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |
| D45-020 | execution_failed | execution_failed | 是 | 无 | intent_classifier -> schema_catalog -> offline_query_executor -> audit_logger |
| D45-021 | execution_failed | execution_failed | 是 | 无 | intent_classifier -> realtime_metric_tool -> audit_logger |
| D45-022 | answered | answered | 是 | 无 | intent_classifier -> lineage_tool -> result_interpreter -> audit_logger |
| D45-023 | answered | answered | 是 | 无 | intent_classifier -> schema_catalog -> rag_retriever -> offline_sql_generator -> sql_validator -> offline_query_executor -> alert_query_tool -> result_interpreter -> audit_logger |
| D45-024 | safely_blocked | safely_blocked | 是 | 无 | intent_classifier -> safe_block -> audit_logger |

## 生产启示

- 先按失败类型定位责任层，再决定是改 Prompt、规则、检索还是异常处理。
- 修复 bad case 后必须跑全量评测集，确认没有引入新的回归问题。
- 对金融信贷 Agent 来说，缺少条件、安全阻断、资料不足和系统异常都要有明确最终状态。
