---
id: Q043
source: mianshiya
category: Prompt 与结构化输出
title: 什么是 GPT Structured Outputs？
generated: 2026-07-23T15:41:19.801548
---

# 什么是 GPT Structured Outputs？

> 来源: 面试鸭题库 | 分类: Prompt 与结构化输出

GPT Structured Outputs 是⼀种让⼤模型输出结构化数据的能⼒，⽐如 JSON 格式的结果，⽽不是⾃由⽂本。这在需
要程序直接解析模型输出的场景⾥特别有⽤。
你告诉模型你想要的 schema，它就会按这个格式返回数据。这样⼀来，前端或后端代码就能直接消费输出，不⽤再
写⼀堆正则或逻辑去提取信息。
⽐如你在调⽤ GPT 时启⽤ response_format  参数，并指定为 JSON Schema，模型就会严格按字段输出。OpenAI
从 2023 年底开始⽀持这个功能，适⽤于像 gpt-3.5-turbo 和 gpt-4 这样的模型。
{
"name": "Alice",
"age": 30,
"city": "Beijing"
}
这种机制适合做配置⽣成、表单填充、API 数据抽取等任务。和以前“靠运⽓”解析⽂本不同，现在结果可预测、可验
证。
不过得注意，模型不会⾃动知道什么时候该输出结构，必须显式设置参数，否则还是⾛⾃由⽣成。另外复杂 schema
可能增加 token 消耗，设计时要权衡清晰度与成本。
如果原题解中的某句话使⽤了超链接，不要对这句话做任何改动。