# Day 43 Agent 工作流报告

- 步骤数：8
- 结构检查：通过

## 步骤清单

| 步骤 | 作用 | 工具 | 失败回退 |
|------|------|------|----------|
| 意图识别 | 判断用户是在问指标、查明细、问规则解释，还是提出敏感导出请求。 | rule_classifier, llm_classifier | 无法识别时返回 clarification_required，不进入 SQL 生成。 |
| Schema 与知识检索 | 查找可用表、字段、指标口径和业务规则，为后续 SQL 或回答提供依据。 | schema_catalog, rag_retriever | 检索不到关键上下文时拒答或要求补充条件。 |
| 问题结构化解析 | 把自然语言拆成指标、维度、时间范围、过滤条件和查询类型。 | question_parser | 缺少关键条件时返回 clarification_required。 |
| 候选 SQL 或回答计划生成 | 根据结构化问题生成候选 SQL，或者生成基于引用资料的回答计划。 | sql_generator, answer_planner | 生成结果缺少表字段依据时拒答。 |
| 安全、权限、成本校验 | 在执行前检查 SQL、字段、权限、扫描范围和成本风险。 | sql_validator, permission_checker, cost_guard | 校验失败时返回 safely_blocked，并说明阻断原因。 |
| 执行工具 | 只在校验通过后调用查询、检索或业务工具。 | query_executor, rag_reader | 执行失败时进入失败分类，不允许编造结果。 |
| 结果解释与引用 | 把工具返回的结构化结果解释成业务能读懂的回答，并附带限制说明。 | result_interpreter, citation_builder | 结果为空或口径不明时输出保守解释和追问建议。 |
| 审计记录 | 把问题、步骤、工具、SQL、校验、执行和最终回答串成可回放记录。 | audit_storage | 审计写入失败时返回系统错误，不静默吞掉。 |
