---
id: Q105
source: interview_core
category: NL2SQL
title: Agent 每一步为什么通常用 JSON 做结构化输入输出，字段应该怎么设计？
generated: 2026-07-23T15:41:19.823428
---

# Agent 每一步为什么通常用 JSON 做结构化输入输出，字段应该怎么设计？

> 来源: 核心题库 | 分类: NL2SQL

Agent 每一步通常用 JSON 做结构化输入输出，是因为 Agent 不是单轮聊天，而是一条可编排的工程链路。
自然语言适合给人看，但不适合直接驱动后续工具调用。
JSON 可以被代码稳定解析、Schema 校验、状态机路由、审计记录和评测回归。
如果模型只返回一段话，系统很难可靠判断下一步该查 Schema、走 RAG、生成 SQL、要求补充条件，还是安全阻断。

设计 JSON 字段时，核心原则是每一步只返回下一步真正需要的字段。
通常要有统一外壳：`request_id` 用来串联全链路，`step` 表示当前步骤，
`status` 表示处理结果，`data` 保存当前步骤的业务产物，`errors` 和 `warnings`
保存结构化错误与风险，`next_action` 决定下一步路由，`audit` 保存角色、时间和必要审计信息。
其中 `status` 和 `next_action` 必须使用固定枚举，不能让模型自由写“可以查”“好像不行”这类自然语言。

例如问题解析步骤的 `data` 可以包含 `intent`、`metric`、`dimensions`、`filters`、
`time_range`、`risk_flags` 和 `missing_fields`。
SQL 生成步骤要返回 `candidate_sql`、`used_tables`、`used_fields`、`is_readonly` 和生成依据。
SQL 校验步骤要返回 `safe_to_execute`、`blocked_reasons`、`checked_items` 和错误码。
查询执行步骤要返回 `execution_status`、`columns`、`rows`、`row_count` 和耗时。
最终回答步骤要返回 `answer`、`key_findings`、`citations`、`limitations` 和 `final_status`。

在金融信贷 NL2SQL 或 Agent 场景里，风险字段尤其重要。
例如 `risk_flags` 可以标记 `missing_time_range`、`sensitive_field`、`customer_detail`、
`bulk_export`、`write_operation`、`high_cost_query` 和 `permission_required`。
这些字段不能只藏在回答文本里，而要显式放在 JSON 中，由编排层决定是否继续执行。
命中敏感字段或写操作时，应进入 `safe_block`；缺少时间范围时，应进入 `clarification`；
SQL 校验失败时，不能进入 `query_executor`。

工程实现上，可以用 Pydantic、dataclass 或 JSON Schema 定义每一步的输入输出模型。
LLM 可以生成候选 JSON，但代码必须负责解析、Schema 校验和业务规则校验。
结构不合法就重试、降级、澄清或拒答，不能把不合格的自然语言结果继续传给工具。
高风险环节如权限、安全、SQL 校验、查询执行和审计，必须由确定性代码兜底。

一句面试总结是：JSON 的价值不是让输出看起来规范，而是让 Agent 每一步都能被解析、校验、路由、审计和评测。
字段设计要围绕下一步需要什么、风险如何拦截、失败如何归因来做。