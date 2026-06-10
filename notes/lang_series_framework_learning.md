# 专题补强 - LangChain / LangGraph / LangSmith 学习

## 学习目标

这篇笔记用于系统学习 Lang 系列框架，并把它们应用到“金融信贷离线/实时仓库 + Agent”项目。

学习完成后，需要能够回答：

- LangChain、LangGraph、LangSmith 分别解决什么问题；
- 什么场景只需要 LangChain，什么场景应该使用 LangGraph；
- 如何把模型、Prompt、工具和结构化输出统一管理；
- 如何设计带权限校验、失败回退、人工审核和审计的 Agent 状态机；
- 如何通过 tracing 和 evaluation 定位问题、验证版本效果；
- 如何避免为了使用框架而增加不必要的复杂度。

---

## 三个框架的定位

| 框架 | 核心定位 | 主要能力 | 在当前项目中的作用 |
|------|----------|----------|--------------------|
| LangChain | LLM 应用组件和 Agent 开发框架 | 模型接入、Prompt、Tool、Retriever、结构化输出、Agent | 把口径问答、NL2SQL、实时告警、血缘查询包装成标准工具 |
| LangGraph | 有状态 Agent 工作流编排框架 | State、Node、Edge、条件路由、持久化、重试、人工介入 | 编排权限校验、工具路由、SQL 安全、结果验证和审计流程 |
| LangSmith | LLM 应用观测和评测平台 | tracing、debug、dataset、evaluation、版本对比 | 追踪每次调用，沉淀 bad case，执行回归评测 |

一句话理解：

```text
LangChain 负责组装能力；
LangGraph 负责控制流程；
LangSmith 负责观察、调试和评测。
```

---

## LangChain 学习重点

### 1. 模型统一接入

LangChain 用统一接口封装不同模型提供方。业务代码不应该到处直接调用模型 API，而应该通过统一的模型配置和适配层调用。

需要掌握：

- Chat Model 的初始化和调用；
- system、user、assistant 消息的区别；
- temperature、超时、重试和 token 限制；
- 模型注册、模型路由和 fallback；
- 敏感配置通过环境变量管理。

### 2. Prompt 模板

Prompt 不应该散落在业务代码中。生产项目需要记录 Prompt 的用途、输入变量、输出约束和版本。

金融信贷场景中的 Prompt 必须明确：

- 只能根据工具结果和证据回答；
- 不允许编造指标变化原因；
- 不允许泄露客户敏感信息；
- 数据延迟或口径不明确时必须说明限制；
- 输出必须符合定义好的结构。

### 3. 结构化输出

结构化输出用于让模型返回稳定字段，而不是返回难以解析的自由文本。

示例输出：

```json
{
  "intent": "realtime_alert_query",
  "risk_level": "medium",
  "required_tools": ["realtime_alert_tool"],
  "need_human_review": false
}
```

生产中仍然需要执行 schema 校验，不能因为模型声称返回 JSON 就直接信任结果。

### 4. Tool

Tool 是 Agent 可以调用的受控业务能力。每个 Tool 都应该有：

- 清晰且唯一的名称；
- 面向模型的准确描述；
- 严格的输入和输出 schema；
- 权限、超时、重试和错误处理；
- request_id、trace_id、耗时和结果状态等审计字段。

当前项目可以封装的工具：

```text
metric_definition_tool       指标口径查询
offline_nl2sql_tool          离线指标查询
realtime_alert_tool          实时告警查询
lineage_query_tool           数据血缘追溯
permission_check_tool        权限校验
daily_report_tool            日报生成
```

### 5. LangChain 使用边界

LangChain 适合封装模型和工具，也适合较简单的 Agent 调用。

当流程包含大量条件分支、状态保存、失败恢复、人工审核或长时间任务时，不应该继续把逻辑堆在一个 Chain 或 Agent Prompt 中，应该使用 LangGraph 显式编排。

---

## LangGraph 学习重点

### 1. State

