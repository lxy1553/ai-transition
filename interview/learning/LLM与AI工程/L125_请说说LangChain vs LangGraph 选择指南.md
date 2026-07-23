---
id: L125
source: learning
category: LLM与AI工程
title: 请说说LangChain vs LangGraph 选择指南
generated: 2026-07-23T15:41:19.876296
---

# 请说说LangChain vs LangGraph 选择指南

> 来源: 学习复习计划 | 分类: LLM与AI工程

| 场景 | 用 LangChain | 用 LangGraph |
|------|:----------:|:----------:|
| 简单的 Prompt → LLM → 输出 | ✅ | ❌ 杀鸡用牛刀 |
| 多步链式调用（A→B→C） | ✅ | 也✅ |
| 有分支的路由（if-else 决策） | ❌ | ✅ |
| 循环直到条件满足 | ❌ | ✅ |
| 等待人工输入 | ❌ | ✅ |
| 复杂状态机 | ❌ | ✅ |


```
一句话: 顺序执行用 Chain，条件分支用 Graph，人工干预用 Graph + Checkpointer。

```

---