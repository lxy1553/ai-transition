---
id: Q038
source: interview_core
category: RAG检索增强
title: 本地 RAG 项目当前有哪些限制，后续可以怎么优化？
generated: 2026-07-23T15:41:19.814768
---

# 本地 RAG 项目当前有哪些限制，后续可以怎么优化？

> 来源: 核心题库 | 分类: RAG检索增强

当前本地 RAG 项目的主要限制是：embedding 使用关键词计数模拟，不是真实语义向量；
answer 还是基于召回 chunk 的答案草稿，没有接真实 LLM；user_id 和 business_domain
只是预留字段，还没有做真实权限过滤；评测集规模较小；也没有缓存、限流、监控、
服务部署和完整接口测试。后续可以从几层优化：替换真实 embedding 模型和向量数据库；
增加 query rewrite、混合检索和 rerank；接入 LLM 并要求只基于引用上下文回答；
增加权限过滤、敏感信息控制和访问审计；扩大评测集，加入拒答、权限、资料冲突和 bad case；
最后补 Docker、配置管理、日志监控和自动化接口测试。