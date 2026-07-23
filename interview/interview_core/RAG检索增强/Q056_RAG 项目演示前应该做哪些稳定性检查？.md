---
id: Q056
source: interview_core
category: RAG检索增强
title: RAG 项目演示前应该做哪些稳定性检查？
generated: 2026-07-23T15:41:19.817210
---

# RAG 项目演示前应该做哪些稳定性检查？

> 来源: 核心题库 | 分类: RAG检索增强

演示前要检查三类链路。
第一是前置条件，例如索引文件是否存在、依赖是否可用、固定回归问题是否能跑完。
第二是成功路径，例如典型问题能返回 answer、citations、request_id、confidence 和 latency。
第三是边界路径，例如空问题、top_k 越界、无相关资料时是否有清楚错误提示或 cannot_answer_reason。
还要准备一份固定演示脚本和检查报告，避免现场临时选问题导致结果不稳定。