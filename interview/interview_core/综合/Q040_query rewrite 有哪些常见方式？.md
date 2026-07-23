---
id: Q040
source: interview_core
category: 综合
title: query rewrite 有哪些常见方式？
generated: 2026-07-23T15:41:19.815101
---

# query rewrite 有哪些常见方式？

> 来源: 核心题库 | 分类: 综合

query rewrite 常见方式包括规则词典改写、同义词扩展、业务术语补全、上下文补全、
精确实体保留、多 query 拆分和 LLM 改写。规则词典适合高频、稳定的业务词，比如把
“来源”扩展成 citations、引用来源、可追溯；同义词扩展适合用户表达和文档表达不一致；
上下文补全适合“这个怎么算”这类指代问题；多 query 适合一个问题包含多个检索方向；
LLM 改写适合复杂口语表达。生产里通常先用可解释规则做第一版，再用测试集验证收益，
最后再考虑 LLM rewrite 和 rerank 配合。