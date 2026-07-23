---
id: Q052
source: interview_core
category: RAG检索增强
title: 生产 RAG 怎么控制 token 成本和响应延迟？
generated: 2026-07-23T15:41:19.816667
---

# 生产 RAG 怎么控制 token 成本和响应延迟？

> 来源: 核心题库 | 分类: RAG检索增强

生产 RAG 控制成本和延迟，核心是减少无效上下文和重复计算。
检索阶段先用 metadata filter 缩小范围，避免无权限、无关文档进入候选。
重排阶段对候选 chunk 做 rerank、低分过滤和去重。
上下文组装阶段设置 token budget，只保留最相关、最有依据的少量 chunk。
模型调用阶段控制 max tokens，并对简单问题使用更便宜的模型。
对高频问题、固定口径和低风险 FAQ，可以缓存召回结果或最终答案。
同时每次请求都要记录 input token、output token、延迟、缓存命中率和 request_id，
这样才能判断优化有没有真实效果。