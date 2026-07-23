---
id: Q058
source: interview_core
category: RAG检索增强
title: 如何把一个 RAG Demo 包装成可投递项目？
generated: 2026-07-23T15:41:19.817464
---

# 如何把一个 RAG Demo 包装成可投递项目？

> 来源: 核心题库 | 分类: RAG检索增强

可投递的 RAG 项目不能只说“我做了向量检索和问答”。
要按生产链路包装：
离线侧讲文档接入、清洗、chunk 切分、embedding、索引和 metadata；
在线侧讲 query rewrite、检索、rerank、上下文构造、citations、拒答和 API；
质量侧讲测试集、命中率、bad case、引用准确性和回归评估；
安全侧讲权限过滤、敏感信息控制和审计；
工程侧讲日志、request_id、成本、缓存、参数校验和演示稳定性。
这样项目才像一个可落地的 AI 应用，而不是一次性脚本。