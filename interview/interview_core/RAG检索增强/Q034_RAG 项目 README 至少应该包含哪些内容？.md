---
id: Q034
source: interview_core
category: RAG检索增强
title: RAG 项目 README 至少应该包含哪些内容？
generated: 2026-07-23T15:41:19.814043
---

# RAG 项目 README 至少应该包含哪些内容？

> 来源: 核心题库 | 分类: RAG检索增强

RAG 项目 README 不能只写启动命令，至少要包含项目目标、适用场景、架构流程、
离线入库说明、在线问答流程、启动命令、接口请求示例、响应示例、固定测试问题、
常见失败场景、当前限制和后续优化方向。对于 API 项目，还应该写清 `/health`、
`/rag/ask` 的输入输出字段，尤其是 `citations`、`request_id`、`confidence`
和 `cannot_answer_reason` 的含义。README 的作用是让业务、后端、测试和面试官
能快速理解这个项目解决什么问题、怎么运行、怎么判断效果好不好，以及哪些边界不能越过。