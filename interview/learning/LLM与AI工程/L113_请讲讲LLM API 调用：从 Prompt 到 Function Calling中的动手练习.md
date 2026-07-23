---
id: L113
source: learning
category: LLM与AI工程
title: 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的动手练习
generated: 2026-07-23T15:41:19.874508
---

# 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的动手练习

> 来源: 学习复习计划 | 分类: LLM与AI工程

```python
"""
练习 1: 实现一个多轮对话的"风控分析师 AI 助手"

要求:
1. 支持连续提问（多轮对话）
2. 当用户问"查数据"时，调用函数生成 SQL 并执行
3. 当用户问"什么是 XXX"时，检索 RAG 知识库
4. 控制上下文长度不超过 10 轮

练习 2: 设计一个 NL2SQL 的 System Prompt

场景: 电商数据仓库
  表: ads.ads_daily_gmv (dt, channel, gmv, order_cnt)
  表: ads.ads_product_rank (dt, product_id, sales, category)

要求: 让用户问"昨天的 GMV""最畅销品类"等，LLM 生成正确的 SQL
"""

```

---