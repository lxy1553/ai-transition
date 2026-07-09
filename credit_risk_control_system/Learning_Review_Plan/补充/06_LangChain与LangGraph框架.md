# LangChain / LangGraph：LLM 应用开发框架实战

> 目标：掌握 LangChain 的链式调用和 LangGraph 的状态机编排，能用这两个框架构建 AI 应用。

---

## 一、为什么需要 LangChain（20min）

### 1.1 没有框架时的问题

```python
# 手写代码调 LLM — 看起来很简单，直到你需要:
# 1. 多轮对话维护上下文
# 2. 调用多个函数
# 3. 错误重试
# 4. 异步调用
# 5. 日志追踪

# 手写代码开始变得混乱...
def my_agent(query):
    response = llm(query)
    if has_tool_call(response):
        result = tool(response)
        response = llm(query + result)
    # 每次都重复这个模式
    # 没有标准的结构
```

### 1.2 LangChain 解决了什么

```
LangChain 提供:
1. 标准化接口 — 所有 LLM（OpenAI/DeepSeek/Claude）用同一套 API
2. 链式编程 — 像搭积木一样组合功能
3. 内置工具 — 向量检索、SQL查询、网页搜索等
4. 可观测性 — LangSmith 追踪执行路径

LangChain 不是必须的，但它是目前最主流的 LLM 应用框架（JD 出现率 71%）
```

---

## 二、LangChain 核心概念（40min）

### 2.1 Chat Models

```python
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatDeepSeek

# 统一接口: 不管用哪个 LLM，代码结构完全一样
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key="sk-xxx",
)

# 改成 DeepSeek: 只换类名和 base_url
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.0,
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
)

# 调用
response = llm.invoke("什么是 night_ops_ratio_30d？")
print(response.content)
```

### 2.2 Prompt Templates

```python
from langchain.prompts import ChatPromptTemplate

# 比普通字符串拼接好的地方:
# 1. 自动变量注入
# 2. 支持 System/User/Assistant 多角色
# 3. 可以串联

# 基础模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。根据以下表结构生成 SQL: {schema}"),
    ("human", "{question}"),
])

# 使用: 自动填充变量
messages = prompt.invoke({
    "schema": "表 ads_model_monitor_daily: channel STRING, approval_rate DOUBLE",
    "question": "上周通过率最高的渠道是什么？",
})
```

### 2.3 Chains（链）

```python
from langchain.chains import LLMChain

# Chain = Prompt + LLM 的组合
# 这是 LangChain 最基础的原子单位

llm = ChatDeepSeek(model="deepseek-chat", temperature=0.0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。表结构: {schema}"),
    ("human", "问题: {question}\n生成 SQL:"),
])

sql_chain = LLMChain(
    llm=llm,
    prompt=prompt,
)

# 调用 chain
result = sql_chain.invoke({
    "schema": "ads_model_monitor_daily(channel, approval_rate, dt)",
    "question": "上周哪个渠道通过率最高？",
})
print(result["text"])  # 输出: SELECT channel, AVG(approval_rate) ...


# Sequential Chain（串行链）— 一个链的输出是下一个链的输入
from langchain.chains import SequentialChain

# Chain 1: 生成 SQL
sql_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。"),
    ("human", "问题: {question}\n生成 SQL:"),
])
chain_sql = LLMChain(llm=llm, prompt=sql_prompt, output_key="sql")

# Chain 2: 解释 SQL
explain_prompt = ChatPromptTemplate.from_messages([
    ("human", "用中文解释这段 SQL 做了什么:\n{sql}"),
])
chain_explain = LLMChain(llm=llm, prompt=explain_prompt, output_key="explanation")

# 串起来: 用户问问题 → 生成 SQL → 解释 SQL
full_chain = SequentialChain(
    chains=[chain_sql, chain_explain],
    input_variables=["question"],
    output_variables=["sql", "explanation"],
)

result = full_chain.invoke({"question": "上周通过率最高渠道？"})
print(f"SQL: {result['sql']}")
print(f"解释: {result['explanation']}")
```

