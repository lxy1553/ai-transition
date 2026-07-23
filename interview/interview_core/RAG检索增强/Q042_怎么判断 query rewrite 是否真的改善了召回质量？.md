---
id: Q042
source: interview_core
category: RAG检索增强
title: 怎么判断 query rewrite 是否真的改善了召回质量？
generated: 2026-07-23T15:41:19.815415
---

# 怎么判断 query rewrite 是否真的改善了召回质量？

> 来源: 核心题库 | 分类: RAG检索增强

判断 query rewrite 是否有效，不能只看某一次答案是否变好，而要用固定测试集评估。
每条样本应该包含原始问题、期望来源、问题类型和必要的标准答案要点。评估时先看
expected source 是否进入 top-k，再看命中排名是否更靠前，同时观察无关 chunk 是否增加。
如果 rewritten query 提高了 hit_rate 和 avg_hit_rank，并且 citations 更相关，说明有正向收益。
如果命中率提高但噪声也明显增加，就要结合 rerank、限制扩展词或调整规则。生产里还要记录
original query、rewritten query、召回结果、最终引用和用户反馈，持续分析 bad case。