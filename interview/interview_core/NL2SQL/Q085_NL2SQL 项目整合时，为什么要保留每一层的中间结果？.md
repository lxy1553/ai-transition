---
id: Q085
source: interview_core
category: NL2SQL
title: NL2SQL 项目整合时，为什么要保留每一层的中间结果？
generated: 2026-07-23T15:41:19.821140
---

# NL2SQL 项目整合时，为什么要保留每一层的中间结果？

> 来源: 核心题库 | 分类: NL2SQL

NL2SQL 项目整合时必须保留每一层的中间结果，因为问题可能出在任何阶段。
如果最终答案错了，需要知道是问题解析漏了时间，Schema Router 选错表，
SQL Generator 生成错字段，SQL Validator 没拦住风险，Executor 执行方言不兼容，
还是 Interpreter 解释过度。
保留中间结果可以支持调试、审计、回放和评测。
生产里还可以用 request_id 把用户问题、解析结果、SQL、校验结果、执行状态、
返回行数和业务解释串起来，这样 bad case 才能被定位和修复。