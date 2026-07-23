---
id: Q040
source: mianshiya
category: RAG 检索增强
title: 什么是 Advanced RAG？
generated: 2026-07-23T15:41:19.801166
---

# 什么是 Advanced RAG？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

Advanced RAG 是在基础 RAG（Retrieval-Augmented Generation）之上，通过优化检索和⽣成两个环节的协同效
率，提升回答质量的⼀套⽅法论。它不是某个具体⼯具，⽽是⼀系列增强技术的组合。
1）传统 RAG 通常直接⽤⽤户问题去向量库检索，但⾃然语⾔存在歧义或表述不清的问题，导致召回不准。Advanced
RAG 会先做查询重写，⽐如⽤ LLM 把原始问题拆解成多个⼦问题，或者改写成更适合检索的关键词形式，像 DPR
（Dense Passage Retrieval）这类模型就常被⽤来做语义对⻬。
2）在检索阶段，除了单纯找 top-k 最相似的⽂档块，还会引⼊重排序（Re-Ranking）。⽐如⽤ Cross-Encoder 对初步
召回的结果做精细打分，把真正相关的排前⾯。这块可以结合 BM25 等稀疏检索做混合召回，提升覆盖度。
3）⽣成环节也不再是“⼀把喂给 LLM”。有些⽅案会做上下⽂压缩，只提取出与问题最相关的句⼦⽚段，减少噪声和
token 消耗。还有像 Self-RAG 这样的思路，让模型⾃⼰判断是否需要检索、要不要采纳检索结果，增加推理可控性。
代码上其实变化不⼤，核⼼是流程增强：
# 伪代码： Advanced RAG 流程
rewritten_query = rewrite_prompt(user_query)
docs = vector_store.search(rewritten_query, k=10)
reranked_docs = cross_encoder_rerank(rewritten_query, docs)
context = compress_context(rewritten_query, reranked_docs)
answer = llm.generate(context, user_query)
整个链路更像是⼀个可调教的系统⼯程，典型应⽤有 LangChain + FAISS/BGE + Cohere Rerank 的组合，或者是⽤
LlamaIndex 做节点后处理。关键是要能根据业务场景动态调整各模块权重，⽽不是堆模块。