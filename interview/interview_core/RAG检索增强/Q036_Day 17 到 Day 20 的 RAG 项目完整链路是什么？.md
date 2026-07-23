---
id: Q036
source: interview_core
category: RAG检索增强
title: Day 17 到 Day 20 的 RAG 项目完整链路是什么？
generated: 2026-07-23T15:41:19.814312
---

# Day 17 到 Day 20 的 RAG 项目完整链路是什么？

> 来源: 核心题库 | 分类: RAG检索增强

Day 17 到 Day 20 串起来就是一个最小 RAG 工程闭环。Day 17 负责离线入库：
读取学习笔记和项目资料，清洗正文，切分 chunk，生成学习版 embedding，
把 chunk、向量、来源、位置和 metadata 写入 SQLite 索引。Day 18 负责在线问答：
接收用户问题，从索引中召回 top-k chunk，并返回答案草稿和 citations。Day 19 负责
召回优化：用固定测试问题对比 baseline、query rewrite 和 top-k 策略，记录 bad case。
Day 20 负责 API 化：用 FastAPI 提供 `/health` 和 `/rag/ask`，响应中返回 answer、
citations、request_id、confidence、cannot_answer_reason 和 latency_ms。
这个链路体现的是
从资料治理到接口交付的完整过程。