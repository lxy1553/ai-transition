---
id: Q048
source: interview_core
category: RAG检索增强
title: RAG 幻觉通常怎么产生，怎么降低？
generated: 2026-07-23T15:41:19.816111
---

# RAG 幻觉通常怎么产生，怎么降低？

> 来源: 核心题库 | 分类: RAG检索增强

RAG 幻觉常见原因包括知识库资料缺失、chunk 切分不合理、检索没有命中正确资料、
query rewrite 改写偏移、无关上下文被塞进 prompt、模型没有被限制只基于引用回答。
降低幻觉要从链路上处理，而不是只改 prompt。
离线侧要保证资料可信、切分合理、版本清楚；
检索侧要提高 expected source 命中率，必要时使用混合检索和 rerank；
生成侧要要求答案必须有 citations 支撑；
边界侧要在无依据、低置信度、越权和敏感场景下拒答；
评测侧要长期维护 bad case 和拒答样本。