---
id: Q031
source: mianshiya
category: RAG 检索增强
title: 什么是 RAG 中的 Rerank？具体需要怎么做？
generated: 2026-07-23T15:41:19.800051
---

# 什么是 RAG 中的 Rerank？具体需要怎么做？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

RAG ⾥的 Rerank 其实就是对检索阶段召回的多个⽂档⽚段，重新打分排序，挑出最相关的结果喂给⼤模型⽣成答
案。
⼀般流程是先⽤向量数据库做相似度搜索，⽐如从知识库⾥找出 top-5 的候选⽂档。但向量检索有个问题，它只看语
义相似，不⼀定和⽤户问题真正匹配。这时候就需要 Rerank 模型再筛⼀遍。
Rerank 模型通常是交叉编码器（Cross-Encoder），⽐如 BGE-Reranker 或 Cohere Rerank API。它会把⽤户问题和每
个召回的⽂档拼在⼀起输⼊模型，输出⼀个相关性分数。这个过程⽐向量检索慢，但精度⾼得多。
具体做法很简单，假设你有 5 个候选段落：
1）把 query 和每个段落组合成⼀对⽂本 2）送进 Rerank 模型得到相关性得分 3）按得分从⾼到低排序，取前 2~3 个
⾼质量段落输⼊ LLM
代码上类似这样：
# 伪代码⽰意
pairs = [(query, doc) for doc in retrieved_docs]
scores = reranker.predict(pairs)
ranked_docs = [doc for _, doc in sorted(zip(scores, retrieved_docs), reverse=True)]
要不要加 Rerank 得看场景。如果你的系统能接受⼀定噪⾳，直接⽤向量检索也⾏。但要是追求准确率，尤其是客服、
医疗这类容错低的场景，这⼀步的提升⾮常明显，基本能提 10%~20% 的最终回答准确率。