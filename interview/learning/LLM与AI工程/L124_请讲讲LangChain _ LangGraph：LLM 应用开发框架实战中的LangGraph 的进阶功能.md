---
id: L124
source: learning
category: LLM与AI工程
title: 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph 的进阶功能
generated: 2026-07-23T15:41:19.876174
---

# 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph 的进阶功能

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 4.1 条件循环（human-in-the-loop）


```python
# 当用户补充材料时，工作流需要恢复
# LangGraph 的 checkpointer 可以自动保存状态

from langgraph.checkpoint.memory import MemorySaver

# 使用持久化存储
checkpointer = MemorySaver()

workflow = build_credit_workflow()
app = workflow.compile(checkpointer=checkpointer)

# 第一次执行: 暂停在 request_docs 等待用户上传
config = {"configurable": {"thread_id": "user_000042_session"}}
result = app.invoke(input_data, config=config)

# 用户上传材料后: 恢复执行
# update_state 从上次暂停处继续
app.update_state(config, {"required_docs": []})
result = app.invoke(None, config=config)

```

### 4.2 可视化


```python
# 生成工作流图
from IPython.display import Image, display

display(Image(workflow.get_graph().draw_mermaid_png()))
# → 直接看到审批流程图

```

---