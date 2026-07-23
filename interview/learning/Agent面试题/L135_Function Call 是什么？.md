---
id: L135
source: learning
category: Agent面试题
title: Function Call 是什么？
generated: 2026-07-23T15:41:19.877680
---

# Function Call 是什么？

> 来源: 学习复习计划 | 分类: Agent面试题

前面我们聊 Agent 的时候反复提到一个词，「工具调用」。Agent 能查天气、能搜索信息、能操作数据库，这些能力是怎么实现的？
答案就是 Function Call（函数调用）。
从「只会说话」到「能做事情」
2023 年之前，大语言模型只能做一件事：生成文本。你问它问题，它给你一段文字回答，仅此而已。它说的再好听，也只是「说」，不能「做」。
Function Call 的出现彻底改变了这个局面。它是 OpenAI 在 2023 年 6 月率先推出的一种能力，简单来说就是让 LLM 不仅能生成文字，还能告诉外部程序「我想调用某个函数，参数是这些」。
打个比方。在没有 Function Call 之前，LLM 就像一个只能写字的人，你问他天气，他只能根据记忆回答「上海通常三月份比较潮湿」。
有了 Function Call 之后，这个人学会了「打电话」，你问他天气，他会拿起电话拨给天气台（调用天气 API），听到对方报的实时数据后再告诉你「今天上海 22°C，多云」。
Function Call 的工作原理
Function Call 的工作流程分四步。
第一步，定义函数。开发者预先告诉 LLM「你手边有哪些工具可以用」，用 JSON 格式描述每个函数的名字、功能说明和参数。比如你告诉它有一个 get_weather 函数，接收一个城市名参数，返回天气信息。
```
{
"tools": [
{
"type": "function",
"function": {
"name": "get_weather",
"description": "获取指定城市的实时天气",
"parameters": {
"type": "object",
"properties": {
"city": {
"type": "string",
"description": "城市名称，比如：上海"
}
},
"required": ["city"]
}
}
}
]
}
```
第二步，模型判断。用户提问后，LLM 分析用户的意图，自己判断「要回答这个问题，我需要调用哪个函数」。如果用户问「上海今天天气如何」，LLM 会决定调用 get_weather，并生成参数 {"city": "上海"}。
```
{
"tool_calls": [
{
"type": "function",
"function": {
"name": "get_weather",
"arguments": "{\"city\": \"上海\"}"
}
}
]
}
```
第三步，执行函数。注意，这一步非常关键，LLM 自己并不执行函数。它只是输出了「我想调用这个函数，参数是这些」的结构化指令。真正执行函数的是你的应用程序。你的代码拿到 LLM 返回的调用指令后，解析出 city=上海，去实际调用天气 API，拿到结果比如 22度，多云。
第四步，生成回答。你的代码把拿到的真实温度数据再次发给 LLM。LLM 这次有了客观数据支撑，就会用非常自然的人类语言回复你：今天上海天气是多云，气温大约 22 摄氏度。
为什么 Function Call 这么重要？
你可能会觉得，这不就是「让 LLM 调 API」吗？有什么了不起的？
关键在于，Function Call 解决了两个核心问题。
第一个是**"什么时候调用"的判断问题**，LLM 能根据用户的自然语言意图，自动判断需不需要调用工具、调用哪个工具。你不需要写复杂的条件判断逻辑，LLM 自己会推理。
第二个是**"传什么参数"的提取问题**，LLM 能从用户的自然语言中提取出结构化的参数。用户说"帮我查一下北京后天的天气"，LLM 能自动提取出 city=北京 和 date=后天。
这两个能力加在一起，就把 LLM 从一个「只会聊天的文本生成器」变成了一个「能理解意图并驱动外部系统的决策引擎」。
而这正是 Agent 的基石。可以说，Function Call 就是 Agent 能力的最底层技术基础，没有 Function Call，Agent 就无法调用工具，也就没法真正「做事」。
目前几乎所有主流大模型都支持 Function Call，包括 OpenAI 的 GPT 系列、Anthropic 的 Claude 系列、Google 的 Gemini 系列，以及各种开源模型如 Llama 等。虽然各家的 API 格式略有不同，但核心原理是一样的。
Function Call 和 Agent 的关系
最后说一下两者的关系。
Function Call 是一次性的「单步调用」，LLM 判断需要调用一个函数，调用完就结束了。而 Agent 是「循环调用」，Agent 在一个循环中反复使用 Function Call，每次调用后观察结果，再决定下一步要不要继续调用其他函数。
所以 Function Call 是 Agent 的「原子操作」，Agent 是 Function Call 的「高级编排」。一个 Agent 完成一个复杂任务，可能需要连续进行十几次 Function Call。