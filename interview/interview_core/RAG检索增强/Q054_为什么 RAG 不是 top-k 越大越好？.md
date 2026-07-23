---
id: Q054
source: interview_core
category: RAG检索增强
title: 为什么 RAG 不是 top-k 越大越好？
generated: 2026-07-23T15:41:19.816935
---

# 为什么 RAG 不是 top-k 越大越好？

> 来源: 核心题库 | 分类: RAG检索增强

top-k 越大，召回覆盖面可能更高，但进入上下文的噪声、token 成本和延迟也会增加。
无关 chunk 进入 prompt 后，模型可能被干扰，引用错误资料，甚至生成看似有依据但实际不准确的答案。
生产里通常会“召回多一点，最终使用少一点”：
先召回一批候选，再用权限过滤、rerank、去重和 token budget 选出少量高质量资料。
top-k 的选择要通过固定评测集验证，而不是凭感觉调大。