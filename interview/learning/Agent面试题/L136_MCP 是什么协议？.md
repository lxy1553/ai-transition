---
id: L136
source: learning
category: Agent面试题
title: MCP 是什么协议？
generated: 2026-07-23T15:41:19.877803
---

# MCP 是什么协议？

> 来源: 学习复习计划 | 分类: Agent面试题

前面讲了 Function Call 让 LLM 能调用工具。但随着 Agent 越来越强大，需要连接的工具和服务越来越多，一个新问题浮出水面了，集成太麻烦了。
Function Call 的集成困境
想象一下，你开发了一个 Agent，需要它能连 Slack 发消息、查 Google Drive 的文档、读 GitHub 的代码、查 Postgres 数据库。
用 Function Call 的方式，你需要为每一个服务单独写适配代码，为 Slack 写一套函数定义和调用逻辑、为 Google Drive 写一套、为 GitHub 写一套、为数据库又写一套。
如果你有 N 个 AI 应用，要对接 M 个外部服务，就需要写 N × M 个定制集成。这在实际中完全不可扩展。更头疼的是，每个 LLM 厂商的 Function Call 格式还不完全一样，OpenAI 用 tool_calls，Anthropic 用 tool_use content block，参数结构也有差异。
MCP 的诞生
为了解决这个问题，Anthropic 在 2024 年 11 月开源了 MCP（Model Context Protocol，模型上下文协议）。你可以把 MCP 理解为「AI 界的 USB-C 接口」。
以前，不同的手机、电脑、设备各自用不同的充电线和接口，非常混乱。
USB-C 统一了这一切，一根线就能充电、传数据、接显示器。MCP 做的是同样的事情：它提供了一个统一的标准，让任何 AI 应用都能用同一种方式连接任何外部工具和数据源。
MCP 是怎么工作的？
MCP 的架构很清晰，主要有三个角色。
首先是 MCP Host（宿主），就是你使用的 AI 应用，比如 Claude Desktop、Cursor 编辑器、你自己开发的 Agent 应用。它是整个交互的发起方。
然后是 MCP Client（客户端），它住在 Host 里面，负责跟 MCP Server 通信。你可以把它理解为"翻译官"，Host 想要什么能力，Client 就去跟对应的 Server 沟通。
最后是 MCP Server（服务端），它负责对外暴露具体的工具能力和数据资源。比如有一个 GitHub MCP Server，它能提供"搜索代码""创建 Issue""查看 PR"等工具。一个 Slack MCP Server 能提供"发送消息""搜索频道"等工具。
整个流程就是：用户在 AI 应用中提问 → AI 应用（Host）通过 MCP Client 发现有哪些可用工具 → AI 决定调用某个工具 → MCP Client 向对应的 MCP Server 发送请求 → Server 执行操作返回结果 → AI 基于结果生成回答。
MCP 解决了什么问题？
最核心的就是把 N × M 的集成问题变成了 N + M 的问题。
以前每个 AI 应用要跟每个服务单独对接，现在每个 AI 应用只要支持 MCP 协议（实现一次 Client），每个服务只要提供一个 MCP Server（实现一次 Server），双方就能自动对接。
新增一个服务不需要改任何 AI 应用的代码，新增一个 AI 应用也不需要改任何服务的代码。
而且 MCP Server 暴露的工具是可发现的，AI 应用启动时能自动查询有哪些 MCP Server 可用、每个 Server 提供哪些工具、每个工具的参数是什么。
这意味着 Agent 可以在运行时动态发现新的能力，而不是只能用开发者写死的那些函数。