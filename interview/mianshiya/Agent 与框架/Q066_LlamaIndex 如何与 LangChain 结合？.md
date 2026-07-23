---
id: Q066
source: mianshiya
category: Agent 与框架
title: LlamaIndex 如何与 LangChain 结合？
generated: 2026-07-23T15:41:19.804306
---

# LlamaIndex 如何与 LangChain 结合？

> 来源: 面试鸭题库 | 分类: Agent 与框架

LlamaIndex 和 LangChain 不是⼆选⼀的关系，更多时候是配合使⽤，⼀个搞数据连接，⼀个做流程编排。
1）LlamaIndex 的核⼼是索引。它擅⻓把⾮结构化数据⽐如 PDF、数据库、⽹⻚内容，变成向量或结构化索引，⽅便
⼤模型⾼效检索。像你⽤它接 Notion、Slack 数据，做 RAG（检索增强⽣成），效果很直接。
2）LangChain 重点在链式流程。你要串起提⽰词、⼯具调⽤、记忆管理、多个 LLM 步骤，LangChain 提供了统⼀的
抽象和调度能⼒。⽐如你做⼀个客服机器⼈，要先查订单，再⽣成回复，还得记住上下⽂，这就得靠 Chain 或 Agent
模式。
它们怎么结合？常⻅两种⽅式：
第⼀种，⽤ LlamaIndex 做数据源，喂给 LangChain 流程。⽐如你在 LangChain ⾥定义⼀个 RetrievalQA 链，
retriever 直接对接 LlamaIndex 构建的 VectorStoreIndex。
第⼆种，反过来，在 LlamaIndex 的 Query Engine ⾥嵌⼊ LangChain 的组件。⽐如你让 LlamaIndex 查完数据后，
⽤ LangChain 的提⽰模板重写查询，或者调⽤外部 API 补充信息。
简单说，LlamaIndex 解决“从哪找数据”，LangChain 解决“怎么⼀步步处理”。⼀个负责精准拉取，⼀个负责逻辑
流转，搭在⼀起能快速做出复杂应⽤。