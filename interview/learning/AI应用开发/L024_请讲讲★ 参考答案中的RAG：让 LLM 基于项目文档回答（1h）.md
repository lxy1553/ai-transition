---
id: L024
source: learning
category: AI应用开发
title: 请讲讲★ 参考答案中的RAG：让 LLM 基于项目文档回答（1h）
generated: 2026-07-23T15:41:19.861115
---

# 请讲讲★ 参考答案中的RAG：让 LLM 基于项目文档回答（1h）

> 来源: 学习复习计划 | 分类: AI应用开发

### 2.1 RAG 的知识库 = 你的项目文档


```
问题: "night_ops_ratio_30d 超过多少算异常？"

RAG 检索:
  → config/schemas/dws_wide_table.yaml: "★ 深夜操作占比(22-05时)。>60%→高度可疑"
  → config/rules/credit_policy.yaml: "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
  → 01_system_architecture.md: "风控强特征，欺诈团伙常在夜间批量操作"

LLM 综合:
  "night_ops_ratio_30d 超过 60% 触发人工审核(RC_BH001)。
   正常范围 < 30%。> 60% 是高度可疑信号，因为欺诈团伙常在夜间操作。"

```

### 2.2 切片策略（比向量模型更重要）


```
错误做法: 每 500 字切一刀
  文档: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括..."
  一刀切在 "申请画像包括" 后面 → 丢失了具体特征列表

正确做法: 按语义边界切
  YAML: 每个顶级 key 一个 chunk（一个表定义 = 一个片段）
  SQL:  每个 CREATE TABLE 一个 chunk（一张表的完整 DDL）
  MD:   每个 ## 标题一个 chunk（一个章节一个片段）

为什么？检索时返回的是"完整片段"，不是"半句话"

```

---