### 2.4 Tools（工具调用）

```python
from langchain.tools import tool

# @tool 装饰器: 把 Python 函数变成 LLM 可调用的工具
@tool
def query_warehouse(sql: str) -> str:
    """
    执行 SQL 查询数据仓库。参数: sql — SQL 查询语句
    """
    # 这里是简化实现
    return f"已执行: {sql}"

# 多种内置工具
from langchain_community.tools import DuckDuckGoSearchRun

# 把工具绑定到 LLM
llm_with_tools = llm.bind_tools([query_warehouse, DuckDuckGoSearchRun()])
```

### 2.5 Agents（智能体）

```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

# Agent = LLM + Tools + 循环决策
# 1. LLM 决定是否调用工具
# 2. 如果调用，执行工具，结果返回给 LLM
# 3. LLM 根据结果决定下一步（继续调用还是直接回答）

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是风控数据仓库的 AI 助手。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # ← 中间步骤
])

agent = create_tool_calling_agent(
    llm=llm_with_tools,
    tools=[query_warehouse],
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[query_warehouse],
    verbose=True,  # ← 打印每一步
)

# 执行
agent_executor.invoke({
    "input": "查一下 2026-07-01 各渠道通过率"
})
# 输出:
# > 调用 query_warehouse(sql="SELECT channel, approval_rate ...")
# > 结果: [('APP_IOS', 0.723), ('APP_ANDROID', 0.651)]
# > 回答: APP_IOS 渠道通过率最高，为 72.3%...
```

---

## 三、LangGraph：状态机工作流（1h）

### 3.1 Chain vs Graph 的区别

```
Chain (串行): A → B → C → D
  固定的、线性的执行路径
  不能分支、不能循环、不能等待

Graph (有向图):
  A → [条件] → [B → C → D]
            → [E → F] → G → ...
  可以分支（条件路由）
  可以循环（状态机）
  可以等待人工输入（异步）
```

**LangGraph 用 StateGraph 来定义有状态的工作流。**

### 3.2 核心概念

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

# ═══════════════════════════════════════════
# 概念 1: State（状态）
#   TypedDict — 定义工作流中传递的数据结构
# ═══════════════════════════════════════════

class ApprovalState(TypedDict):
    """信贷审批工作流的状态 — 在各个节点之间传递"""
    user_id: str
    score: int
    decision: str      # APPROVE / REJECT / MANUAL_REVIEW
    reason: str
    rejected: bool


# ═══════════════════════════════════════════
# 概念 2: Nodes（节点）
#   每个节点是一个函数: 输入 State → 修改 State → 输出
# ═══════════════════════════════════════════

def rule_check(state: ApprovalState) -> ApprovalState:
    """节点1: 规则引擎检查"""
    print(f"[规则引擎] 检查 {state['user_id']}")
    state["rejected"] = False
    return state

def model_score(state: ApprovalState) -> ApprovalState:
    """节点2: 模型评分"""
    state["score"] = 672
    return state


# ═══════════════════════════════════════════
# 概念 3: Edges（边）
#   条件边: 根据 State 决定下一步
#   普通边: 固定走到下一个节点
# ═══════════════════════════════════════════

def route_after_rules(state: ApprovalState) -> Literal["rejected", "scoring"]:
    """
    条件边: 规则检查后决定去哪
    - 如果命中硬拒绝 → 去 rejection 节点
    - 否则 → 去模型评分节点
    """
    if state.get("rejected"):
        return "rejected"
    return "scoring"


# ═══════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════

workflow = StateGraph(ApprovalState)

# 注册节点
workflow.add_node("check", rule_check)
workflow.add_node("scoring", model_score)
workflow.add_node("rejection", lambda s: s)

# 设置入口
workflow.set_entry_point("check")

