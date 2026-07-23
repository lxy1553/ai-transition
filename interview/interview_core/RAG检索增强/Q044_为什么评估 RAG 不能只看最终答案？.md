---
id: Q044
source: interview_core
category: RAG检索增强
title: 为什么评估 RAG 不能只看最终答案？
generated: 2026-07-23T15:41:19.815687
---

# 为什么评估 RAG 不能只看最终答案？

> 来源: 核心题库 | 分类: RAG检索增强

RAG 的最终答案是多个环节叠加后的结果，只看答案无法判断问题出在哪里。一个答案错误，
可能是知识库没有正确资料，也可能是 chunk 切分不合理、query rewrite 改写偏移、top-k 太小、
metadata 过滤误伤、rerank 排序错误，或者模型生成时没有忠实依据。评估时要拆开看：
先看检索层 expected source 是否进入 top-k，再看 citations 是否正确，最后看答案是否基于上下文。
这样才能把问题定位到资料、检索、引用、生成或工程稳定性，而不是盲目改 prompt。