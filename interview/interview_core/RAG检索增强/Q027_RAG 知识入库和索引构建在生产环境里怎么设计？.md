---
id: Q027
source: interview_core
category: RAG检索增强
title: RAG 知识入库和索引构建在生产环境里怎么设计？
generated: 2026-07-23T15:41:19.813091
---

# RAG 知识入库和索引构建在生产环境里怎么设计？

> 来源: 核心题库 | 分类: RAG检索增强

生产级 RAG 入库不是简单把文档丢进向量库。
完整流程一般包括文档接入、解析、清洗去重、脱敏、chunk 切分、metadata 构建、
embedding 生成、向量索引构建和版本管理。这样在线检索时才能做权限过滤、
引用溯源、增量更新和质量排查。
我会把 RAG 入库看成离线数据处理链路。首先接入原始资料，比如飞书文档、
Confluence、Git README、数据字典、指标口径和历史 SQL。然后解析成正文，
清理页眉页脚、重复内容和废弃版本，并在入库前做脱敏和权限标记。
接着按标题、段落、问答、指标或表结构切成 chunk。每个 chunk 都要带 metadata，
比如 doc_id、source、business_domain、permission、version、updated_at 和 status。
然后生成 embedding，把向量写入向量库，把正文和元数据写入数据库。
生产里还要记录文档 hash，用于判断文档是否变化，支持增量更新和版本回滚。
这样设计的好处是，在线问答时不仅能检索相似内容，还能按权限和版本过滤，
并且回答可以追溯到原始文档。