# 设置边
workflow.add_conditional_edges(
    "check",
    route_after_rules,
    {"rejected": "rejection", "scoring": "scoring"}
)
workflow.add_edge("scoring", END)
workflow.add_edge("rejection", END)

# 编译
app = workflow.compile()
```

### 3.3 实战：信贷审批完整工作流

```python
"""
本例实现信贷审批的完整状态机:

rule_check ──REJECT──→ rejection_letter → END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse → END
                    │
                    ├──MANUAL_REVIEW──→ request_docs → 【等待用户上传】→ model_score
                    └──REJECT──→ rejection_letter → END
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
import json


# ── 状态定义 ──
class CreditState(TypedDict):
    user_id: str
    features: dict
    rule_hits: list[str]
    score: int
    decision: str
    reason: str
    required_docs: list[str]


# ── 节点函数 ──

def rule_check(state: CreditState) -> CreditState:
    """节点1: 规则引擎检查 — 需要实现短路逻辑"""
    hits = []
    if state["features"].get("in_blacklist"):
        hits.append("BLACKLIST_HIT")
        state["decision"] = "REJECT"
        state["reason"] = "命中黑名单"
    state["rule_hits"] = hits
    print(f"  [规则] 命中: {hits}")
    return state


def model_scoring(state: CreditState) -> CreditState:
    """节点2: 模型评分"""
    # 模拟 XGBoost 推理
    prob = 0.3  # 违约概率
    score = int(600 + 50 / 0.693 * (1 - prob) / prob)  # 简化评分公式
    state["score"] = score
    print(f"  [模型] 评分: {score}")
    return state


def request_docs(state: CreditState) -> CreditState:
    """节点3 (LLM): 生成需要补充的材料清单"""
    docs = {
        "收入不稳定": "收入证明、银行流水",
        "多头借贷": "现有贷款合同明细",
        "设备异常": "人脸识别视频验证",
    }
    # 根据规则命中情况生成
    state["required_docs"] = [docs.get(state["reason"], "身份证明")]
    print(f"  [LLM] 请补充材料: {state['required_docs']}")
    return state


def rejection_letter(state: CreditState) -> CreditState:
    """节点4 (LLM): 生成拒绝通知"""
    letter = f"""尊敬的{state['user_id']}:
    很抱歉，您的贷款申请未通过。
    原因: {state['reason']}
    您有权在 15 个工作日内申请人工复核。"""
    state["reason"] = letter
    print(f"  [LLM] 已生成拒绝函")
    return state


def disburse(state: CreditState) -> CreditState:
    """节点5: 放款"""
    print(f"  [放款] 已向 {state['user_id']} 放款 ¥5,000")
    return state


# ── 路由函数 ──

def route_after_rules(state) -> Literal["REJECT", "PROCEED"]:
    if state["decision"] == "REJECT":
        return "REJECT"
    return "PROCEED"


def route_after_scoring(state) -> Literal["APPROVE", "MANUAL_REVIEW", "REJECT"]:
    score = state["score"]
    if score >= 600:
        return "APPROVE"
    elif score >= 500:
        return "MANUAL_REVIEW"
    else:
        return "REJECT"


# ── 构建图 ──

def build_credit_workflow():
    graph = StateGraph(CreditState)

    graph.add_node("rule_check", rule_check)
    graph.add_node("model_scoring", model_scoring)
    graph.add_node("request_docs", request_docs)
    graph.add_node("rejection_letter", rejection_letter)
    graph.add_node("disburse", disburse)

    # 条件边: 规则引擎 → 拒绝/继续
    graph.add_conditional_edges(
        "rule_check",
        route_after_rules,
        {
            "REJECT": "rejection_letter",
            "PROCEED": "model_scoring"
        }
    )

    # 条件边: 模型评分 → 通过/人工/拒绝
    graph.add_conditional_edges(
        "model_scoring",
        route_after_scoring,
        {
            "APPROVE": "disburse",
            "MANUAL_REVIEW": "request_docs",
            "REJECT": "rejection_letter"
        }
    )

    graph.add_edge("disburse", END)
    graph.add_edge("rejection_letter", END)
    graph.add_edge("request_docs", END)  # 等待用户上传 — 异步恢复

    graph.set_entry_point("rule_check")
    return graph.compile()


# ── 执行 ──
workflow = build_credit_workflow()

# 场景 1: 正常用户
result = workflow.invoke({
    "user_id": "user_000042",
    "features": {"in_blacklist": False, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']}")

# 场景 2: 黑名单用户
result = workflow.invoke({
    "user_id": "user_000999",
    "features": {"in_blacklist": True, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']} — 原因: {result['reason'][:30]}...")
```

---

## 四、LangGraph 的进阶功能

### 4.1 条件循环（human-in-the-loop）

```python
# 当用户补充材料时，工作流需要恢复
# LangGraph 的 checkpointer 可以自动保存状态

from langgraph.checkpoint.memory import MemorySaver

# 使用持久化存储
checkpointer = MemorySaver()

workflow = build_credit_workflow()
app = workflow.compile(checkpointer=checkpointer)

# 第一次执行: 暂停在 request_docs 等待用户上传
config = {"configurable": {"thread_id": "user_000042_session"}}
result = app.invoke(input_data, config=config)

# 用户上传材料后: 恢复执行
# update_state 从上次暂停处继续
app.update_state(config, {"required_docs": []})
result = app.invoke(None, config=config)
```

### 4.2 可视化

```python
# 生成工作流图
from IPython.display import Image, display

display(Image(workflow.get_graph().draw_mermaid_png()))
# → 直接看到审批流程图
```

---

## 五、LangChain vs LangGraph 选择指南

| 场景 | 用 LangChain | 用 LangGraph |
|------|:----------:|:----------:|
| 简单的 Prompt → LLM → 输出 | ✅ | ❌ 杀鸡用牛刀 |
| 多步链式调用（A→B→C） | ✅ | 也✅ |
| 有分支的路由（if-else 决策） | ❌ | ✅ |
| 循环直到条件满足 | ❌ | ✅ |
| 等待人工输入 | ❌ | ✅ |
| 复杂状态机 | ❌ | ✅ |

```
一句话: 顺序执行用 Chain，条件分支用 Graph，人工干预用 Graph + Checkpointer。
```

---

## 六、动手练习（1h）

```python
"""
练习 1: 用 LangChain 实现 NL2SQL Agent

