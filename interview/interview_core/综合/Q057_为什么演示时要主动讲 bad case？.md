---
id: Q057
source: interview_core
category: 综合
title: 为什么演示时要主动讲 bad case？
generated: 2026-07-23T15:41:19.817343
---

# 为什么演示时要主动讲 bad case？

> 来源: 核心题库 | 分类: 综合

主动讲 bad case 能体现你理解的是生产系统，而不是只会展示顺利样例。
RAG 项目一定会遇到资料缺失、召回不准、引用错误、权限边界和成本问题。
如果只展示成功样例，面试官很难判断你是否知道系统边界。
主动展示 bad case，并说明它是资料问题、检索问题、prompt 问题还是权限问题，
再给出 query rewrite、rerank、评测集、拒答和监控等改进方案，会更像真实工程复盘。