State 保存工作流执行过程中需要共享的数据。

金融信贷 Agent 的状态可以包含：

```python
class AgentState:
    request_id: str
    user_id: str
    question: str
    intent: str
    permissions: list[str]
    selected_tool: str
    tool_result: dict
    risk_level: str
    final_answer: str
    error: str | None
```

State 中不应该无限保存原始数据和敏感信息，需要控制字段、大小和保留周期。

### 2. Node

Node 是流程中的一个明确步骤。每个节点应该只负责一类任务，便于测试、重试和审计。

推荐节点：

```text
parse_intent
check_permission
select_tool
validate_tool_input
execute_tool
validate_result
human_review
generate_answer
write_audit_log
```

### 3. Edge 和条件路由

Edge 定义节点之间如何流转。条件路由根据当前 State 决定下一步。

示例：

```text
权限不足 -> 拒答节点
SQL 风险过高 -> 人工审核节点
实时数据延迟 -> 降级说明节点
工具执行失败 -> 重试或 fallback 节点
结果校验通过 -> 回答生成节点
```

### 4. 持久化与恢复

生产 Agent 需要能够保存执行状态。当工具超时、服务重启或等待人工审核时，可以从检查点继续执行，而不是重新运行整个流程。

需要关注：

- thread_id 和 request_id 的关系；
- checkpoint 保存位置和保留周期；
- 恢复执行是否会重复调用有副作用的工具；
- 重试时如何保证幂等；
- 敏感状态如何脱敏和加密。

### 5. Human-in-the-loop

高风险操作不能完全交给模型自动决定。

以下场景可以进入人工审核：

- 查询涉及敏感客户明细；
- SQL 扫描范围或成本超过阈值；
- 模型试图调用未授权工具；
- 告警要求执行外部通知或业务动作；
- 多个数据源结果冲突，无法自动判断。

---

## LangSmith 学习重点

### 1. Tracing

Tracing 用于记录一次请求经过了哪些模型、节点和工具。

建议记录：

```text
request_id
trace_id
user_id 或脱敏用户标识
scenario
model_id
prompt_version
node_name
tool_name
latency_ms
token_usage
estimated_cost
status
error_type
```

金融场景中不能直接把手机号、身份证号、银行卡号、客户名单或完整 SQL 查询结果上传到外部观测平台。接入前必须完成脱敏和数据合规评估。

### 2. Debug

出现错误时，不只看最终答案，还要定位：

- 意图识别是否错误；
- 路由是否选错工具；
- Tool 输入是否缺少必要条件；
- SQL 是否被安全校验拦截；
- 工具结果是否为空或延迟；
- 模型是否忽略证据；
- Prompt、模型或工具版本是否发生变化。

### 3. Dataset

Dataset 是稳定的评测样例集合。每条样例应该包含输入、预期行为和判断标准。

当前项目至少需要覆盖：

- 正常指标口径问答；
- 离线 NL2SQL 查询；
- 实时告警解释；
- 数据血缘追溯；
- 缺少时间范围，需要追问；
- 权限不足，必须拒答；
- 实时链路延迟，必须降级说明；
- SQL 包含危险操作，必须拦截；
- 找不到证据，不能编造答案；
- 工具异常，必须返回可审计错误。

### 4. Evaluation

评测不能只比较文本是否完全相同，还应该按业务目标拆分指标：

| 评测维度 | 判断重点 |
|----------|----------|
| 路由准确率 | 是否选择了正确工具 |
| 参数完整率 | 时间、指标、维度等参数是否完整 |
| SQL 安全通过率 | 是否阻止危险或越权 SQL |
| 证据一致性 | 回答是否忠于工具结果 |
| 拒答准确率 | 无权限或无证据时是否正确拒答 |
| 延迟与成本 | 响应时间和模型成本是否符合阈值 |
| 审计完整率 | 是否留下必要 trace 和审计字段 |

---

## 推荐学习顺序

### 第一阶段：LangChain 组件化

