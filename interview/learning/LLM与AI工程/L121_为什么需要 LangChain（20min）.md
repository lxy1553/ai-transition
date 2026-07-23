---
id: L121
source: learning
category: LLM与AI工程
title: 为什么需要 LangChain（20min）
generated: 2026-07-23T15:41:19.875607
---

# 为什么需要 LangChain（20min）

> 来源: 学习复习计划 | 分类: LLM与AI工程

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