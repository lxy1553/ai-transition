---
id: Q129
source: interview_core
category: Agent
title: 为什么 Agent 端到端评测不能只看最终回答文字？
generated: 2026-07-23T15:41:19.826293
---

# 为什么 Agent 端到端评测不能只看最终回答文字？

> 来源: 核心题库 | 分类: Agent

Agent 端到端评测不能只看最终回答文字，因为最终回答可能看起来合理，但内部路线是错的。
例如实时问题误走离线日报，口径问题误走 SQL，敏感导出问题中间已经查了 DWD 明细，最终文本即使没有泄露数据，也说明安全边界已经被突破。

金融信贷数据 Agent 的正确性包括多层：意图是否识别正确、工具是否路由正确、前置条件是否满足、SQL 是否安全、实时延迟是否检查、证据是否返回、审计是否记录。
这些都不是只看最终自然语言能判断的。

所以端到端评测要检查结构化 trace，包括 route、tool_calls、status、evidence、audit、refusal_reason 和 final_answer。
一句面试总结是：生产 Agent 评测的是链路正确，不只是回答像样。