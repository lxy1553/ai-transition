---
id: Q015
source: interview_core
category: 综合
title: JSON 合法和业务校验通过有什么区别？
generated: 2026-07-23T15:41:19.811260
---

# JSON 合法和业务校验通过有什么区别？

> 来源: 核心题库 | 分类: 综合

JSON 合法只说明格式能被解析，比如括号、引号、逗号没错。
业务校验通过还要求字段完整、类型正确、枚举值合法，并且符合业务规则。
比如 `risk_level` 必须是固定枚举，`can_publish` 必须和风险等级一致。
JSON 合法是语法层面的概念，程序能 `json.loads` 解析就算合法。
但生产系统还需要业务层校验。比如 SQL 解释结果里必须有 `summary`、`tables`、
`risk_level`、`risks` 和 `suggestions`。其中 `risk_level` 不能随便写，
必须是 `low`、`medium`、`high` 这类固定枚举。`risks` 应该是数组，
每个风险最好有类型、说明和建议。更进一步，业务规则也要一致：
如果风险等级是 high，`can_publish` 就不能是 true。否则 JSON 虽然合法，
但下游系统会误判。生产里通常用 Pydantic、JSON Schema 或自定义规则做这层校验。