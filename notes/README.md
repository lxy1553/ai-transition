# Notes Index

## 置顶

- [AI 转型学习术语表](./terminology_glossary.md)
- [代码注释规则](../docs/code_commenting_guidelines.md)
- [生产级 RAG 流程框架图](./rag_production_architecture.md)
- [生产级 NL2SQL 流程框架图](./nl2sql_production_architecture.md)
- 每日学习笔记必须包含“生产实际”部分，说明真实项目里的用法、风险和工程取舍。
- 旧代码和新代码都要补大白话注释，说明用途、设计原因和风险，不只写运行用法。

## 笔记风格规则

主日更笔记统一采用新的生产化风格：

- 必须说明今日目标和核心概念；
- 必须补充“生产实际”，默认使用金融信贷业务例子；
- 必须沉淀面试问题和术语；
- 必须保留“每日核心问题自测”；
- 每日自测固定 10 个：A 区今日核心问题 7 个，B 区前三天核心回顾 3 个；
- 每道面试沉淀题和核心自测题都必须写 `重要程度：x/5`；
- 用户回答后，每题必须按“回答评价 -> 评分 -> 参考答案”补齐，评分格式为 `评分：x/10`；
- 每 7 天复盘日要额外包含周回顾问题。

索引、术语表、架构长文这类非日更笔记不强行套每日自测， 但必须说明自身定位、适用范围和维护规则。

## 专题补强笔记

- [金融信贷离线/实时仓库如何支撑 Agent](./offline_warehouse_agent_basics.md)
- [LangChain / LangGraph / LangSmith 学习](./lang_series_framework_learning.md)
- [Day55+ LangChain / LangGraph / LangSmith 学习计划](../docs/day55_plus_langchain_langgraph_langsmith_learning_plan.md)

## 每日学习笔记

