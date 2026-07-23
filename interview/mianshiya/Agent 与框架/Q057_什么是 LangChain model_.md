---
id: Q057
source: mianshiya
category: Agent 与框架
title: 什么是 LangChain model?
generated: 2026-07-23T15:41:19.803123
---

# 什么是 LangChain model?

> 来源: 面试鸭题库 | 分类: Agent 与框架

LangChain model 并不是⼀个独⽴的模型，它其实是 LangChain 框架中对各种⼤语⾔模型（LLM）的统⼀抽象封装。
你⽤它来调⽤ GPT、通义千问、ChatGLM 这些模型时，接⼝都是⼀致的。
1）它的核⼼是提供⼀个标准接⼝，让开发者不⽤关⼼底层模型是哪家的，都能⽤同样的⽅式传⼊ prompt、拿到输
出。⽐如你切换从 OpenAI 到本地部署的 Llama，代码改动可以⾮常⼩。
2）除了基础的⽂本⽣成，它还⽀持流式输出、带历史对话的会话模型（ChatModel）、以及结构化输出解析。像和⽤
户多轮聊天的场景，直接⽤ RunnableWithMessageHistory  就能管理上下⽂。
3）实际开发⾥，你经常要拼接提⽰词、调⽤⼯具、做数据预处理。LangChain model 和 PromptTemplate、
RetrievalChain 这些组件能⽆缝配合，把这⼀整条链路串起来。
举个简单例⼦：
// 伪  Java ⻛格代码⽰意
ChatModel model = new ChatOpenAI("gpt-3.5-turbo");
String response = model.call(" 请⽤  Java 写个单例模式 ");
它真正解决的是 AI 应⽤开发中的㬵⽔问题。没有它的时候，每个模型调⽤都要写⼀堆适配代码，现在这些脏活累活框
架帮你扛住了。