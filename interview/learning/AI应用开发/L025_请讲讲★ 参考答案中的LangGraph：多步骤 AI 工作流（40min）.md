---
id: L025
source: learning
category: AI应用开发
title: 请讲讲★ 参考答案中的LangGraph：多步骤 AI 工作流（40min）
generated: 2026-07-23T15:41:19.861235
---

# 请讲讲★ 参考答案中的LangGraph：多步骤 AI 工作流（40min）

> 来源: 学习复习计划 | 分类: AI应用开发

### 3.1 信贷审批的状态机


```
rule_check ──REJECT──→ rejection_letter(LLM) ──→ END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse ──→ END
                    │
                    ├──REJECT──→ rejection_letter(LLM)
                    └──MANUAL_REVIEW──→ request_docs(LLM) ──→ END
                                            ↑
                                    用户上传材料后恢复

```

### 3.2 为什么用 LangGraph 而不是手写 if-else


```
手写 if-else 的问题:
  改流程 = 改代码 = 改 if-else 分支 = 容易出错
  异步操作(等用户上传材料) → 状态需要自己持久化
  流程可视化 → 要另外画图

LangGraph:
  加一个节点 = graph.add_node("new_step", new_step_fn)
  异步状态 = checkpointer 自动处理
  可视化 = graph.get_graph().draw_mermaid_png()

```

---