---
id: Q037
source: interview_core
category: 综合
title: 演示 citations 时，应该向面试官或同事说明什么？
generated: 2026-07-23T15:41:19.814450
---

# 演示 citations 时，应该向面试官或同事说明什么？

> 来源: 核心题库 | 分类: 综合

演示 citations 时不能只说“这里有引用”，要说明引用解决的是可信度、追溯和排查问题。
应该讲清楚每条 citation 至少包含文档来源、chunk_id、doc_id、标题、位置和相关性分数。
用户可以根据 citations 核对答案依据；研发可以根据 citations 判断错误来自哪里：
如果引用不相关，说明检索或 rerank 有问题；如果引用资料过期，说明知识库版本管理有问题；
如果引用正确但答案错，才重点看 prompt 或模型生成。生产场景里，citations 也是审计、
合规和用户信任的基础能力，尤其适用于指标口径、SQL 规范、财务、人事和合同类问答。