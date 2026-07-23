---
id: Q049
source: mianshiya
category: Agent 与框架
title: LangGraph 编排的原理是什么？
generated: 2026-07-23T15:41:19.802232
---

# LangGraph 编排的原理是什么？

> 来源: 面试鸭题库 | 分类: Agent 与框架

LangGraph 的本质是把⼤模型的执⾏过程变成⼀个有向图，每个节点是⼀个动作或决策点，边代表执⾏路径。你给它
⼀个输⼊，它就从起点开始，按图的结构⼀步步⾛，⾛到哪、下⼀步⼲啥，由当前节点的逻辑决定。
1）节点可以是调⽤⼤模型、执⾏⼯具、做条件判断，甚⾄是⼈⼯审核这种阻塞操作。⽐如在客服机器⼈⾥，⼀个节点
可能是“识别⽤户意图”，下⼀个节点根据意图跳转到“查订单”或者“投诉处理”。
2）每⼀步的状态都通过⼀个共享的 state 对象传递，这个 state 是可变的，后续节点能读也能改。这就让整个流程有
了上下⽂记忆，不像普通函数调⽤那样孤⽴。
3）控制流靠的是 conditional edges，也就是条件边。你可以写个函数判断 state ⾥的字段，返回下⼀个节点的名字。
⽐如判断“是否需要⼈⼯介⼊”，返回 "human_in_the_loop" 或 "continue_automated"。
代码上其实就是定义节点函数和边规则：
graph.add_node("generate", generate)
graph.add_conditional_edges("generate", route_generate_result)
整个执⾏过程是同步推进的，但每步之间可以暂停、恢复，适合⻓周期任务。像 AutoGen、CrewAI 这些框架底层也⽤
了类似思路，只是 LangGraph 更灵活，⽀持复杂 DAG。