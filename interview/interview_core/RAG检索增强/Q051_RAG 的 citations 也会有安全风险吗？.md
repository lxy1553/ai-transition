---
id: Q051
source: interview_core
category: RAG检索增强
title: RAG 的 citations 也会有安全风险吗？
generated: 2026-07-23T15:41:19.816374
---

# RAG 的 citations 也会有安全风险吗？

> 来源: 核心题库 | 分类: RAG检索增强

citations 也会有安全风险。
引用里可能包含敏感文档标题、路径、chunk 内容、业务域、版本或内部系统地址。
即使答案正文没有泄露，citation 也可能暴露用户无权知道的资料存在。
生产里 citations 要和答案正文一样做权限过滤和脱敏处理。
普通用户只看到允许访问的来源信息；
研发和审计人员可以在后台通过 request_id 查看更完整的召回链路。