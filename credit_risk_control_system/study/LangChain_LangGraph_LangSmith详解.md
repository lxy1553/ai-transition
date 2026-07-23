# LangChain + LangGraph + LangSmith 最详细讲解

> 一份面向 AI 应用开发的系统学习资料，涵盖原理、代码、项目应用和面试要点。

---

## 目录

1. [三者的关系全景图](#三者的关系全景图)
2. [LangChain — LLM 应用开发框架](#langchain--llm-应用开发框架)
3. [LangGraph — 有状态多智能体编排框架](#langgraph--有状态多智能体编排框架)
4. [LangSmith — LLM 应用可观测性平台](#langsmith--llm-应用可观测性平台)
5. [项目实战：风控系统中的完整应用](#项目实战风控系统中的完整应用)
6. [面试高频考点 & 深度回答](#面试高频考点--深度回答)

---

## 三者的关系全景图

```
                         ┌───────────────────────────────────────┐
                         │           LangSmith                    │
                         │     (可观测性 / 调试 / 评估平台)         │
                         │                                        │
                         │   ┌─────────────────────────────────┐ │
                         │   │        LangGraph                  │ │
                         │   │   (有状态编排 / Agent 协作)         │ │
                         │   │  ┌───────────────────────────┐   │ │
                         │   │  │       LangChain            │   │ │
                         │   │  │   (组件 / 链式调用 / 工具)   │   │ │
                         │   │  │                             │   │ │
                         │   │  │  · ChatModel (LLM封装)      │   │ │
                         │   │  │  · PromptTemplate (模板)    │   │ │
                         │   │  │  · Tool (工具定义)           │   │ │
                         │   │  │  · VectorStore (向量库)      │   │ │
                         │   │  │  · Retriever (检索器)        │   │ │
                         │   │  │  · Chain/LCEL (链式编排)     │   │ │
                         │   │  └───────────────────────────┘   │ │
                         │   │                                   │ │
                         │   │  · StateGraph (状态图编排)         │ │
                         │   │  · Node (节点/步骤)                │ │
                         │   │  · Edge (边/路由)                  │ │
                         │   │  · Checkpointer (持久化/记忆)      │ │
                         │   │  · Human-in-the-loop              │ │
                         │   │  · Subgraph (子图嵌套)             │ │
                         │   └─────────────────────────────────┘ │
                         │                                        │
                         │  · Trace (全链路追踪)                   │
                         │  · Dataset (评估数据集)                 │
                         │  · Experiment (对比实验)                │
                         │  · Monitor (线上监控)                   │
                         │  · Annotation (人工标注反馈)            │
                         └───────────────────────────────────────┘
```

**一句话记忆**：
- **LangChain** = 给你 LLM 开发的乐高积木（组件层）
- **LangGraph** = 给你把积木搭成智能工作流的图纸（编排层）
- **LangSmith** = 给你监控整个搭积木过程的摄像头（可观测层）

---

## LangChain — LLM 应用开发框架

### 1. 你遇到的问题（没有它之前）

> 场景：你要做一个能调用公司内部 API 查询客户信用分的 AI 助手。

**裸写方案的痛苦**：

```python
# 没有 LangChain 时，你需要手写这一切
import openai

def query_credit_score(user_id: str) -> dict:
    """调用内部信用分接口"""
    # 自己处理 HTTP 请求、鉴权、重试、序列化
    response = requests.post(
        "https://internal-api/credit/score",
        json={"user_id": user_id}
    )
    return response.json()

def chat_with_tools(user_message: str, chat_history: list):
    """手动管理 tool calling 的完整流程"""

    # 1. 手动构造 system prompt
    system_prompt = "你是信用评估助手..."

    # 2. 手动拼接对话历史
    messages = [{"role": "system", "content": system_prompt}] + chat_history
    messages.append({"role": "user", "content": user_message})

    # 3. 手动定义 function schema（老方式，还要手写 JSON Schema）
    tools = [{
        "type": "function",
        "function": {
            "name": "query_credit_score",
            "description": "查询用户信用分",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户ID"}
                },
                "required": ["user_id"]
            }
        }
    }]

    # 4. 调用 LLM
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=tools
    )

    msg = response.choices[0].message

    # 5. 手动循环处理 tool calls（可能要多次）
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            # 6. 手动路由到对应函数
            if func_name == "query_credit_score":
                result = query_credit_score(user_id=args["user_id"])
            elif func_name == "something_else":
                result = ...
            # ... 每新增一个工具就要加一个 elif

            # 7. 手动构造 tool result 消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

        # 8. 再次调用 LLM 获取最终回复
        final_response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return final_response.choices[0].message.content

    return msg.content
```

**痛点总结**：
| 痛点        | 说明                           |
|------------|------------------------------|
| 模板管理混乱    | 提示词字符串散落各处，没有版本管理            |
| LLM 切换困难  | 换一个模型就要重写 API 调用代码           |
| 工具调用繁琐    | 手写 JSON Schema，手动路由，手动拼接消息   |
| 没有记忆管理    | 对话历史手动维护，没有自动截断/摘要           |
| 无法流式输出    | 如果要 streaming，需要手写生成器逻辑      |
| 工具链不统一    | 每个中间件（缓存、重试、限流）都要自己实现        |
| 无法组合复用    | 一段处理逻辑写完就焊死，下一个项目重写          |

---

### 2. LangChain 如何解决

```
            ┌────────────────────────────────────────────────┐
            │              LangChain 六大核心模块              │
            │                                                 │
            │  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
            │  │  Model   │  │ Prompt   │  │   Retriever  │ │
            │  │  I/O     │  │ Template │  │   + Index    │ │
            │  │          │  │          │  │              │ │
            │  │ 统一调用  │  │ 模板管理  │  │ 向量库/RAG   │ │
            │  │ 任意LLM  │  │ 变量注入  │  │ 检索增强生成  │ │
            │  └──────────┘  └──────────┘  └──────────────┘ │
            │                                                 │
            │  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
            │  │  Chain   │  │  Agent   │  │   Callback   │ │
            │  │  / LCEL  │  │  + Tool  │  │   System     │ │
            │  │          │  │          │  │              │ │
            │  │ 组合能力  │  │ 规划执行  │  │ 钩子/日志    │ │
            │  │ 管道编排  │  │ 工具调用  │  │ 可观测性     │ │
            │  └──────────┘  └──────────┘  └──────────────┘ │
            └────────────────────────────────────────────────┘
```

#### 模块一：Model I/O — 统一 LLM 调用接口

```python
# ========== LangChain 方式 ==========
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatTongyi  # 通义千问

# 只需改这一行，其余代码不变
llm = ChatOpenAI(model="gpt-4o", temperature=0)        # OpenAI
# llm = ChatAnthropic(model="claude-sonnet-5")         # Anthropic
# llm = ChatTongyi(model="qwen-max")                   # 阿里通义

# 同步调用
response = llm.invoke("你好")
print(response.content)

# 流式调用
for chunk in llm.stream("写一首诗"):
    print(chunk.content, end="", flush=True)

# 批量调用（自动并发）
results = llm.batch(["翻译: Hello", "翻译: World"])
```

#### 模块二：Prompt Template — 模板管理与复用

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 定义可复用的提示词模板
credit_assessment_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是银行信用风险评估专家。
    评估规则：
    1. 信用分 < 600：高风险
    2. 信用分 600-700：中风险
    3. 信用分 > 700：低风险

    当前时间：{current_time}
    可用工具：{tool_names}
    """),
    MessagesPlaceholder(variable_name="history"),  # 自动管理对话历史
    ("human", "{user_input}"),
])

# 使用时注入变量
formatted = credit_assessment_prompt.invoke({
    "current_time": "2026-07-07",
    "tool_names": "query_credit_score, analyze_transaction",
    "history": chat_history,
    "user_input": "用户 12345 的信用情况如何？"
})

# 多场景复用
# 场景A：只改变量，模板不动
prompt_a = credit_assessment_prompt.invoke({
    "current_time": "2026-07-07",
    "tool_names": "query_credit_score",
    "history": [],
    "user_input": "评估用户 A"
})

# 场景B：从 YAML 文件加载（生产常用）
# prompts/credit_assessment.yaml
"""
system: |
  你是信用评估专家。
  规则：{rules}
history: {history}
human: {user_input}
"""
```

#### 模块三：Tool / Agent — 自动工具调用引擎

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ========== 方式1：装饰器定义工具 ==========
@tool
def query_credit_score(user_id: str) -> dict:
    """查询用户在央行征信系统的信用分。

    Args:
        user_id: 用户唯一标识，格式为 "UID-XXXX"
    """
    # LLM 会自动调用这个函数
    score = credit_db.query(user_id)
    return {"user_id": user_id, "score": score, "level": get_risk_level(score)}

# ========== 方式2：Pydantic 定义结构化工具（生产推荐）==========
class CreditScoreInput(BaseModel):
    """信用分查询参数"""
    user_id: str = Field(description="用户ID，格式: UID-XXXX")
    include_history: bool = Field(default=False, description="是否包含历史信用记录")

class AnalyzeTransactionInput(BaseModel):
    """交易分析参数"""
    user_id: str = Field(description="用户ID")
    start_date: str = Field(description="开始日期 YYYY-MM-DD")
    end_date: str = Field(description="结束日期 YYYY-MM-DD")

@tool(args_schema=CreditScoreInput)
def query_credit_score_v2(user_id: str, include_history: bool = False) -> str:
    """查询用户信用分及可选的历史记录"""
    # ... 实现
    return f"用户 {user_id} 信用分: 680"

@tool(args_schema=AnalyzeTransactionInput)
def analyze_transaction_pattern(user_id: str, start_date: str, end_date: str) -> str:
    """分析用户交易模式，识别异常行为"""
    # ... 实现
    return f"检测到 3 笔异常交易"

# ========== 绑定工具到 LLM ==========
tools = [query_credit_score_v2, analyze_transaction_pattern]
llm_with_tools = llm.bind_tools(tools)

# LLM 会自动决定：什么时候需要调用工具、调用哪个、传什么参数
response = llm_with_tools.invoke("用户 UID-1234 最近信用怎么样？")
# response.tool_calls = [
#     {"name": "query_credit_score_v2", "args": {"user_id": "UID-1234"}}
# ]
```

#### 模块四：LCEL（LangChain Expression Language）— 链式编排

```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# LCEL 使用 | 管道符，像 Unix 管道一样串联组件
# 语法: component_a | component_b | component_c

# ========== 示例：RAG 问答链 ==========
from langchain_core.output_parsers import StrOutputParser

# 定义每个环节
retrieve_docs = lambda query: vector_store.similarity_search(query, k=5)

def format_context(docs):
    return "\n\n".join(f"【文档{i}】{doc.page_content}" for i, doc in enumerate(docs, 1))

rag_chain = (
    # 环节1：检索相关文档 + 原始问题并行传递
    {
        "context": RunnableLambda(retrieve_docs) | RunnableLambda(format_context),
        "question": RunnablePassthrough()  # 原样传递
    }
    # 环节2：注入到提示词
    | ChatPromptTemplate.from_messages([
        ("system", "根据以下参考资料回答问题：\n{context}"),
        ("human", "{question}")
    ])
    # 环节3：调用 LLM
    | llm
    # 环节4：解析输出
    | StrOutputParser()
)

# 调用
answer = rag_chain.invoke("信用风险评估模型的 AUC 最低要求是多少？")

# ========== LCEL 数据流图 ==========
# 输入: "信用风险评估模型的 AUC 最低要求是多少？"
#   │
#   ├──→ RunnableLambda(retrieve_docs) → RunnableLambda(format_context) → 注入为 context
#   │
#   └──→ RunnablePassthrough() ─────────────────────────────────────────→ 注入为 question
#                                    │
#                                    ↓
#                          ChatPromptTemplate
#                                    │
#                                    ↓
#                               ChatOpenAI
#                                    │
#                                    ↓
#                           StrOutputParser
#                                    │
#                                    ↓
#                          输出: "根据监管要求，AUC不应低于0.7..."
```

#### 模块五：Runnable 生命周期（Runtime 绑定）

```python
# LCEL 的所有组件都是 Runnable，都支持这些接口

# 1. 标准调用
result = chain.invoke({"query": "..."})

# 2. 批量调用（自动并发）
results = chain.batch([{"query": "q1"}, {"query": "q2"}, {"query": "q3"}])

# 3. 流式输出
for chunk in chain.stream({"query": "..."}):
    print(chunk)

# 4. 异步调用
result = await chain.ainvoke({"query": "..."})

# 5. 带回调的调用（接入 LangSmith）
with collect_runs() as cb:
    result = chain.invoke({"query": "..."})
    run_id = cb.traced_runs[0].id  # 获得 LangSmith trace ID

# 6. 绑定运行时配置（不修改链定义）
chain_with_config = chain.with_config({
    "run_name": "credit_eval_v2",     # 在 LangSmith 中的显示名称
    "tags": ["production", "v2"],
    "metadata": {"user_id": "12345"},
})
```

---

### 3. LangChain 在项目中的实际应用

```
风控系统中的一个典型 RAG 场景：

用户提问："这个客户的信用风险有多大？"
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  LangChain Chain (LCEL)                              │
│                                                       │
│  ① RunnableLambda: 查询客户基础信息 (姓名、年龄、地区)  │
│           │                                           │
│           ▼                                           │
│  ② VectorStoreRetriever: 在知识库中检索相似案例       │
│           │ (使用 Chroma/Faiss 向量库)                 │
│           ▼                                           │
│  ③ {context, question} → ChatPromptTemplate            │
│           │ 注入检索到的文档 + 用户问题                 │
│           ▼                                           │
│  ④ ChatOpenAI: 综合客户数据 + 案例库 → 评估结论        │
│           │                                           │
│           ▼                                           │
│  ⑤ PydanticOutputParser: 解析为结构化 RiskReport      │
│           │                                           │
│           ▼                                           │
│  输出: RiskReport(                                    │
│     risk_level="HIGH",                                │
│     score=580,                                        │
│     reasons=["多头借贷", "近期逾期"],                  │
│     similar_cases=[...]                               │
│  )                                                    │
└──────────────────────────────────────────────────────┘
```

**实际代码**：

```python
# credit_risk_control_system 中的 RAG 风险评估链
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class RiskReport(BaseModel):
    risk_level: str = Field(description="HIGH / MEDIUM / LOW")
    score: int = Field(description="信用分 300-850")
    reasons: list[str] = Field(description="风险原因列表")
    similar_cases: list[str] = Field(description="相似历史案例")

def build_credit_risk_chain(vector_store, llm):
    """构建信用风险 RAG 评估链"""

    parser = PydanticOutputParser(pydantic_object=RiskReport)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是银行信用风险评估专家。
        根据客户信息和相似历史案例，评估该客户的信用风险。

        {format_instructions}
        """),
        ("human", """客户信息: {customer_info}
        相似案例: {context}

        请评估该客户的信用风险。""")
    ]).partial(format_instructions=parser.get_format_instructions())

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    chain = (
        {
            "customer_info": RunnablePassthrough(),
            "context": lambda x: format_docs(retriever.invoke(x["query"]))
        }
        | prompt
        | llm
        | parser
    )

    return chain

# 使用
chain = build_credit_risk_chain(vector_store, llm)
report: RiskReport = chain.invoke({
    "query": "用户 138XXXX 信用情况"
})
print(f"风险等级: {report.risk_level}, 信用分: {report.score}")
```

---

## LangGraph — 有状态多智能体编排框架

### 1. LangChain 的局限性 → LangGraph 要解决的问题

> LangChain 的 LCEL 是做「线性 DAG」（有向无环图），但真实业务中很多流程是**有环**的、**有状态**、需要**条件跳转**的。

```
问题场景：风控审批中的"人机协同审核"

LCEL 能做（线性链）:           LangGraph 能做（有状态图）:
                              ┌─────────────────────────────────────────┐
  输入 → 初审 → 复审 → 输出    │              ┌──────────────┐           │
                              │     ┌───────→│   AI 初筛     │──┐       │
  但如果需要：                 │     │        └──────────────┘  │       │
  "初筛不通过→收集更多证据     │     │               │ 通过      │ 不通过 │
   →再筛→还不通过→转人工       │     │               ↓           ↓       │
   →人工批准→终审"             │  ┌──────────┐  ┌──────────┐          │
                              │  │  终审    │←─│  人工审核  │←─┐      │
  这种循环+条件跳转，LCEL      │  └──────────┘  └──────────┘  │      │
  做不到。                    │       │                          │      │
                              │       ↓              ┌──────────┐     │
                              │  输出审批结果      ┌─│收集补充材料│←──┘ │
                              │                    │ └──────────┘    │
                              │                    └─────────────────┘
                              └─────────────────────────────────────────┘
```

### 2. LangGraph 核心概念

```
LangGraph  =  状态机（State Machine） + 图（Graph） + 持久化（Checkpointer）

┌─────────────────────────────────────────────────────┐
│                   LangGraph 四大件                    │
│                                                      │
│  State  ──── 定义 Agent 在每一步中的记忆              │
│  Nodes  ──── 定义处理函数（每个节点做一件事）          │
│  Edges  ──── 定义节点之间如何流转                     │
│  Checkpointer ── 持久化每步的 State（支持回溯/恢复）   │
└─────────────────────────────────────────────────────┘
```

#### 核心概念一：State（状态定义）

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# ========== State = Agent 的"记忆" ==========
class CreditReviewState(TypedDict):
    """信用审核的完整状态"""

    # 对话消息
    messages: list[BaseMessage]

    # 业务数据
    user_id: str
    credit_score: int | None
    risk_level: str          # LOW / MEDIUM / HIGH

    # 流程控制
    review_stage: str        # initial / evidence / manual / final
    collected_evidence: list[str]
    manual_decision: str | None   # approve / reject

    # 计数器（防死循环）
    retry_count: int
```

#### 核心概念二：Node（节点/处理步骤）

```python
# ========== Node = 处理函数 ==========
# 每个 Node 接收 State，返回更新后的 State

def initial_screening(state: CreditReviewState) -> dict:
    """节点1：AI 初筛 - 查询信用分并给出初步判断"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 调用信用分查询工具
    score_result = query_credit_score(state["user_id"])

    # 让 LLM 综合判断
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是风控审核员，根据信用分判断风险等级"),
        ("human", "信用分: {score}，判断风险等级并给出理由")
    ])
    chain = prompt | llm
    result = chain.invoke({"score": score_result["score"]})

    return {
        "credit_score": score_result["score"],
        "risk_level": classify_risk(score_result["score"]),
        "messages": [AIMessage(content=result.content)],
        "review_stage": "evidence_collection"  # 进入下一阶段
    }

def collect_evidence(state: CreditReviewState) -> dict:
    """节点2：证据收集 - 分析交易记录、多头借贷等"""
    evidence = []

    # 分析交易记录
    transactions = analyze_transaction_pattern(state["user_id"])
    if transactions.get("anomalies"):
        evidence.extend(transactions["anomalies"])

    # 查询多头借贷
    multi_loan = check_multi_platform_loans(state["user_id"])
    if multi_loan.get("platform_count", 0) > 3:
        evidence.append(f"多头借贷: {multi_loan['platform_count']}个平台")

    # 查询司法记录
    judicial = check_judicial_records(state["user_id"])
    if judicial.get("has_record"):
        evidence.append(f"司法记录: {judicial['type']}")

    return {
        "collected_evidence": evidence,
        "review_stage": "risk_evaluation"
    }

def risk_evaluation(state: CreditReviewState) -> dict:
    """节点3：综合风险评估"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是风控总监，综合所有信息做出最终判断"),
        ("human", """
        信用分: {score}
        风险等级: {risk_level}
        证据: {evidence}

        判断：
        1. 是否可以通过？（approve / reject / need_manual）
        2. 是否需要转人工？
        """)
    ])

    chain = prompt | llm
    result = chain.invoke({
        "score": state["credit_score"],
        "risk_level": state["risk_level"],
        "evidence": "\n".join(state["collected_evidence"])
    })

    # 解析 LLM 输出
    decision = parse_decision(result.content)

    return {
        "messages": [AIMessage(content=result.content)],
        "review_stage": decision["next_stage"],  # manual_review or final_approval
        "retry_count": state.get("retry_count", 0) + 1
    }

def manual_review(state: CreditReviewState) -> dict:
    """节点4：人工审核 - 暂停等待人工输入"""
    # 这个节点会中断，等待 human-in-the-loop 输入
    # LangGraph 通过 interrupt 机制实现
    return {
        "review_stage": "waiting_for_human"
    }

def final_approval(state: CreditReviewState) -> dict:
    """节点5：最终审批"""
    return {
        "review_stage": "completed",
        "messages": [AIMessage(content=f"审批完成：{state.get('manual_decision', 'approved')}")]
    }
```

#### 核心概念三：Edge（路由/条件跳转）+ Graph 构建

```python
# ========== 构建完整的审核流程图 ==========

# 1. 创建 StateGraph
workflow = StateGraph(CreditReviewState)

# 2. 添加节点
workflow.add_node("initial_screening", initial_screening)
workflow.add_node("collect_evidence", collect_evidence)
workflow.add_node("risk_evaluation", risk_evaluation)
workflow.add_node("manual_review", manual_review)
workflow.add_node("final_approval", final_approval)

# 3. 设置入口
workflow.set_entry_point("initial_screening")

# 4. 添加边（路由逻辑）
workflow.add_edge("initial_screening", "collect_evidence")
workflow.add_edge("collect_evidence", "risk_evaluation")

# 5. 条件边：根据状态决定下一步
def route_after_evaluation(state: CreditReviewState) -> Literal["manual_review", "final_approval", "collect_evidence"]:
    """路由函数：决定下一步走哪个节点"""
    risk_level = state["risk_level"]
    evidence_count = len(state["collected_evidence"])
    retry_count = state.get("retry_count", 0)

    # 高风险 → 转人工
    if risk_level == "HIGH":
        return "manual_review"

    # 证据不足 + 中风险 → 重新收集证据（循环！这是 LCEL 做不到的）
    if risk_level == "MEDIUM" and evidence_count < 2 and retry_count < 3:
        print(f"⚠️ 证据不足，重新收集（第{retry_count}次重试）")
        return "collect_evidence"

    # 低风险 → 直接通过
    return "final_approval"

workflow.add_conditional_edges(
    "risk_evaluation",
    route_after_evaluation,
    {
        "manual_review": "manual_review",
        "final_approval": "final_approval",
        "collect_evidence": "collect_evidence"  # 回环！形成循环
    }
)

workflow.add_edge("manual_review", "final_approval")
workflow.add_edge("final_approval", END)

# 6. 编译（可选持久化）
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("credit_review_checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)
```

#### 核心概念四：Human-in-the-Loop（人机协同）

```python
# ========== 人工审核中断机制 ==========

# 方式1：使用 interrupt() 暂停（LangGraph 内置）
def manual_review_with_interrupt(state: CreditReviewState) -> dict:
    """等待人工审核员做决定"""
    # 这里卡住，等待外部输入
    # 人工审核员在 UI 上看到：风险等级 HIGH，证据：XX，请决定 approve/reject
    # 审核员点击后，LangGraph 恢复执行

    # 前端 WebSocket 接收 interrupt 事件，展示给审核员
    # 审核员提交后，通过 aupdate_state 恢复
    return {"review_stage": "waiting_for_human"}

# 方式2：编译时指定 interrupt_before
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["manual_review"]  # 执行这个节点前自动暂停
)

# ========== 恢复执行 ==========
# 外部系统（审核员操作后）：
config = {"configurable": {"thread_id": "credit-review-12345"}}

# 审核员批准
app.update_state(config, {"manual_decision": "approved"})

# 恢复执行（从暂停点继续）
result = app.invoke(None, config)
print(f"审核结果: {result['review_stage']}")  # completed
```

#### 核心概念五：Subgraph（子图嵌套 — 生产级架构）

```python
# ========== 子图：把复杂流程模块化 ==========

# 定义子图：交易异常检测流程
class TransactionAnalysisState(TypedDict):
    transactions: list
    anomalies: list
    risk_signals: list

def build_transaction_subgraph() -> StateGraph:
    """交易分析子图（作为大流程中的一个可复用模块）"""
    sg = StateGraph(TransactionAnalysisState)

    sg.add_node("fetch_transactions", fetch_user_transactions)
    sg.add_node("detect_anomalies", detect_transaction_anomalies)
    sg.add_node("classify_signals", classify_risk_signals)

    sg.set_entry_point("fetch_transactions")
    sg.add_edge("fetch_transactions", "detect_anomalies")
    sg.add_edge("detect_anomalies", "classify_signals")
    sg.add_edge("classify_signals", END)

    return sg.compile()

# 主流程中使用子图
workflow.add_node("transaction_analysis", build_transaction_subgraph())
```

---

### 3. LangGraph 完整流程图（风控审批 Agent）

```
                    ┌─────────────────────────────────────────────────┐
                    │        风控审批 Agent (LangGraph StateGraph)      │
                    │                                                  │
                    │              ┌──────────────────┐               │
                    │     START───→│  initial_screening│               │
                    │              │  (AI 初筛)        │               │
                    │              └────────┬─────────┘               │
                    │                       │                          │
                    │                       ▼                          │
                    │              ┌──────────────────┐               │
                    │              │ collect_evidence  │               │
                    │              │ (证据收集)         │               │
                    │              └────────┬─────────┘               │
                    │                       │                          │
                    │                       ▼                          │
                    │              ┌──────────────────┐               │
                    │     ┌────────│ risk_evaluation   │               │
                    │     │        │ (综合风险评估)     │               │
                    │     │        └──┬───────┬───────┘               │
                    │     │           │       │                        │
                    │     │   LOW风险  │       │  HIGH风险              │
                    │     │           │       │                        │
                    │     │           ▼       ▼                        │
                    │     │   ┌──────────┐ ┌──────────────┐           │
                    │     │   │  final   │ │ manual_review │           │
                    │     │   │ approval │ │ (人工审核)     │           │
                    │     │   └────┬─────┘ └──────┬───────┘           │
                    │     │        │               │                    │
                    │     │        │               │                    │
                    │     └──(循环)─┘               │                    │
                    │   MEDIUM + 证据不足            │                    │
                    │   → 回到 collect_evidence     ▼                    │
                    │                    ┌──────────────────┐           │
                    │                    │        END        │           │
                    │                    └──────────────────┘           │
                    │                                                  │
                    │  持久化: SqliteSaver 将每一步 state 写入 DB        │
                    │  可观测: LangSmith 自动追踪每步执行                │
                    │  人机协同: interrupt_before 等待人工输入            │
                    └─────────────────────────────────────────────────┘
```

---

### 4. LangGraph vs 传统方案

| 维度     | 传统 if-else 代码    | LCEL Chain   | LangGraph                  |
|---------|-------------------|---------------|----------------------------|
| 循环/回环  | ❌ 手动 while 循环管理  | ❌ 只支持 DAG    | ✅ 原生支持                     |
| 条件跳转   | 🤷 大量 if-elif     | 🔺 有限支持       | ✅ 条件边                      |
| 状态持久化  | ❌ 自己写 DB         | ❌ 无状态        | ✅ Checkpointer             |
| 中断恢复   | ❌ 极其复杂           | ❌ 不支持        | ✅ interrupt()              |
| 人机协同   | ❌ 自己实现           | ❌ 不支持        | ✅ 原生支持                     |
| 并行执行   | 🤷 需要 asyncio     | 🔺 Send API   | ✅ Send API                 |
| 可视化调试  | ❌                | 🔺 LangSmith  | ✅ LangSmith 图可视化           |
| 流式输出   | ❌                | ✅            | ✅ 支持 step-wise streaming   |

---

## LangSmith — LLM 应用可观测性平台

### 1. 你遇到的问题（没有它之前）

> 场景：你的风控 AI 上线了，但效果变差了。用户投诉"模型乱判断"。你怎么排查？

```
暗黑时刻：
- "这个用户为什么被判为高风险？" → 查日志，翻 10 个服务
- "新模型比旧模型好多少？"     → Excel 手动对比，不严谨
- "为什么这个场景延迟 5 秒？"    → 不知道卡在哪一步
- "Token 成本怎么翻倍了？"      → 月底看账单才发现
- "A/B 测试到底谁赢了？"        → 没有标准化评估框架
```

### 2. LangSmith 的核心能力

```
LangSmith = 全链路追踪 + 数据集管理 + 实验对比 + 线上监控 + 人工标注

┌──────────────────────────────────────────────────────────────┐
│                      LangSmith 五大功能模块                   │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Traces     │  │   Datasets   │  │   Experiments        │ │
│  │   全链路追踪  │  │   评估数据集   │  │   对比实验            │ │
│  │              │  │              │  │                      │ │
│  │ 每个调用的    │  │ 输入+期望输出  │  │ 同一数据集上跑       │ │
│  │ 完整运行记录: │  │ 的集合       │  │ 不同 Prompt/模型     │ │
│  │ · LLM 调用   │  │              │  │ 自动打分对比         │ │
│  │ · 工具调用   │  │ Example:     │  │                      │ │
│  │ · 检索查询   │  │ 问题→预期答案  │  │ v1 vs v2 盲测结果   │ │
│  │ · 延迟/Token │  │              │  │                      │ │
│  └─────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                               │
│  ┌─────────────────────────┐  ┌────────────────────────────┐ │
│  │   Annotation Queue       │  │   Online Evaluators        │ │
│  │   人工标注队列            │  │   线上自动评估              │ │
│  │                          │  │                            │ │
│  │ 审核员标注 AI 输出：      │  │ 自定义打分器自动运行：       │ │
│  │ · 正确 / 错误 / 部分正确  │  │ · 事实准确性               │ │
│  │ · 打分 1-5              │  │ · 回答相关性               │ │
│  │ · 写改进建议             │  │ · PII 泄露检测             │ │
│  └─────────────────────────┘  └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 功能一：Traces — 全链路追踪

```python
# ========== 接入 LangSmith ==========
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_xxxx"
os.environ["LANGCHAIN_PROJECT"] = "credit-risk-approval-v2"

# 设置了这些环境变量后，所有 LangChain/LangGraph 调用自动上报
# 无需修改任何业务代码！

# ========== 追踪效果 ==========
"""
在 LangSmith 平台上看到的 Trace（层级结构）：

┌─ Run: credit_risk_approval_v2 (7.2s, $0.042) ─────────────────────┐
│                                                                     │
│  ├─ ChatOpenAI (gpt-4o) — 0.8s, 450 tokens, $0.005               │
│  │   Input: "你是银行风控专家..."                                   │
│  │   Output: "根据信用分680，该客户为中风险..."                      │
│  │                                                                  │
│  ├─ Tool: query_credit_score — 1.2s                                │
│  │   Input: {"user_id": "UID-12345"}                               │
│  │   Output: {"score": 680, "level": "MEDIUM"}                     │
│  │                                                                  │
│  ├─ Tool: analyze_transaction_pattern — 2.1s                       │
│  │   Input: {"user_id": "UID-12345", "start": "...", "end": "..."} │
│  │   Output: {"anomalies": ["大额转账", "异地登录"]}                │
│  │                                                                  │
│  ├─ Chroma VectorStore.search — 0.3s                               │
│  │   Input: "信用风险 MEDIUM 案例"                                  │
│  │   Output: [Document1, Document2, Document3]                     │
│  │                                                                  │
│  └─ ChatOpenAI (gpt-4o) — 2.8s, 1200 tokens, $0.012              │
│      Input: "综合评分：680，异常：大额转账..."                      │
│      Output: "评估结论：中风险，建议人工复核..."                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

一眼看出：
- 哪个环节最慢？（analyze_transaction_pattern 2.1s）
- Token 消耗多少？（共 1650 tokens，$0.017）
- 哪个工具调用出错了？
- 重放这个请求只需要点击 "Re-run"
"""
```

#### 功能二：Datasets + Experiments — 评估对比

```python
# ========== 创建评估数据集 ==========
from langsmith import Client

client = Client()

# 方式1：从线上 Trace 中挑选 → 添加到 Dataset
# 在 LangSmith UI 中：点击某条 Trace → "Add to Dataset"

# 方式2：通过 SDK 批量创建
examples = [
    {
        "inputs": {"user_id": "UID-0001", "scenario": "正常客户"},
        "outputs": {"expected_risk": "LOW", "expected_score_range": [700, 850]}
    },
    {
        "inputs": {"user_id": "UID-0002", "scenario": "多头借贷"},
        "outputs": {"expected_risk": "HIGH", "expected_score_range": [300, 500]}
    },
    {
        "inputs": {"user_id": "UID-0003", "scenario": "边缘案例"},
        "outputs": {"expected_risk": "MEDIUM", "expected_score_range": [550, 650]}
    },
    # ... 200 条测试用例
]

dataset = client.create_dataset(
    dataset_name="credit_risk_test_cases_v1",
    description="信用风险评估测试集：覆盖 HIGH/MEDIUM/LOW 三种场景"
)

for example in examples:
    client.create_example(
        inputs=example["inputs"],
        outputs=example["outputs"],
        dataset_id=dataset.id
    )

# ========== 自定义评估函数 ==========
def evaluate_risk_accuracy(outputs: dict, reference_outputs: dict) -> dict:
    """评估风险判断的准确性"""
    predicted_risk = outputs.get("risk_level")
    expected_risk = reference_outputs.get("expected_risk")

    score = 1.0 if predicted_risk == expected_risk else 0.0

    return {
        "key": "risk_accuracy",
        "score": score,
        "comment": f"预测={predicted_risk}, 期望={expected_risk}"
    }

def evaluate_score_range(outputs: dict, reference_outputs: dict) -> dict:
    """评估信用分是否在合理范围"""
    predicted_score = outputs.get("score")
    expected_range = reference_outputs.get("expected_score_range")

    in_range = expected_range[0] <= predicted_score <= expected_range[1]
    score = 1.0 if in_range else 0.0

    return {
        "key": "score_in_range",
        "score": score,
        "comment": f"预测分={predicted_score}, 期望范围={expected_range}"
    }

# ========== 运行实验 ==========
from langsmith import run_on_dataset

# 实验1：GPT-4o + 完整 prompt
result_v1 = run_on_dataset(
    client=client,
    dataset_name="credit_risk_test_cases_v1",
    llm_or_chain_factory=lambda: build_chain(model="gpt-4o"),
    evaluation=[evaluate_risk_accuracy, evaluate_score_range],
    project_name="experiment-gpt4o-v1"
)

# 实验2：Claude Sonnet 5 + 优化后的 prompt
result_v2 = run_on_dataset(
    client=client,
    dataset_name="credit_risk_test_cases_v1",
    llm_or_chain_factory=lambda: build_chain(model="claude-sonnet-5"),
    evaluation=[evaluate_risk_accuracy, evaluate_score_range],
    project_name="experiment-claude-v2"
)

# ========== 在 LangSmith UI 中对比 ==========
"""
┌─────────────────────────────────────────────────────────────────┐
│  对比实验: credit_risk_test_cases_v1 (200 条)                    │
│                                                                  │
│  ┌──────────────────────┬───────────────┬──────────────────────┐│
│  │ 指标                  │ gpt4o-v1      │ claude-v2            ││
│  ├──────────────────────┼───────────────┼──────────────────────┤│
│  │ risk_accuracy        │ 0.87          │ 0.92 ↑              ││
│  │ score_in_range       │ 0.82          │ 0.89 ↑              ││
│  │ avg_latency          │ 3.2s          │ 2.1s                ││
│  │ avg_cost_per_call    │ $0.018        │ $0.009 ↓            ││
│  └──────────────────────┴───────────────┴──────────────────────┘│
│                                                                  │
│  ✅ Claude v2 在准确率、延迟、成本上全面优于 GPT-4o v1            │
└─────────────────────────────────────────────────────────────────┘
"""
```

#### 功能三：线上监控 + 自动评估

```python
# ========== 自定义线上评估器 ==========
from langsmith import evaluation

@evaluation.evaluator
def detect_pii_leak(run, example):
    """检测是否泄露了客户 PII 信息（如身份证号、手机号）"""
    output_text = run.outputs.get("content", "")

    import re
    patterns = {
        "phone": r"1[3-9]\d{9}",
        "id_card": r"\d{17}[\dXx]",
        "bank_card": r"\d{16,19}"
    }

    for pii_type, pattern in patterns.items():
        if re.search(pattern, output_text):
            return {
                "key": "pii_leak_check",
                "score": 0.0,
                "comment": f"⚠️ 泄露了 {pii_type} 信息！"
            }

    return {
        "key": "pii_leak_check",
        "score": 1.0,
        "comment": "✅ 无 PII 泄露"
    }

@evaluation.evaluator
def check_hallucination(run, example):
    """检测幻觉：判断 LLM 是否编造了不存在的规则"""
    output_text = run.outputs.get("content", "")

    # 用另一个 LLM 做事实核查
    fact_checker = ChatOpenAI(model="gpt-4o", temperature=0)
    check_prompt = f"""
    以下是一段风控评估结论。请检查其中是否有任何虚构的法规、规则编号或数据：

    结论：{output_text}

    只回答 YES（有虚构）或 NO（无虚构），然后列出虚构内容。
    """
    check_result = fact_checker.invoke(check_prompt)

    if "YES" in check_result.content.upper():
        return {"key": "hallucination_check", "score": 0.0, "comment": check_result.content}
    return {"key": "hallucination_check", "score": 1.0, "comment": "通过"}
```

---

## 项目实战：风控系统中的完整应用

### 场景：智能信用审批系统

```
业务流程：客户申请贷款 → AI 初筛 → 证据收集 → 综合评估 → (人工复核) → 放款/拒绝

技术栈：
  编排层: LangGraph (有状态多步骤 + 人机协同)
  组件层: LangChain (LLM调用 + Tool定义 + RAG检索)
  可观测: LangSmith (全链路追踪 + 线上评估)
```

```python
"""
=============================================================================
credit_risk_control_system/approval_agent.py
智能信用审批 Agent — LangGraph + LangChain + LangSmith 完整实现
=============================================================================
"""
import os
from typing import TypedDict, Annotated, Literal
from datetime import datetime

# ========== LangChain 组件 ==========
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_community.vectorstores import Chroma

# ========== LangGraph 组件 ==========
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# ========== LangSmith (自动注入，无需额外代码) ==========
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_xxx"
os.environ["LANGCHAIN_PROJECT"] = "credit-risk-approval-prod"


# ############################################################################
# 1. 定义 State
# ############################################################################
class ApprovalState(TypedDict):
    """审批流程的完整状态机"""
    # 基础信息
    user_id: str
    applicant_name: str
    loan_amount: float

    # AI 分析结果
    credit_score: int | None
    risk_level: str | None          # LOW / MEDIUM / HIGH
    anomaly_flags: list[str]        # 异常标记
    evidence_summary: str | None

    # RAG 知识库检索
    similar_cases: list[str]
    policy_references: list[str]

    # 流程控制
    current_stage: str              # screening → evidence → evaluation → manual → done
    need_manual_review: bool
    manual_result: str | None       # approved / rejected / need_more_info
    retry_count: int

    # 最终输出
    final_decision: str | None
    decision_reason: str | None
    risk_report_url: str | None

    # 消息历史
    messages: Annotated[list, "对话消息"]


# ############################################################################
# 2. 定义 Tools (LangChain)
# ############################################################################
@tool
def query_credit_score(user_id: str) -> dict:
    """查询用户在央行征信系统的信用分和信用报告摘要"""
    # 生产环境：调用实际的征信接口
    return {
        "score": 680,
        "report_summary": "无严重逾期，近6个月查询次数：3次",
        "total_loans": 2,
        "total_credit_limit": 500000
    }

@tool
def check_multi_platform_loans(user_id: str) -> dict:
    """查询用户是否在多个平台同时借款（多头借贷风险）"""
    return {
        "platform_count": 4,
        "platforms": ["借呗", "微粒贷", "京东金条", "美团借钱"],
        "total_debt": 180000,
        "risk_flag": True  # 超过3个平台，标记为风险
    }

@tool
def analyze_transaction_pattern(user_id: str, days: int = 90) -> dict:
    """分析用户近期交易模式，识别异常行为"""
    return {
        "total_transactions": 156,
        "anomalies": [
            "凌晨3点大额转账 50,000元",
            "频繁向新添加账户转账（7天内向5个新账户转账）",
            "月支出突然增加300%"
        ],
        "risk_score": 75  # 0-100，越高越异常
    }

@tool
def check_judicial_records(user_id: str) -> dict:
    """查询用户是否有司法被执行记录"""
    return {
        "has_record": False,
        "records": []
    }

tools = [
    query_credit_score,
    check_multi_platform_loans,
    analyze_transaction_pattern,
    check_judicial_records
]

# ############################################################################
# 3. 定义 Nodes (LangGraph)
# ############################################################################
llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def screening_node(state: ApprovalState) -> dict:
    """Node 1: AI 初筛"""
    system_prompt = """你是银行智能风控审批系统的初筛引擎。
    任务：
    1. 调用 query_credit_score 获取信用分
    2. 调用 check_multi_platform_loans 检查多头借贷
    3. 给出初步风险判断（LOW / MEDIUM / HIGH）
    """
    response = llm_with_tools.invoke([
        AIMessage(content=system_prompt),
        HumanMessage(content=f"请对用户 {state['user_id']} 进行初筛")
    ])
    return {
        "messages": [response],
        "current_stage": "evidence"
    }

def evidence_collection_node(state: ApprovalState) -> dict:
    """Node 2: 证据收集"""
    system_prompt = """你是证据收集引擎。
    任务：
    1. 调用 analyze_transaction_pattern 分析交易行为
    2. 调用 check_judicial_records 检查司法记录
    3. 汇总所有发现的异常标记
    """
    response = llm_with_tools.invoke([
        AIMessage(content=system_prompt),
        HumanMessage(content=f"用户 {state['user_id']}：深入收集风险证据")
    ])
    return {
        "messages": [response],
        "current_stage": "rag_retrieval"
    }

def rag_retrieval_node(state: ApprovalState) -> dict:
    """Node 3: RAG 知识库检索"""
    # 检索相似历史案例
    vector_store = Chroma(
        persist_directory="./credit_case_db",
        embedding_function=get_embedding_model()
    )

    query = f"信用分 {state.get('credit_score', 'N/A')} 风险等级评估案例"
    similar = vector_store.similarity_search(query, k=5)
    similar_cases = [doc.metadata["case_id"] for doc in similar]

    # 检索相关风控政策
    policy_docs = vector_store.similarity_search(
        "信用审批政策 风险评估标准", k=3
    )
    policy_refs = [doc.metadata["policy_id"] for doc in policy_docs]

    return {
        "similar_cases": similar_cases,
        "policy_references": policy_refs,
        "current_stage": "evaluation"
    }

def evaluation_node(state: ApprovalState) -> dict:
    """Node 4: 综合评估"""
    evaluation_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是风控总监。综合所有信息做出审批决策。

        审批规则：
        1. 信用分 < 550 或 多头借贷 > 3 或 交易异常分 > 80 → HIGH → 必须人工
        2. 信用分 550-650 或 2 个以上异常标记 → MEDIUM → 建议人工
        3. 信用分 > 650 且 无异常 → LOW → 可自动通过
        """),
        ("human", """
        用户: {user_id}
        贷款金额: {loan_amount}
        信用分: {credit_score}
        多头借贷平台数: {platform_count}
        交易异常: {anomalies}
        相似案例: {similar_cases}

        请给出审批决策和详细理由。
        """)
    ])

    chain = evaluation_prompt | llm
    result = chain.invoke({
        "user_id": state["user_id"],
        "loan_amount": state["loan_amount"],
        "credit_score": state.get("credit_score", "N/A"),
        "platform_count": state.get("platform_count", 0),
        "anomalies": state.get("anomaly_flags", []),
        "similar_cases": state.get("similar_cases", [])
    })

    # 解析风险等级
    content = result.content
    if "HIGH" in content.upper():
        risk_level = "HIGH"
        need_manual = True
    elif "MEDIUM" in content.upper():
        risk_level = "MEDIUM"
        need_manual = "建议人工" in content
    else:
        risk_level = "LOW"
        need_manual = False

    return {
        "messages": [result],
        "risk_level": risk_level,
        "need_manual_review": need_manual,
        "current_stage": "evaluation"
    }

def manual_review_node(state: ApprovalState) -> dict:
    """Node 5: 人工审核（阻断等待）"""
    # 构造给审核员的信息
    review_summary = f"""
    ⚠️ 需要人工审核
    用户: {state['user_id']}
    贷款金额: {state['loan_amount']} 元
    信用分: {state.get('credit_score')}
    风险等级: {state.get('risk_level')}
    异常标记: {state.get('anomaly_flags', [])}

    请选择: approved / rejected / need_more_info
    """
    return {
        "current_stage": "manual_review",
        "messages": [AIMessage(content=review_summary)]
    }

def final_decision_node(state: ApprovalState) -> dict:
    """Node 6: 最终决策"""
    if state.get("manual_result") == "approved" or state["risk_level"] == "LOW":
        decision = "APPROVED"
        reason = f"风险评估等级:{state['risk_level']}，人工审核:通过"
    else:
        decision = "REJECTED"
        reason = f"风险评估等级:{state['risk_level']}，人工审核:不通过"

    return {
        "final_decision": decision,
        "decision_reason": reason,
        "current_stage": "done"
    }


# ############################################################################
# 4. 定义路由逻辑
# ############################################################################
def route_after_evaluation(state: ApprovalState) -> Literal["manual_review", "final_decision"]:
    """条件路由：需要人工审核吗？"""
    if state["need_manual_review"]:
        print(f"🔴 需要人工审核 - 风险等级: {state['risk_level']}")
        return "manual_review"
    print(f"🟢 自动通过 - 风险等级: {state['risk_level']}")
    return "final_decision"

def route_after_manual(state: ApprovalState) -> Literal["final_decision", "evidence_collection"]:
    """人工审核后的路由"""
    if state.get("manual_result") == "need_more_info":
        print("🔄 审核员要求补充材料，重新收集证据")
        return "evidence_collection"  # 回环！
    return "final_decision"


# ############################################################################
# 5. 构建 Graph
# ############################################################################
def build_approval_graph() -> StateGraph:
    """构建完整的审批流程图"""
    workflow = StateGraph(ApprovalState)

    # 添加所有节点
    workflow.add_node("screening", screening_node)
    workflow.add_node("evidence_collection", evidence_collection_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("evaluation", evaluation_node)
    workflow.add_node("manual_review", manual_review_node)
    workflow.add_node("final_decision", final_decision_node)

    # 入口
    workflow.set_entry_point("screening")

    # 线性边
    workflow.add_edge("screening", "evidence_collection")
    workflow.add_edge("evidence_collection", "rag_retrieval")
    workflow.add_edge("rag_retrieval", "evaluation")

    # 条件边（分流）
    workflow.add_conditional_edges(
        "evaluation",
        route_after_evaluation,
        {
            "manual_review": "manual_review",
            "final_decision": "final_decision"
        }
    )

    # 人工审核后的条件跳转（可能有回环）
    workflow.add_conditional_edges(
        "manual_review",
        route_after_manual,
        {
            "final_decision": "final_decision",
            "evidence_collection": "evidence_collection"  # ⚡ 回环路径
        }
    )

    workflow.add_edge("final_decision", END)

    return workflow


# ############################################################################
# 6. 编译并运行
# ############################################################################
checkpointer = SqliteSaver.from_conn_string("approval_checkpoints.db")

app = build_approval_graph().compile(
    checkpointer=checkpointer,
    interrupt_before=["manual_review"]  # 人工审核前自动暂停
)

# ========== 使用示例 ==========
async def main():
    # 启动审批流程
    config = {"configurable": {"thread_id": "approval-20260707-001"}}

    initial_state = {
        "user_id": "UID-12345",
        "applicant_name": "张三",
        "loan_amount": 300000,
        "current_stage": "screening",
        "anomaly_flags": [],
        "similar_cases": [],
        "policy_references": [],
        "retry_count": 0,
        "need_manual_review": False,
        "messages": []
    }

    # 运行审批（会在 manual_review 节点暂停）
    result = app.invoke(initial_state, config)

    if result["current_stage"] == "manual_review":
        print(f"⏸️ 暂停于人工审核节点，等待审核员输入...")
        print(f"当前状态: {result['current_stage']}")
        print(f"风险等级: {result['risk_level']}")

        # ========== 人工审核员在 UI 上操作 ==========
        # 模拟审核员点击 "批准"
        app.update_state(config, {"manual_result": "approved"})

        # 恢复执行
        final_result = app.invoke(None, config)
        print(f"✅ 审批完成: {final_result['final_decision']}")
        print(f"原因: {final_result['decision_reason']}")

    # ========== 流式执行（实时看到每步进展）==========
    for event in app.stream(initial_state, config):
        node_name = list(event.keys())[0]
        print(f"▸ 执行节点: {node_name}")
        # LangSmith 会记录每一步的详细信息

# 运行
import asyncio
asyncio.run(main())
```

### 项目目录结构

```
credit_risk_control_system/
├── approval_agent.py          # 主审批 Agent（上面那个文件）
├── tools/
│   ├── credit_score.py        # 信用分查询 Tool
│   ├── transaction_analysis.py # 交易分析 Tool
│   └── judicial_check.py      # 司法查询 Tool
│
├── graphs/
│   ├── approval_graph.py      # 审批流程 StateGraph
│   ├── appeal_graph.py        # 申诉流程 StateGraph（子图复用）
│   └── monitoring_graph.py    # 贷后监控 StateGraph
│
├── chains/
│   ├── rag_risk_chain.py      # RAG 风险评估链
│   ├── report_chain.py        # 报告生成链
│   └── classification_chain.py # 文本分类链
│
├── prompts/
│   ├── screening.yaml         # 初筛提示词模板
│   ├── evaluation.yaml        # 评估提示词模板
│   └── report.yaml            # 报告提示词模板
│
├── evaluators/
│   ├── accuracy.py            # 准确率评估器
│   ├── pii_check.py           # PII 泄露检测
│   └── hallucination_check.py # 幻觉检测
│
├── langsmith_config.py        # LangSmith 配置
├── test_datasets/
│   └── approval_cases.json    # 评估测试集
│
└── checkpoints/
    └── approval_checkpoints.db # State 持久化
```

---

## 面试高频考点 & 深度回答

### Q1: LangChain 的核心设计思想是什么？

**回答框架**：

> LangChain 的核心是把 LLM 应用开发中的常见模式抽象为可组合的组件。核心思想有三层：
>
> **第一层：标准化抽象。** 把 LLM、Prompt、Tool、Retriever 等都定义成统一接口（都是 Runnable），解决了"每个模型 API 不一样"的问题。你换了模型，只需要改一行 `ChatOpenAI` → `ChatAnthropic`。
>
> **第二层：LCEL 管道式组合。** 用 `|` 操作符把组件串起来，像 Unix 管道。这样数据流向清晰、容易调试、支持流式输出。
>
> **第三层：Runtime 绑定。** 同一套链可以在不同配置下运行（不同的 model、tags、metadata），做到了"定义时"和"运行时"的分离。

**加分点**：能说出 LCEL 的底层原理 → 每个 `|` 实际上是调用了 `Runnable.__or__`，返回一个新的 `RunnableSequence`，最终形成一棵 Runnable 树。invoke 时从叶子节点向上执行（或者根节点向下，取决于实现）。

---

### Q2: LangChain 的 Chain 和 Agent 有什么区别？

| 维度    | Chain                | Agent                   |
|--------|-----------------------|-------------------------|
| 执行路径  | **固定的**：A→B→C，编译时确定  | **动态的**：LLM 在运行时决定下一步   |
| 决策权   | 开发者预定义               | LLM 自主判断                |
| 工具调用  | 手动绑定+路由              | 自动选择工具和参数               |
| 适用场景  | 确定性的管道（RAG，翻译，分类）    | 不确定的开放任务（客服，搜索，审批）      |
| 可控性   | 高（每步可预期）             | 低（LLM 可能绕弯路）            |
| 成本    | 低（固定 Token 消耗）       | 高（可能多轮调用）               |

**面试官追问**："什么场景用 Chain，什么场景用 Agent？"

> 回答：能确定步骤的用 Chain（比如 RAG：检索→注入→问答），步骤不确定或需要 LLM 自行判断的用 Agent（比如"帮我查这个客户的风险，搜集各种信息，综合判断"）。生产环境更倾向于 Chain + 有限 Agent 混合，纯 Agent 的成本和不确定性太高。

---

### Q3: LangGraph 和 LangChain 的关系？为什么不直接在 Chain 里做循环？

**回答框架**：

> 1. **LangChain 的 LCEL 只支持 DAG（有向无环图）。** 它的设计哲学是数据从一个组件流向另一个组件，不能形成环。
>
> 2. **真实业务场景需要循环和状态。** 比如风控审批中"证据不足→重新收集→再评估→还是不足→再收集"这种循环，LCEL 根本表达不出来。
>
> 3. **LangGraph 本质是一个状态机框架。** 它引入 State、Node、Edge、Checkpointer，可以表达任意复杂的图结构（包括循环、条件跳转、并行分支）。
>
> 4. **两者的关系是叠加，不是替代。** LangGraph 的每个 Node 里面可以是一个 LangChain Chain。你可以想象：LangGraph 是高速公路的路网（图结构），每段路上跑的车是 LangChain（具体的 LLM 调用逻辑）。
>
> **核心区别**：LCEL 是函数式编程（数据流入流出），LangGraph 是状态机编程（根据 State 做决策和跳转）。

---

### Q4: LangGraph 的 Checkpointer 是什么？为什么重要？

**回答框架**：

> Checkpointer 是 LangGraph 的持久化层，它在每执行一个 Node 之后，自动把当前的 State 快照保存到数据库中。
>
> **三个关键价值**：
>
> 1. **中断恢复。** 如果服务崩溃或人工审核暂停了，恢复时可以从中断点继续，不会丢失中间状态。
>
> 2. **时间旅行调试。** 可以回溯到任何一个历史 State，看当时的数据是什么，然后从那个点重新执行（LangSmith UI 中点击某个节点即可重放）。
>
> 3. **多轮对话记忆。** Checkpointer 按 thread_id 组织，天然支持多用户、多会话的长期记忆。
>
> **存储后端**：支持 MemorySaver（开发用，重启丢失）、SqliteSaver（本地持久化）、PostgresSaver（生产用）。
>
> **追问**："Checkpointer 和普通的 Redis 缓存有什么区别？"
>
> > Checkpointer 不是为了缓存，是为了**状态机的持久化**。Redis 存的是最终数据，Checkpointer 存的是**每一步的快照+图的执行位置**。比如你在第 3 个节点暂停了，恢复时不是从第一个重跑，而是直接从第 3 个继续。这需要记录"当前在执行图的哪个位置"，Redis 做不到这一点。

---

### Q5: 如何用 LangSmith 做 LLM 应用的 A/B 测试？

**回答框架**：

> 标准流程：
>
> 1. **创建 Dataset**：从线上 Trace 中挑选 200 条代表性请求，手动标注期望输出。
>
> 2. **定义 Evaluator**：写自定义打分函数（准确率、延迟、成本、安全性等）。
>
> 3. **运行 Experiment**：用 `run_on_dataset` 在同一个 Dataset 上分别跑 Prompt v1 和 v2。
>
> 4. **对比分析**：在 LangSmith UI 中查看 side-by-side 对比结果，包括各项指标、胜率、每条 case 的差异。
>
> 5. **决策上线**：根据实验数据决定是否上线新版本。
>
> **关键认知**：这不是传统的 A/B 测试（流量分割），而是**离线评估（Offline Evaluation）**。比在线 A/B 更快、更便宜、更安全，不会影响线上用户。线上流量 A/B 应该放在离线评估通过之后。

---

### Q6: 你在项目中如何防止 LLM 幻觉？

**回答框架**（结合实际项目）：

> 我们从四个层面防止幻觉：
>
> 1. **知识锚定（RAG）**：所有评估结论必须有检索到的文档支撑，Prompt 中明确要求"请引用参考文档编号"。
>
> 2. **结构化输出**：使用 PydanticOutputParser 强制 LLM 输出结构化 JSON，而不是自由文本。`RiskReport(risk_level, score, reasons)` 这种格式很难编造。
>
> 3. **工具校验**：关键数据（信用分、交易记录）不靠 LLM "记住"，而是通过 Tool 实时查询。LLM 只做推理，不做数据存储。
>
> 4. **线上自动评估（LangSmith）**：部署了 hallucination detector，用另一个 LLM 事后检查输出中是否有虚构的法规编号、不存在的案例 ID。

---

### Q7: LangGraph 如何实现人机协同（Human-in-the-Loop）？

**回答框架**：

> LangGraph 提供了两种机制：
>
> **方式1：interrupt_before。** 编译时指定 `interrupt_before=["manual_review"]`，执行到该节点前自动暂停，直到调用 `app.update_state()` 恢复。
>
> **方式2：Node 内部中断。** 在 Node 函数中使用 `interrupt()` 或在 State 中设置暂停标记。
>
> **恢复机制**：
> ```python
> # Step 1: 初始调用，暂停在 manual_review 前
> result = app.invoke(initial_state, config)
> # result["current_stage"] == "manual_review"  ← 已暂停
>
> # Step 2: 外部系统（审核员操作后）更新 State
> app.update_state(config, {"manual_result": "approved"})
>
> # Step 3: 从中断点恢复执行
> final = app.invoke(None, config)
> ```
>
> **工程细节**：线程通过 `thread_id` 标识，多个并发审核互不干扰。Checkpointer 保证了即使服务重启，中断状态也不丢失。

---

### Q8: 解释一下 LangGraph 的 Send API（并行执行）？

**回答框架**：

> Send API 允许一个节点向多个下游节点**并行**发送执行任务，每个任务可以有不同的 State 更新。
>
> ```python
> from langgraph.types import Send
>
> def fan_out_to_analysts(state):
>     """一个请求分发给多个分析专家并行处理"""
>     return [
>         Send("credit_analyst", {"focus": "信用记录"}),
>         Send("transaction_analyst", {"focus": "交易行为"}),
>         Send("fraud_analyst", {"focus": "欺诈检测"}),
>     ]
>
> # 三个分析师节点会并行执行
> # 都完成后，自动合并结果到下一个节点
> ```
>
> 这在风控中非常实用：一次审批请求，同时分析信用、交易、欺诈三个维度，并行执行后再汇总，大大缩短审核时间。

---

## 速记卡片

```
┌─────────────────────────────────────────────────────────────┐
│                   三件套速记                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LangChain    乐高积木       提供 LLM 开发的基础组件          │
│  (组件)       搭什么都可以    Model/Prompt/Tool/Chain/Agent   │
│                                                              │
│  LangGraph    电路图         编排复杂的有状态工作流            │
│  (编排)       电流怎么走      State/Node/Edge/Checkpointer    │
│                                                              │
│  LangSmith    监控摄像头     追踪、调试、评估 LLM 应用         │
│  (可观测)     全程录像        Traces/Datasets/Experiments     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  一句话关系：                                                │
│  LangChain 是工具箱 → LangGraph 是流水线 → LangSmith 是质检站 │
│                                                              │
│  技术栈分层：                                                │
│    LangSmith  (最上层 — 所有调用自动上报)                     │
│    LangGraph  (中间层 — 编排多步流程，调用 LangChain 组件)    │
│    LangChain  (基础层 — LLM 调用、工具定义、RAG 检索)         │
│                                                              │
│  选择指南：                                                  │
│    简单问答       → LCEL Chain 就够了                         │
│    多步推理       → LangGraph Agent                          │
│    人机协同       → LangGraph + interrupt                    │
│    复杂审批流     → LangGraph StateGraph + Checkpointer       │
│    线上监控       → LangSmith Traces + Evaluators             │
│    A/B 对比       → LangSmith Datasets + Experiments          │
└─────────────────────────────────────────────────────────────┘
```

---

> **学习路径建议**：
> 1. 先用 LangChain 的 LCEL 写一个 RAG 问答（1-2天）
> 2. 接入 LangSmith，观察 Trace 和评估结果（半天）
> 3. 把 RAG 拆成多个 Node，用 LangGraph StateGraph 编排（1-2天）
> 4. 加入条件路由、循环、human-in-the-loop（2-3天）
> 5. 最终构建完整的 Agent 系统，加入线上评估（1周）
