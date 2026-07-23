---
id: 附-06
source: mianshiya
category: 未分类
title: 请描述使用LangChain构建一个文档问答系统的关键技术组件及实现步骤
generated: 2026-07-23T15:41:19.807653
---

# 请描述使用LangChain构建一个文档问答系统的关键技术组件及实现步骤

> 来源: 面试鸭题库 | 分类: 未分类

构建⽂档问答系统，本质是把⾮结构化⽂本转成向量，再结合⼤模型做⾃然语⾔交互。LangChain 提供了⼀整套⼯具
链来简化这个过程。
1）⽂档加载与分割
先⽤ DocumentLoaders 从 PDF、Word 或⽹⻚抓取原始内容。拿到⽂本后得切分，⼀般按段落或固定⻓度（⽐如 500
token），太⻓会超出模型上下⽂，太短⼜丢失语义。这⾥常⽤ RecursiveCharacterTextSplitter。
2）向量化与检索
切好的⽂本块喂给嵌⼊模型（Embedding Model），⽐如 OpenAI 的 text-embedding-ada-002 或开源的 BGE。⽣成
的向量存进向量数据库，像 Chroma、Pinecone 或 Milvus。⽤户提问时，系统先把问题向量化，去库⾥找最相似的
top-k ⽂本块，这叫相关性检索。
3）提⽰⼯程与模型调⽤
检索到的上下⽂拼上⽤户问题，组装成 prompt，丢给⼤语⾔模型（LLM）。LangChain 提供 PromptTemplate 来规范
格式，避免模型胡说。典型的模板就是“根据以下内容回答问题：{context} 问题：{question}”。
4）链式调⽤（Chain）
把上述步骤串起来⽤ LLMChain 或 RetrievalQA 链。RetrievalQA 是现成的⾼级封装，⼀⾏代码就能连起检索器和
LLM，适合快速搭建原型。
整个流程⾥，数据预处理和检索质量直接决定效果上限。模型再强，喂进去的上下⽂不对，也搞不定准确回答。