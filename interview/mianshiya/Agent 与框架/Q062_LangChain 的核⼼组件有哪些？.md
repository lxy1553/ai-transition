---
id: Q062
source: mianshiya
category: Agent 与框架
title: LangChain 的核⼼组件有哪些？
generated: 2026-07-23T15:41:19.803887
---

# LangChain 的核⼼组件有哪些？

> 来源: 面试鸭题库 | 分类: Agent 与框架

LangChain 的设计是为了解耦⼤模型应⽤的各个关键环节，让开发者能灵活组装。它不是单⼀⼯具，⽽是⼀套拼图。
1）Model I/O
负责与⼤模型交互，封装了输⼊输出逻辑。⽀持多种模型类型，⽐如 OpenAI、Anthropic、Hugging Face 等。你不⽤
⾃⼰写 HTTP 请求，它帮你统⼀调⽤⽅式。
2）Prompts
提⽰词管理模块，包括提⽰词模板（PromptTemplate）和⽰例选择器（ExampleSelector）。你可以定义变量化的
prompt，⽐如把⽤户问题动态填⼊模板，还能做 few-shot ⽰例注⼊。
3）Chains
把多个步骤串起来执⾏。⽐如先调⽤模型⽣成摘要，再⽤另⼀个 prompt 做情感分析，整个流程封装成⼀个 chain。最
常⽤的是 LLMChain ，也可以⾃定义复杂链式逻辑。
4）Agents
允许模型“决策”下⼀步动作。⽐如模型判断当前需要查天⽓，就会调⽤指定⼯具（Tool），执⾏完再继续推理。背后
依赖 Tools 和 AgentExecutor，典型场景像 LangChain 结合 SerpAPI 做搜索代理。
5）Memory
维持对话状态，常⻅有 ConversationBufferMemory （保存全部历史）和 ConversationSummaryMemory
（只存摘要）。适合聊天机器⼈这类需要上下⽂记忆的应⽤。
6）Retrieval
结合向量数据库做检索增强。⽐如⽤ FAISS 或 Chroma 存⽂档嵌⼊，查询时先检索相关⽚段，再喂给模型⽣成答案，
有效缓解幻觉。
这些组件可以单独使⽤，也能组合出复杂应⽤，关键是按需选取，别⼀上来就全堆上去。
LangChain核⼼架构是什么样的
LangChain 的设计其实围绕⼀个核⼼⽬标：让⼤模型能像搭积⽊⼀样灵活接⼊各种外部能⼒。它不追求把所有功能塞
进引擎，⽽是通过标准化接⼝降低扩展成本。
链（Chain） 是整个架构的组织单元，你可以把多个处理步骤串成⼀条流⽔线。⽐如先⽤ PromptTemplate ⽣成⽂
本，再交给 LLM 处理，最后调⽤ API 写⼊数据库，每个环节都是可替换的组件。
关键抽象有四个： 1）Model I/O 封装了⼤模型的输⼊输出，⽀持 OpenAI、Anthropic、HuggingFace 等主流服务 2）
Retriever 负责从外部获取数据，典型的是⽤ FAISS 或 Chroma 做向量检索 3）Tool 允许模型调⽤外部函数，⽐如搜索
天⽓、执⾏ Python 代码 4）Agent 根据 prompt 决定调⽤哪些 Tool，实现动态决策流
实际项⽬⾥，你常会看到 Agent 结合 ReAct 模式⼯作。模型输出带特殊标记的⽂本，框架解析后触发⼯具调⽤，结果
再拼回去继续推理。这种设计让逻辑闭环可以在⼀次会话中反复迭代。
和直接调 API 的最⼤区别是，LangChain 把“感知-决策-⾏动”循环变成了可配置的⼯作流。但要注意，链路越⻓，
延迟叠加越明显，调试也越困难。简单任务直接⽤ LLMClient 反⽽更稳。