---
id: Q030
source: interview_core
category: RAG检索增强
title: RAG 问答 API 在生产环境里应该怎么设计？
generated: 2026-07-23T15:41:19.813502
---

# RAG 问答 API 在生产环境里应该怎么设计？

> 来源: 核心题库 | 分类: RAG检索增强

RAG API 不能只设计成一个返回字符串的接口。生产里至少要包括请求校验、用户身份、
权限上下文、问题文本、召回参数、答案、引用来源、request_id、错误码和日志记录。
最小接口可以是 `POST /rag/ask`，请求里包含 `question`、`user_id`、`top_k`、
`business_domain` 等字段，响应里包含 `answer`、`citations`、`cannot_answer_reason`
和 `request_id`。引用来源要能追溯到文档、chunk、位置和版本，方便用户核对，也方便研发排查。
工程上还要有 timeout、异常处理、统一响应格式和回归测试。这样 RAG 才能从本地脚本变成可接入业务系统的服务。