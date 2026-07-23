---
id: Q045
source: interview_core
category: RAG检索增强
title: expected_sources 在 RAG 测试集中有什么作用？
generated: 2026-07-23T15:41:19.815817
---

# expected_sources 在 RAG 测试集中有什么作用？

> 来源: 核心题库 | 分类: RAG检索增强

expected_sources 是每条测试问题应该命中的资料来源，用来判断检索是否找到了正确依据。
没有 expected_sources，系统即使返回了几个看起来相关的 chunk，也很难客观判断是否真的召回了正确资料。
它可以用于计算 hit_rate、hit_rank 和 citations 准确性。
当 expected source 没进入 top-k，
说明检索或知识库侧有问题；如果进入但排名靠后，说明排序或 rerank 需要优化；如果引用正确但答案错，
才重点看 prompt 或模型生成。生产里 expected_sources 是 RAG 评测从“凭感觉”走向“可回归”的关键字段。