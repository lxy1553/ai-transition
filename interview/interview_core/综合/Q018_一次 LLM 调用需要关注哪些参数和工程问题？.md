---
id: Q018
source: interview_core
category: 综合
title: 一次 LLM 调用需要关注哪些参数和工程问题？
generated: 2026-07-23T15:41:19.811697
---

# 一次 LLM 调用需要关注哪些参数和工程问题？

> 来源: 核心题库 | 分类: 综合

要关注模型选择、messages、temperature、max tokens、timeout、重试、错误处理、
成本和日志。像 SQL 解释、RAG、NL2SQL 这类场景更重视准确和稳定，
通常会使用较低 temperature，并限制输出格式。
一次 LLM 调用不只是传一段 prompt。首先要选择合适模型，简单分类和结构化抽取可以用较小模型，
复杂推理或长上下文问答可能需要更强模型。messages 里要区分 system prompt、
user prompt 和检索上下文。temperature 控制随机性，生产里很多任务需要低 temperature，
避免输出漂移。max tokens 控制输出长度和成本。工程上还要设置 timeout、
重试、限流和异常处理，不能让模型调用拖垮接口。日志也很重要，
至少要记录请求 ID、模型、耗时、token、错误码和关键业务结果，
但不能把敏感数据明文打到日志里。