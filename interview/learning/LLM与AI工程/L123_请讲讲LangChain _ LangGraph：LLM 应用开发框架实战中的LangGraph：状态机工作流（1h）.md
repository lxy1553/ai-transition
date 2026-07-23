---
id: L123
source: learning
category: LLM与AI工程
title: 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph：状态机工作流（1h）
generated: 2026-07-23T15:41:19.875864
---

# 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph：状态机工作流（1h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 3.1 Chain vs Graph 的区别


```
Chain (串行): A → B → C → D
  固定的、线性的执行路径
  不能分支、不能循环、不能等待

Graph (有向图):
  A → [条件] → [B → C → D]
            → [E → F] → G → ...
  可以分支（条件路由）
  可以循环（状态机）
  可以等待人工输入（异步）

```

**LangGraph 用 StateGraph 来定义有状态的工作流。**

### 3.2 核心概念


```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

# ═══════════════════════════════════════════
# 概念 1: State（状态）
#   TypedDict — 定义工作流中传递的数据结构
# ═══════════════════════════════════════════

class ApprovalState(TypedDict):
    """信贷审批工作流的状态 — 在各个节点之间传递"""
    user_id: str
    score: int
    decision: str      # APPROVE / REJECT / MANUAL_REVIEW
    reason: str
    rejected: bool


# ═══════════════════════════════════════════
# 概念 2: Nodes（节点）
#   每个节点是一个函数: 输入 State → 修改 State → 输出
# ═══════════════════════════════════════════

def rule_check(state: ApprovalState) -> ApprovalState:
    """节点1: 规则引擎检查"""
    print(f"[规则引擎] 检查 {state['user_id']}")
    state["rejected"] = False
    return state

def model_score(state: ApprovalState) -> ApprovalState:
    """节点2: 模型评分"""
    state["score"] = 672
    return state


# ═══════════════════════════════════════════
# 概念 3: Edges（边）
#   条件边: 根据 State 决定下一步
#   普通边: 固定走到下一个节点
# ═══════════════════════════════════════════

def route_after_rules(state: ApprovalState) -> Literal["rejected", "scoring"]:
    """
    条件边: 规则检查后决定去哪
    - 如果命中硬拒绝 → 去 rejection 节点
    - 否则 → 去模型评分节点
    """
    if state.get("rejected"):
        return "rejected"
    return "scoring"


# ═══════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════

workflow = StateGraph(ApprovalState)

# 注册节点
workflow.add_node("check", rule_check)
workflow.add_node("scoring", model_score)
workflow.add_node("rejection", lambda s: s)

# 设置入口
workflow.set_entry_point("check")

# 设置边
workflow.add_conditional_edges(
    "check",
    route_after_rules,
    {"rejected": "rejection", "scoring": "scoring"}
)
workflow.add_edge("scoring", END)
workflow.add_edge("rejection", END)

# 编译
app = workflow.compile()

```

### 3.3 实战：信贷审批完整工作流


```python
"""
本例实现信贷审批的完整状态机:

rule_check ──REJECT──→ rejection_letter → END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse → END
                    │
                    ├──MANUAL_REVIEW──→ request_docs → 【等待用户上传】→ model_score
                    └──REJECT──→ rejection_letter → END
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
import json


# ── 状态定义 ──
class CreditState(TypedDict):
    user_id: str
    features: dict
    rule_hits: list[str]
    score: int
    decision: str
    reason: str
    required_docs: list[str]


# ── 节点函数 ──

def rule_check(state: CreditState) -> CreditState:
    """节点1: 规则引擎检查 — 需要实现短路逻辑"""
    hits = []
    if state["features"].get("in_blacklist"):
        hits.append("BLACKLIST_HIT")
        state["decision"] = "REJECT"
        state["reason"] = "命中黑名单"
    state["rule_hits"] = hits
    print(f"  [规则] 命中: {hits}")
    return state


def model_scoring(state: CreditState) -> CreditState:
    """节点2: 模型评分"""
    # 模拟 XGBoost 推理
    prob = 0.3  # 违约概率
    score = int(600 + 50 / 0.693 * (1 - prob) / prob)  # 简化评分公式
    state["score"] = score
    print(f"  [模型] 评分: {score}")
    return state


def request_docs(state: CreditState) -> CreditState:
    """节点3 (LLM): 生成需要补充的材料清单"""
    docs = {
        "收入不稳定": "收入证明、银行流水",
        "多头借贷": "现有贷款合同明细",
        "设备异常": "人脸识别视频验证",
    }
    # 根据规则命中情况生成
    state["required_docs"] = [docs.get(state["reason"], "身份证明")]
    print(f"  [LLM] 请补充材料: {state['required_docs']}")
    return state


def rejection_letter(state: CreditState) -> CreditState:
    """节点4 (LLM): 生成拒绝通知"""
    letter = f"""尊敬的{state['user_id']}:
    很抱歉，您的贷款申请未通过。
    原因: {state['reason']}
    您有权在 15 个工作日内申请人工复核。"""
    state["reason"] = letter
    print(f"  [LLM] 已生成拒绝函")
    return state


def disburse(state: CreditState) -> CreditState:
    """节点5: 放款"""
    print(f"  [放款] 已向 {state['user_id']} 放款 ¥5,000")
    return state


# ── 路由函数 ──

def route_after_rules(state) -> Literal["REJECT", "PROCEED"]:
    if state["decision"] == "REJECT":
        return "REJECT"
    return "PROCEED"


def route_after_scoring(state) -> Literal["APPROVE", "MANUAL_REVIEW", "REJECT"]:
    score = state["score"]
    if score >= 600:
        return "APPROVE"
    elif score >= 500:
        return "MANUAL_REVIEW"
    else:
        return "REJECT"


# ── 构建图 ──

def build_credit_workflow():
    graph = StateGraph(CreditState)

    graph.add_node("rule_check", rule_check)
    graph.add_node("model_scoring", model_scoring)
    graph.add_node("request_docs", request_docs)
    graph.add_node("rejection_letter", rejection_letter)
    graph.add_node("disburse", disburse)

    # 条件边: 规则引擎 → 拒绝/继续
    graph.add_conditional_edges(
        "rule_check",
        route_after_rules,
        {
            "REJECT": "rejection_letter",
            "PROCEED": "model_scoring"
        }
    )

    # 条件边: 模型评分 → 通过/人工/拒绝
    graph.add_conditional_edges(
        "model_scoring",
        route_after_scoring,
        {
            "APPROVE": "disburse",
            "MANUAL_REVIEW": "request_docs",
            "REJECT": "rejection_letter"
        }
    )

    graph.add_edge("disburse", END)
    graph.add_edge("rejection_letter", END)
    graph.add_edge("request_docs", END)  # 等待用户上传 — 异步恢复

    graph.set_entry_point("rule_check")
    return graph.compile()


# ── 执行 ──
workflow = build_credit_workflow()

# 场景 1: 正常用户
result = workflow.invoke({
    "user_id": "user_000042",
    "features": {"in_blacklist": False, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']}")

# 场景 2: 黑名单用户
result = workflow.invoke({
    "user_id": "user_000999",
    "features": {"in_blacklist": True, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']} — 原因: {result['reason'][:30]}...")

```

---