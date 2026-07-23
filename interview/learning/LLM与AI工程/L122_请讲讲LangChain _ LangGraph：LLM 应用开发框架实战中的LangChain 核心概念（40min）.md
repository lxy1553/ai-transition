---
id: L122
source: learning
category: LLM与AI工程
title: 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangChain 核心概念（40min）
generated: 2026-07-23T15:41:19.875718
---

# 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangChain 核心概念（40min）

> 来源: 学习复习计划 | 分类: LLM与AI工程

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