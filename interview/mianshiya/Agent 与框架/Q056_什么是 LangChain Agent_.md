---
id: Q056
source: mianshiya
category: Agent 与框架
title: 什么是 LangChain Agent?
generated: 2026-07-23T15:41:19.803024
---

# 什么是 LangChain Agent?

> 来源: 面试鸭题库 | 分类: Agent 与框架

LangChain Agent 的本质是⼀个能做决策的“⼤脑”，它不直接⽣成最终结果，⽽是根据⽬标动态规划步骤，调⽤⼯具
去执⾏。
1）Agent 会接收⽤户输⼊，结合预设的提⽰词和可⽤⼯具描述，决定下⼀步动作。这个动作要么是调⽤某个⼯具（⽐
如搜索、数据库查询），要么是直接返回结果。
2）它依赖 LLM 做推理判断。⽐如你问“今天上海天⽓怎么样”，Agent 会先意识到需要实时数据，于是选择调⽤天⽓
API ⼯具，拿到结果后再让 LLM 汇总成⾃然语⾔回复。
3）⼯具（Tools）是关键组件，每个⼯具对应⼀个函数，声明了名称、描述和⼊参。Agent 不直接写代码，⽽是通过
描述理解⼯具能⼒。你可以接⼊ SerpAPI 做搜索，或者⾃定义⼀个查订单的函数。
// 伪代码⽰意：定义⼀个搜索⼯具
Tool searchTool = Tool.builder()
.name("search")
.description(" ⽤于查询实时信息，⽐如天⽓、新闻 ")
.function(query -> callSerpAPI(query))
.build();
和普通 Chain 的区别在于，Chain 是固定流程，Agent 是动态路径。你没法提前预知它会怎么⾛，就像你不能预测⼈
思考的过程。
适合场景：需要多步推理、外部数据获取、动态决策的任务。但如果逻辑简单，直接写 Chain 更⾼效，别为了⽤⽽
⽤。