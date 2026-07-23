---
id: L126
source: learning
category: LLM与AI工程
title: 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的动手练习（1h）
generated: 2026-07-23T15:41:19.876407
---

# 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的动手练习（1h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

```python
"""
练习 1: 用 LangChain 实现 NL2SQL Agent

要求:
1. 定义两个工具: query_warehouse(sql), get_schema(table_name)
2. Agent 先获取 Schema → 再生成 SQL → 执行 SQL → 返回结果
3. 支持"查一下 2026-07-01 各渠道通过率"这类问题

练习 2: 用 LangGraph 实现客服质检工作流

状态:
  Text → Classify → [投诉] → RouteToAgent → LLM生成摘要 → END
                    [简单问题] → AutoReply → END
                    [复杂问题] → Escalate → END
"""

```

---