要求:
1. 定义两个工具: query_warehouse(sql), get_schema(table_name)
2. Agent 先获取 Schema → 再生成 SQL → 执行 SQL → 返回结果
3. 支持"查一下 2026-07-01 各渠道通过率"这类问题

练习 2: 用 LangGraph 实现客服质检工作流

状态:
  Text → Classify → [投诉] → RouteToAgent → LLM生成摘要 → END
                    [简单问题] → AutoReply → END
                    [复杂问题] → Escalate → END
"""
```

---

## 七、常见问题

### Q1: LangChain 值得学吗？还是直接用 Python 调 API 更好？

```
如果只是调 LLM API（NL2SQL、聊天）→ 直接调 API 更简单，不需要 LangChain
如果需要工具调用（Agent）→ LangChain 让代码结构更清晰
如果面试要求（JD 出现率 71%）→ 值得学

最佳实践: 学会 LanfgChain 的概念，小项目手写，大项目用框架。
```

### Q2: LangGraph 和 FastAPI 的异步兼容吗？

```python
# LangGraph 原生支持 async
result = await app.ainvoke(input_data)

# 可以集成到 FastAPI
from fastapi import FastAPI

fastapi_app = FastAPI()
workflow = build_credit_workflow()

@fastapi_app.post("/credit/apply")
async def credit_apply(user_id: str):
    result = await workflow.ainvoke({
        "user_id": user_id,
        "features": {"in_blacklist": False},
    })
    return {"decision": result["decision"]}
```
