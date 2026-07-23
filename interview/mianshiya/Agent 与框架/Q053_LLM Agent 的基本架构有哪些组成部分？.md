---
id: Q053
source: mianshiya
category: Agent 与框架
title: LLM Agent 的基本架构有哪些组成部分？
generated: 2026-07-23T15:41:19.802691
---

# LLM Agent 的基本架构有哪些组成部分？

> 来源: 面试鸭题库 | 分类: Agent 与框架

LLM Agent 不是简单地调⽤⼤模型，⽽是⼀个能感知环境、做出决策并执⾏动作的智能体。它的结构更像是⼀个闭环
控制系统。
1）感知模块（Perception）
负责接收外部输⼊，⽐如⽤户指令、环境状态或历史交互记录。这部分会把原始信息转换成模型可理解的格式，通常
就是拼接到 prompt ⾥。
2）规划模块（Planning）
这是 Agent 的“⼤脑”，⼜可以拆成两块：
推理（Reasoning）：让模型对当前问题进⾏多步思考，⽐如使⽤思维链（Chain-of-Thought），先想“我该
怎么做”，再决定下⼀步。
任务分解（Task Decomposition）：复杂任务会被拆成多个⼦任务，按序或并⾏处理，像 LangChain 中的
Plan-and-Execute 就是典型实现。
3）记忆模块（Memory）
维持短期和⻓期上下⽂。短期记忆⼀般是当前对话的 token 上下⽂窗⼝，受限于模型⻓度；⻓期记忆则依赖向量数据
库，⽐如⽤ Milvus 或 Chroma 存储历史经验，需要时检索召回。
4）⼯具调⽤与执⾏（Tool Use & Action）
Agent 能主动调⽤外部⼯具，⽐如查天⽓、执⾏代码、操作数据库。主流做法是通过函数调⽤（Function Calling）机
制，让模型输出结构化 JSON 去触发 API，例如在 OpenAI 的接⼝中定义 tools 列表。
整个流程⾛下来，其实就是⼀个“观察 → 思考 → 决策 → ⾏动 → 观察”的循环。