- [Day 1 - 定位与环境搭建](./day01_environment_setup.md)
- [Day 2 - Python 基础补齐](./day02_python_basics.md)
- [Day 3 - 数据处理基础](./day03_data_processing.md)
- [Day 4 - HTTP 与 API](./day04_http_api.md)
- [Day 5 - FastAPI 入门](./day05_fastapi.md)
- [Day 6 - 工程化基础](./day06_engineering.md)
- [Day 7 - 第 1 周复盘](./day07_week1_review.md)
- [Day 8 - LLM 基础概念](./day08_llm_basics.md)
- [Day 9 - Prompt 实战](./day09_prompt_practice.md)
- [Day 10 - 结构化输出](./day10_structured_output.md)
- [Day 11 - Tool Use](./day11_tool_use.md)
- [Day 12 - SQL 解释助手 CLI](./day12_sql_explainer_cli.md)
- [Day 13 - SQL 解释助手强化](./day13_sql_explainer_enhancement.md)
- [Day 14 - 第 2 周复盘](./day14_week2_review.md)
- [第 3 周前补齐清单](./day14_week3_prerequisites_review.md)
- [Day 15 - RAG 准备](./day15_rag_preparation.md)
- [Day 16 - RAG 基础](./day16_rag_basics.md)
- [Day 17 - RAG 知识入库](./day17_rag_ingestion.md)
- [Day 18 - RAG 检索与引用](./day18_rag_retrieval_citations.md)
- [Day 19 - RAG 召回优化](./day19_rag_retrieval_optimization.md)
- [Day 20 - RAG 问答 API](./day20_rag_api.md)
- [Day 21 - RAG 项目收口](./day21_rag_project_review.md)
- [Day 22 - Query Rewrite](./day22_query_rewrite.md)
- [Day 23 - RAG 测试集](./day23_rag_eval_testset.md)
- [Day 24 - 幻觉控制：拒答与边界](./day24_hallucination_guardrails.md)
- [Day 25 - 权限与安全：敏感信息控制](./day25_security_controls.md)
- [Day 26 - 性能与成本：缓存与上下文控制](./day26_rag_performance_cost.md)
- [Day 27 - 项目 2 打磨：演示与稳定性](./day27_rag_demo_stability.md)
- [Day 28 - 第 4 周复盘与试投启动](./day28_week4_review_application.md)
- [Day 29 - NL2SQL 准备：Schema 与问题类型](./day29_nl2sql_schema_preparation.md)
- [Day 30 - NL2SQL 问题解析：指标、维度、时间抽取](./day30_nl2sql_question_parser.md)
- [Day 31 - NL2SQL SQL 生成：从结构化解析到只读 SQL](./day31_nl2sql_sql_generation.md)
- [Day 32 - NL2SQL SQL 校验：风控与约束](./day32_nl2sql_sql_validation.md)
- [Day 33 - NL2SQL 查询执行：结果返回与格式化](./day33_nl2sql_query_execution.md)
- [Day 34 - NL2SQL 结果解释：业务语言化](./day34_nl2sql_result_interpretation.md)
- [Day 35 - 项目 3 整合：NL2SQL 助手成型](./day35_nl2sql_project_integration.md)
- [Day 36 - 后端重构：项目服务化](./day36_backend_refactor.md)
- [Day 37 - 接口设计：错误处理与响应规范](./day37_api_design.md)
- [Day 38 - Docker 化：本地部署](./day38_dockerization.md)
- [Day 39 - 配置管理：环境隔离与密钥管理](./day39_config_management.md)
- [Day 40 - 数据存储：SQLite、Postgres 与审计数据](./day40_storage_selection.md)
- [Day 41 - 测试基础：接口测试与回归](./day41_testing_regression.md)
- [Day 42 - 周复盘与部署说明：像产品一样交付](./day42_week6_delivery_review.md)
- [Day 43 - Agent 思路：流程编排](./day43_agent_workflow.md)
- [Day 44 - 工具协同：多工具调用策略](./day44_tool_orchestration.md)
- [Day 45 - Agent 评测：离线/实时仓库评测样例](./day45_e2e_evaluation.md)
- [Day 46 - 错误治理：Prompt 与逻辑修正](./day46_error_governance.md)
- [Day 47 - 离线仓库分层：ODS/DWD/DWS/ADS 与 Agent 离线路由](./day47_offline_warehouse_routing.md)
- [Day 48 - 实时仓库基础：事件时间、窗口、延迟与 Agent 实时路由](./day48_realtime_warehouse_routing.md)
- [Day 49 - 信贷主题域：授信/额度/风控/放款/还款/逾期与 Agent 意图识别](./day49_credit_domain_intent.md)
- [Day 50 - 指标字典：离线/实时指标口径与 RAG 问答](./day50_metric_dictionary_rag.md)
- [Day 51 - Schema Catalog：工具注册表与 Agent 调用约束](./day51_schema_catalog_tool_registry.md)
- [Day 52 - 数据血缘：Agent 可追溯与影响分析](./day52_data_lineage_agent_traceability.md)
- [Day 53 - 离线 NL2SQL：SQL 安全、分区裁剪与执行控制](./day53_offline_nl2sql_sql_safety.md)
- [Day 54 - 实时指标查询：告警解释、延迟状态与证据来源](./day54_realtime_metric_alert_explanation.md)
- [Day 55 - 日报 + 实时告警 Agent：多工具编排、摘要生成与审计](./day55_daily_report_realtime_alert_agent.md)
- [Day 56 - 仓库 Agent 端到端评测：回归、拒答与异常场景](./day56_warehouse_agent_e2e_evaluation.md)
- [Day 57 - 数据质量 + 错误治理：空值、重复、乱序、补偿与回归](./day57_data_quality_error_governance.md)
- [Day 58 - 服务化 + 审计存储：API 契约、request_id、trace 回放](./day58_service_api_audit_storage.md)
- [Day 59 - 综合项目集成：统一离线/实时仓库 Agent 入口](./day59_integrated_project_integration.md)
- [Day 60 - 项目演示 + 作品集包装：3 分钟讲清综合项目](./day60_project_demo_portfolio_packaging.md)
- [Day 61 - SQL / Python / 仓库面试：用工程语言讲项目实现](./day61_sql_python_warehouse_interview.md)
- [Day 62 - Agent / AI 应用模拟面试：RAG、NL2SQL、评测、安全深挖](./day62_agent_ai_application_mock_interview.md)
- [Day 63 - 收官与精准投递：项目卖点、简历表达和岗位匹配](./day63_final_review_targeted_delivery.md)
