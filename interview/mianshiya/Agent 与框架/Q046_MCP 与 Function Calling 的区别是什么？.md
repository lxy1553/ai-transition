---
id: Q046
source: mianshiya
category: Agent 与框架
title: MCP 与 Function Calling 的区别是什么？
generated: 2026-07-23T15:41:19.801911
---

# MCP 与 Function Calling 的区别是什么？

> 来源: 面试鸭题库 | 分类: Agent 与框架

MCP 和 Function Calling 看似都在让模型“调⽤功能”，但它们的定位和机制完全不同。
MCP 其实是⼀种协议，更准确地说是 Model Context Protocol，它定义了外部系统如何向⼤模型提供上下⽂、⼯具
描述以及如何接收模型的结构化输出。它不绑定具体实现，强调的是模型与环境之间的标准化交互⽅式。你可以把它
理解成⼀个通⽤的“插件通信规范”，像 GitHub Copilot Extensions 就基于这类思想构建扩展能⼒。
⽽ Function Calling 是具体的能⼒，指的是⼤模型能根据输⼊决定是否调⽤某个预定义函数，并⽣成符合 schema 的
参数。主流闭源模型如 GPT-4 都⽀持这个特性，它是实现 Agent ⾏为的基础组件之⼀。⽐如你⽤ LangChain 写个天⽓
查询，模型会判断⽤户意图后返回 {"name": "get_weather", "arguments": {"city": "Beijing"}}  这样
的结构。
关键区别在于：Function Calling 是单⼀模型对外暴露的能⼒接⼝，MCP 则是多个系统间协作的协议框架，⽀持更复
杂的双向交互和资源共享。