---
id: Q023
source: mianshiya
category: RAG 检索增强
title: 什么是 RAG 中的分块？为什么需要分块？
generated: 2026-07-23T15:41:19.798910
---

# 什么是 RAG 中的分块？为什么需要分块？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

RAG 的上下⽂⻓度是有限的，⽐如主流模型⼀般⽀持 32k 或 128k 的 token 上下⽂。你塞进去的 prompt 越⻓，能留
给检索内容的空间就越少。分块其实就是把原始⽂档切成适合模型处理的⼩段落，让每次检索和⽣成都能在上下⽂窗
⼝内完成。
1）分块不是简单按段落切。如果按固定字符数切，可能把⼀句话从中间劈开，语义就断了。好的分块策略会尽量保持
语义完整，⽐如⽤ 递归分割，先按标题切，再按段落，最后才是固定⻓度。LangChain ⾥的
RecursiveCharacterTextSplitter  就是这么⼲的。
2）块太⼩，信息不全，模型容易“只⻅树⽊不⻅森林”；块太⼤，⼜挤占上下⽂，影响其他 prompt 内容。⼀般来
说，512 到 1024 个 token 是⽐较常⻅的块⼤⼩，具体得看你的数据和模型。
3）有些场景还得考虑跨块关联。⽐如⼀个技术⽅案分布在三个块⾥，单靠⼀个块检索出来，模型也拼不全逻辑。这时
候就得靠后续的查询扩展或多步检索来补救。
代码上⼤概⻓这样：
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
chunk_size=512,
chunk_overlap=50,
separators=["\n\n", "\n", " 。 ", " ", ""]
)
docs = splitter.split_text(large_document)
要不要分块，其实取决于你的数据形态和检索⽬标。像 PDF、⻓⽹⻚这种肯定要分，但如果是短问答对，可能直接喂
进去就⾏。