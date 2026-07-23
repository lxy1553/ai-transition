---
id: Q026
source: mianshiya
category: RAG 检索增强
title: 在 RAG 中，你知道有哪些 Embedding Model 嵌⼊模型？
generated: 2026-07-23T15:41:19.799248
---

# 在 RAG 中，你知道有哪些 Embedding Model 嵌⼊模型？

> 来源: 面试鸭题库 | 分类: RAG 检索增强

Embedding 模型在 RAG ⾥头其实就⼲⼀件事：把⽂本转成向量，让检索系统能算相似度。选对模型直接影响召回质
量。
主流的通⽤嵌⼊模型有 Sentence-BERT（SBERT），它在 BERT 基础上加了个池化层，专⻔优化句⼦级表⽰。⽐如你
⽤ paraphrase-MiniLM-L6-v2 ，⼩模型快，适合轻量场景。
进阶⼀点的是 Cohere 提供的 multilingual-2 和 command-r 系列，尤其是多语⾔⽀持好，在跨语⾔检索⾥表现稳。
Cohere 的 API 易⽤，但得⾛⽹络请求。
还有 OpenAI 的 text-embedding-ada-002，虽然不开放本地部署，但在英⽂任务上精度⾼，适合不想调参直接上⽣产
的场景。
开源界现在⽤得猛的是 BGE（来⾃智源研究院），⽐如 bge-small-zh-v1.5，中⽂场景下效果拉满，本地跑起来也顺。
它通过“查询-⽂档”对增强训练，特别适配 RAG 的检索偏好。
别忘了还有 Jina AI 推的 jina-embeddings-v2，⽀持 8192 token ⻓度，⻓⽂本处理有优势，⽽且许可友好，能商⽤。
选模型得看三点：语⾔是否匹配、延迟能不能压住、有没有⻓⽂本需求。别⼀上来就⽤⼤模型，⼩模型蒸馏过的在
90% 场景都够⽤。
实际项⽬⾥，BGE + Milvus 是中⽂ RAG 的常⻅组合，本地可控⼜⾼效。