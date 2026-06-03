# Day 44 工具编排报告

- 工具数量：10
- 场景数量：5
- 路线检查问题：0

## 工具注册表

| 工具 | 用途 | 风险等级 | 前置条件 |
|------|------|----------|----------|
| intent_classifier | 识别用户是在问指标、规则解释、明细查询还是敏感导出。 | low | 无 |
| schema_lookup | 查找用户有权限访问的表、字段、指标口径和权限标签。 | medium | intent_is_metric_query |
| rag_retriever | 检索政策、口径、规则和说明文档，并返回引用来源。 | medium | intent_is_rule_question |
| sql_generator | 基于 schema_context 生成候选只读 SQL。 | medium | schema_lookup_done |
| sql_validator | 检查只读、敏感字段、时间范围、limit、权限和成本风险。 | high | candidate_sql_generated |
| query_executor | 只执行校验通过的 SQL，并限制超时和返回行数。 | high | sql_validation_passed |
| result_interpreter | 把查询结果或检索资料解释成业务语言，并说明口径和限制。 | medium | has_query_result_or_citations |
| safe_block | 对敏感导出、越权字段、高成本查询或危险请求做安全阻断。 | low | risk_detected |
| clarification | 当时间范围、指标、产品、地区等关键条件缺失时，要求用户补充。 | low | missing_required_condition |
| audit_logger | 记录 request_id、工具路线、失败原因、最终状态和必要脱敏信息。 | low | 无 |

## 场景路线

| 场景 | 问题 | 工具路线 | 最终状态 | 回退原因 |
|------|------|----------|----------|----------|
| metric_success | 本周授信通过率比上周变化多少？ | intent_classifier -> schema_lookup -> sql_generator -> sql_validator -> query_executor -> result_interpreter -> audit_logger | answered | 无 |
| rule_answer | 近 90 天有 M2 逾期记录还能自动审批吗？ | intent_classifier -> rag_retriever -> result_interpreter -> audit_logger | answered | 无 |
| sensitive_export | 导出今天被拒客户的手机号和身份证号。 | intent_classifier -> safe_block -> audit_logger | safely_blocked | 命中敏感字段或批量导出风险。 |
| missing_time_range | 查一下放款金额最高的渠道。 | intent_classifier -> schema_lookup -> clarification -> audit_logger | clarification_required | 指标查询缺少时间范围，不能继续生成 SQL。 |
| unsafe_sql | 删除测试客户的授信申请记录。 | intent_classifier -> safe_block -> audit_logger | safely_blocked | 命中写操作风险，Agent 只能走只读查询或拒答。 |
