---
id: Q029
source: mianshiya
category: RAG 检索增强
title: 当发现RAG系统召回结果与⽤户query意图不匹配时，有哪些可能的改进⽅向？
generated: 2026-07-23T15:41:19.799836
---

# 当发现RAG系统召回结果与⽤户query意图不匹配时，有哪些可能的改进⽅向？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

RAG 系统召回结果偏离⽤户意图，问题通常出在检索和⽣成两个环节的衔接上。先定位是“没找到”还是“找到了但
没⽤好”。
1）优化检索阶段的语义匹配能⼒
query 本⾝可能有歧义或表述不清晰，直接搜容易翻⻋。可以⽤ query 改写来增强表达，⽐如⽤⼤模型把原始 query
扩展成多个相关问法，再并⾏检索。像 LangChain 提供了 MultiQueryRetriever  就是⼲这个的。另外，
embedding 模型是否适配业务场景也很关键，通⽤模型如 text-embedding-ada-002 在垂直领域可能不如微调过的
BGE 或 m3e。
2）提升⽂档切分的合理性
chunk 太⼤，关键信息被稀释；太⼩，上下⽂丢失。⼀般建议按语义切分，⽐如⽤ LangChain 的
RecursiveCharacterTextSplitter  结合 sentence transformers 做句⼦边界感知。chunk size 控制在
256~512 token ⽐较常⻅，具体得看内容密度。
3）引⼊重排序（Rerank）机制
初检可能召回⼀堆相关度⼀般的⽂档，加⼀层 cross-encoder 重排能显著提升 TopK 质量。像 Cohere 的 reranker、
bge-reranker 都可以直接调⽤，把最相关的⼏个往前顶，让 LLM 看到更准的信息。
4）调整⽣成阶段的提⽰⼯程
有时候检索是对的，但 prompt 写得太松，模型⾃⼰脑补。要明确约束“基于以下上下⽂回答”，并在输⼊⾥只放⾼相
关度的 chunk。也可以做 query 路由，判断是否⾛检索流程，避免⽆关 query 强⾏查库。
线上可以接反馈闭环，⽐如⽤户点赞/点踩驱动 embedding 或 reranker 微调，持续迭代。