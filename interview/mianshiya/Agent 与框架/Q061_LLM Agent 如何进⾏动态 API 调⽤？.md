---
id: Q061
source: mianshiya
category: Agent 与框架
title: LLM Agent 如何进⾏动态 API 调⽤？
generated: 2026-07-23T15:41:19.803781
---

# LLM Agent 如何进⾏动态 API 调⽤？

> 来源: 面试鸭题库 | 分类: Agent 与框架

LLM Agent 做动态 API 调⽤，关键在于把⾃然语⾔意图转成结构化请求，中间靠 ⼯具抽象 和 运⾏时绑定 撑起来。
Agent 不是直接拼 URL 调接⼝，⽽是通过定义好的⼯具描述（Tool Description），让模型知道“我能⼲啥”。⽐如你
接⼊了⻜书消息 API 或内部⼯单系统，就封装成 tool，带上 name、description、parameters，⽤ JSON Schema 描
述输⼊格式。模型输出会明确说“我要⽤ send_message 这个⼯具，参数是 to=张三, content=上线提醒”，⽽不是⾃
由发挥写⼀段话。
真正执⾏时，Agent 框架捕获这个调⽤意图，拿参数去实例化真实请求。这块⼀般有统⼀的 Tool Executor，注册所有
可⽤⼯具，做参数校验、鉴权、重试，再发出去。像 LangChain、LlamaIndex 都是这么搞的，你⾃⼰写也建议拆成
两层：⼀层对⻬模型理解，⼀层处理 HTTP、序列化这些脏活累活。
代码上⼤概⻓这样：
record SendMsgTool(@NonNull String to, @NonNull String content) implements Tool {
public void run() {
// 实际调⻜书  Webhook
HttpClient.newCall(req -> req.url("https://open.feishu.cn/path")
.post(json(to, content)));
}
}
整个流程其实是“模型提议 + 系统执⾏”的分离设计。模型压根不经过⽹络层，只负责决策调哪个⼯具；真正的 API
调⽤由运⾏时安全落地，避免幻觉乱发请求。⾼频场景⽐如⾃动查数据库、触发 CI/CD、拉取监控指标，都是靠这套
机制扛住的。