目标：把现有 Python 函数包装成标准 Tool，并使用结构化输出完成意图识别。

练习：

1. 包装指标口径查询 Tool；
2. 包装实时告警查询 Tool；
3. 定义统一输入和输出 schema；
4. 增加超时、异常和审计字段；
5. 编写正常、缺参和越权测试。

### 第二阶段：LangGraph 流程化

目标：把手写 Agent 主流程改造成可检查、可恢复的状态机。

练习：

1. 创建 AgentState；
2. 实现意图识别、权限校验、工具执行、结果校验和审计节点；
3. 增加条件路由；
4. 增加失败重试和 fallback；
5. 为高风险 SQL 增加人工审核节点。

### 第三阶段：LangSmith 可观测与评测

目标：让每次 Agent 执行可追踪，让每次代码或 Prompt 修改可评测。

练习：

1. 接入 tracing；
2. 设置 metadata 和 tags；
3. 对敏感输入和工具结果脱敏；
4. 建立回归评测集；
5. 对比不同 Prompt、模型和路由策略。

### 第四阶段：综合交付

目标：形成可演示、可解释、可审计的准生产 Agent。

最终演示流程：

```text
用户问题
  -> LangGraph 意图识别节点
  -> 权限校验节点
  -> LangChain Tool 调用
  -> 结果安全校验
  -> 回答生成
  -> 审计记录
  -> LangSmith trace 和评测
```

---

## 常见误区

- 为了使用框架，把简单函数调用改造成过度复杂的 Agent；
- 只依赖 Tool 描述和 Prompt 做权限控制；
- 把 SQL 校验、敏感字段拦截等确定性规则交给模型；
- 使用 LangGraph，但所有逻辑仍然集中在一个大节点中；
- 接入 tracing，却没有 request_id、业务标签和错误分类；
- 只评测最终答案，不评测路由、工具参数、安全和拒答；
- 将敏感业务数据直接发送到外部观测平台；
- 只会写 Demo，不考虑超时、重试、幂等、成本和审计。

---

## 面试表达

### 为什么使用 LangGraph，而不是只使用 LangChain？

参考回答：

> LangChain 适合统一模型、Prompt 和 Tool 调用。金融信贷 Agent 包含权限校验、SQL 安全、实时延迟判断、失败回退和人工审核等明确流程，因此我使用 LangGraph 把这些步骤建模为可测试、可恢复、可审计的状态机，避免把关键控制逻辑隐藏在 Prompt 中。

### LangSmith 解决了什么问题？

参考回答：

> LangSmith 用于记录模型、节点和工具调用链路，并支持基于数据集执行回归评测。它能帮助定位问题发生在意图识别、工具路由、参数生成、工具执行还是答案生成阶段。金融场景接入时还需要做好输入输出脱敏和合规评估。

### 使用框架后还需要自己实现什么？

参考回答：

> 框架提供组件、编排和观测能力，但业务权限、SQL 安全、数据口径、错误码、审计规范、幂等和合规控制仍然需要项目自己实现。不能把业务正确性和安全责任交给框架或模型。

---

## 核心问题自测

1. LangChain、LangGraph、LangSmith 分别解决什么问题？
2. 什么情况下只使用 LangChain 就足够？
3. 为什么金融信贷 Agent 的权限校验和 SQL 安全应该设计成显式节点？
4. AgentState 中应该保存哪些字段，哪些敏感数据不应该长期保存？
5. Tool 为什么必须定义输入输出 schema 和错误码？
6. 如何避免工作流重试导致工具重复执行？
7. 什么情况下应该进入 human-in-the-loop？
8. LangSmith tracing 应该记录哪些业务字段？
9. 为什么 Agent 评测不能只判断最终答案文本？
10. 如何保证 LangSmith 接入不泄露金融敏感数据？

## 官方资料

- LangChain：https://docs.langchain.com/oss/python/langchain/overview
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
- LangSmith：https://docs.langchain.com/langsmith/home
