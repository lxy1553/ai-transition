---
id: L051
source: learning
category: 数据仓库
title: 请讲讲数据血缘 + SchemaRegistry 元数据管理中的今天要点
generated: 2026-07-23T15:41:19.864991
---

# 请讲讲数据血缘 + SchemaRegistry 元数据管理中的今天要点

> 来源: 学习复习计划 | 分类: 数据仓库

```
SchemaRegistry 的三个价值:
  1. 代码可消费: NL2SQL 可以直接读 schema 构造 LLM Prompt
  2. 数据可自描述: 数据目录下的 _TABLE_SCHEMA.json 让别人也能读懂
  3. 变更可追溯: schema 和代码一起用 git 管理

数据血缘的两种形态:
  1. 表级: 层与层之间的流转关系（哪张 DWD 表生成了哪张 DWS 表）
  2. 列级: 每个特征追溯到 DWD 源列和聚合公式

```

---