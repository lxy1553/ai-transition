---
id: Q064
source: mianshiya
category: Agent 与框架
title: 如何让 LLM Agent 具备⻓期记忆能⼒？
generated: 2026-07-23T15:41:19.804092
---

# 如何让 LLM Agent 具备⻓期记忆能⼒？

> 来源: 面试鸭题库 | 分类: Agent 与框架

让 LLM Agent 有⻓期记忆，关键不是靠模型本⾝记住东西，⼤模型的上下⽂窗⼝再⼤，也就⼏⼗k到百k token，根本
存不下⻓期数据。真正的解法是外挂存储 + 检索机制。
1）把 Agent 历史交互、关键决策、⽤户偏好这些信息存到外部数据库。可以⽤向量数据库⽐如 Chroma、Pinecone
存语义向量，⽅便后续语义检索。同时⽤传统数据库如 PostgreSQL 存结构化元数据，⽐如时间、对话ID、标签等。
2）每次新请求进来，先根据当前输⼊做语义匹配，在向量库中查最相关的⼏段历史记录。这个过程叫 Retrieval-
Augmented Generation（RAG），把查到的内容拼进 prompt，⼀起喂给 LLM。
3）检索策略要设计好。不能每次都拉全部历史，会炸上下⽂。可以按时间衰减加权，或者⽤摘要压缩⽼记忆，⽐如每
天⽣成⼀个当⽇⾏为摘要存进去。
// 伪代码⽰意：记忆检索核⼼逻辑
List<Memory> recent = memoryStore.findByTimeRange(last24Hours);
List<Memory> relevant = vectorDB.similaritySearch(currentInput, topK=3);
Prompt prompt = buildPromptWithMemories(currentInput, recent, relevant);
String response = llm.generate(prompt);
memoryStore.save(new Memory(timestamp, currentInput, response)); // 写回
这么⼀来，Agent 就能“记得”⼏个⽉前的事，还能理解“上次你说不喜欢红⾊”这种指代。本质上，⻓期记忆是个
读多写少的系统，重点在快速定位有⽤信息，⽽不是全量回放。