# Day55+ LangChain / LangGraph / LangSmith 学习计划

## 定位

这份计划是 Day55 之后的 Agent 工程化补强线，服务于当前“金融信贷离线/实时仓库 + Agent”项目。

三者分工：

- LangChain：统一模型、Prompt、Tool、结构化输出和基础 Agent 调用；
- LangGraph：把 Agent 流程做成可控状态机，支持路由、重试、人工审核、持久化和回放；
- LangSmith：记录 trace、调试链路、构造评测集、对比版本和沉淀线上问题。

学习目标不是“会调用框架”，而是把现有项目里的口径问答、NL2SQL、实时告警、日报生成、血缘追溯、安全审计改造成可观察、可评测、可演示的准生产 Agent。

## Day55+ 每日安排

| Day | 主题 | 学习重点 | 项目落地点 | 交付物 |
|-----|------|----------|------------|--------|
| 55 | LangChain 基础接入 | ChatModel、Prompt、Tool、结构化输出、工具描述 | 把日报 + 实时告警 Agent 的本地函数包装成标准工具 | LangChain 工具注册清单和调用 Demo |
| 56 | LangChain 工具路由 | 多工具选择、输入 schema、错误返回、fallback | 口径问答、离线 SQL、实时告警、血缘查询统一接入 Agent | 多工具路由样例和 bad case |
| 57 | LangGraph 状态机 | State、Node、Edge、条件路由、END、可恢复流程 | 把“意图识别 -> 权限校验 -> 工具调用 -> 结果校验 -> 审计”做成图 | Agent 流程图和 LangGraph Demo |
| 58 | LangGraph 生产控制 | 重试、人工审核、失败分支、状态持久化、回放 | 对高风险 SQL、敏感字段、实时延迟告警加入拦截和人工确认节点 | 可回放的审计链路和异常分支报告 |
| 59 | LangSmith tracing | trace、run、metadata、tag、输入输出脱敏 | 每次 Agent 调用记录 request_id、user_id、tool_name、latency、cost | trace 字段规范和本地审计映射表 |
| 60 | LangSmith evaluation | dataset、evaluator、回归集、版本对比 | 建立口径问答、NL2SQL、实时告警解释、拒答安全评测集 | Agent 评测报告和版本对比 |
| 61 | 框架化综合集成 | LangChain + LangGraph + LangSmith 串联 | 重构综合项目主流程，保留本地可运行 fallback | 准生产 Agent 编排 README |
| 62 | 面试表达与架构复盘 | 框架选型、边界、成本、稳定性、安全 | 准备“为什么不用纯 Chain、为什么要状态机、为什么要 tracing” | 高频面试问答 |
| 63 | 作品集收口 | 演示脚本、架构图、部署说明、风险说明 | 把三件套能力写入最终项目介绍和简历条目 | 最终演示稿和简历项目描述 |

## 学习顺序

1. 先学 LangChain，不急着复杂编排。
   重点是把模型调用、工具调用、结构化输出和 Prompt 管起来。

2. 再学 LangGraph。
   重点是让 Agent 流程从“一个大函数”变成“可检查的状态机”。金融信贷场景里，权限校验、SQL 安全、敏感字段拦截、实时延迟判断都应该是显式节点。

3. 最后接 LangSmith。
   重点是把每次调用留下证据：用户问了什么、走了哪个节点、调用了哪个工具、用了哪个模型、耗时多少、为什么拒答、评测是否通过。

## 和现有项目的对应关系

| 现有能力 | LangChain 改造 | LangGraph 改造 | LangSmith 观测 |
|----------|----------------|----------------|----------------|
| 指标口径 RAG | Retriever Tool | 口径解释节点 | 命中文档、引用、拒答原因 |
| 离线 NL2SQL | SQL Tool | SQL 生成、校验、执行分支 | SQL、扫描范围、拦截原因 |
| 实时告警解释 | Realtime Alert Tool | 实时窗口和延迟状态分支 | 告警等级、窗口、证据 |
| 血缘追溯 | Lineage Tool | 影响分析节点 | 来源表、下游、trace_id |
| 日报生成 | Report Tool | 多工具聚合和摘要节点 | 每段摘要来源和版本 |
| 权限安全 | Guardrail Tool | 权限校验和人工审核节点 | 拒答、脱敏、越权证据 |

## 准生产交付标准

- 所有工具都有名称、描述、输入 schema、输出 schema、错误码和审计字段；
- 所有高风险流程都有显式节点，不把权限、安全和 SQL 校验藏在 Prompt 里；
- 所有 Agent 调用都有 request_id、trace_id、user_id、scenario、model_id、tool_name、latency_ms、status；
- 所有评测样例至少覆盖成功、缺少条件、权限不足、实时延迟、SQL 风险、资料不足和工具异常；
- 所有回答都能说明来源，不能把模型推测当成事实。

## 参考资料

- LangChain 官方文档：https://docs.langchain.com/oss/python/langchain/overview
- LangGraph 官方文档：https://docs.langchain.com/oss/python/langgraph/overview
- LangSmith 官方文档：https://docs.langchain.com/langsmith/home
