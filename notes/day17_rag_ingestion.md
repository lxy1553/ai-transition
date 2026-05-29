# Day 17 - RAG 知识入库：索引构建

## 今日目标

今天进入 RAG 的离线入库链路。

目标不是“问答”，而是先把资料整理成系统能检索的知识库。这一步对应生产 RAG 里的文档接入、解析、切分、embedding、索引构建和版本管理。

今天产出：

- 一个本地可运行的知识入库脚本
- 一个 SQLite 知识库索引文件
- 一份入库结果摘要
- 面试题库和术语表更新

---

## 大白话解释

RAG 有两条链路：

```text
离线入库链路：提前把资料整理好
在线问答链路：用户提问时拿资料回答
```

Day 17 做的是第一条链路。

大白话：

**今天不是用户来问问题，而是先把书整理进图书馆。**

如果没有这一步，用户提问时系统就不知道去哪里找资料。所以知识入库就是把散落的 Markdown、README、规则说明、项目笔记，加工成一条条可以检索、
可以引用、
可以管理的 chunk。

---

## 生产实际

真实公司里，RAG 知识入库通常不是一次性脚本，而是一条后台数据处理链路。

它可能接入：

- 飞书 / 语雀 / Confluence 文档
- Git 仓库里的 Markdown 和 README
- 数据字典、指标平台、表结构说明
- 历史 SQL 和数据开发规范
- 工单、FAQ、客服知识库
- PDF、Word、网页和对象存储文件

生产系统通常会把入库结果拆开存：

- 表格行 1
  - 数据：原始文件
  - 生产常见存储：S3、OSS、COS、MinIO、文件系统
- 表格行 2
  - 数据：文档元数据
  - 生产常见存储：PostgreSQL、MySQL
- 表格行 3
  - 数据：chunk 正文
  - 生产常见存储：PostgreSQL、MongoDB、文档库
- 表格行 4
  - 数据：embedding 向量
  - 生产常见存储：pgvector、Milvus、Qdrant、OpenSearch
- 表格行 5
  - 数据：权限和版本
  - 生产常见存储：PostgreSQL、权限系统
- 表格行 6
  - 数据：入库日志
  - 生产常见存储：ELK、OpenSearch、ClickHouse

今天本地练习用 SQLite 简化模拟：

```text
documents 表：存文档级信息
chunks 表：存切分后的文本片段
embeddings 表：存模拟向量
ingestion_runs 表：存本次入库任务摘要
```

这样虽然不是完整生产架构，但数据结构已经贴近真实 RAG 入库系统。

---

## 今日核心流程

```text
读取知识文件
-> 计算文档 hash
-> 解析 Markdown 文本
-> 按标题和长度切 chunk
-> 给 chunk 构建 metadata
-> 生成模拟 embedding
-> 写入 SQLite
-> 输出入库摘要
```

对应生产链路：

- 表格行 1
  - 今日练习步骤：读取本地 Markdown
  - 生产环境对应能力：文档接入
- 表格行 2
  - 今日练习步骤：计算 hash
  - 生产环境对应能力：判断文档是否变化，支持增量更新
- 表格行 3
  - 今日练习步骤：按标题切 chunk
  - 生产环境对应能力：文档切分策略
- 表格行 4
  - 今日练习步骤：构建 source、title、status
  - 生产环境对应能力：metadata 管理
- 表格行 5
  - 今日练习步骤：生成模拟向量
  - 生产环境对应能力：embedding 生成
- 表格行 6
  - 今日练习步骤：写 SQLite
  - 生产环境对应能力：模拟数据库和向量库存储
- 表格行 7
  - 今日练习步骤：输出 manifest
  - 生产环境对应能力：入库任务审计和排查

---

## 常见坑

- 表格行 1
  - 问题：文档重复入库
  - 影响：检索结果重复，浪费存储
  - 生产处理方式：用 hash 去重
- 表格行 2
  - 问题：chunk 太大
  - 影响：召回不精准，token 成本高
  - 生产处理方式：按标题、段落、语义边界切分
- 表格行 3
  - 问题：chunk 太小
  - 影响：上下文丢失，模型答不完整
  - 生产处理方式：设置最小长度和 overlap
- 表格行 4
  - 问题：metadata 缺失
  - 影响：无法过滤、引用、审计
  - 生产处理方式：入库时强制写 doc_id、source、权限、版本
- 表格行 5
  - 问题：无权限标签
  - 影响：可能泄露内部资料
  - 生产处理方式：文档和 chunk 都要带权限信息
- 表格行 6
  - 问题：无版本字段
  - 影响：用户查到旧口径
  - 生产处理方式：保留 version、updated_at、status
- 表格行 7
  - 问题：只存向量
  - 影响：无法回查原文和来源
  - 生产处理方式：向量、正文、metadata 分开存

---

## 工程取舍

今天为什么用 SQLite，而不是直接上 Milvus 或 pgvector？

原因是当前目标是先理解“入库数据结构”和“离线处理链路”。SQLite 足够模拟文档表、chunk 表、embedding 表和入库任务表。

生产环境里可以这样升级：

```text
SQLite documents/chunks
-> PostgreSQL documents/chunks
-> pgvector 或 Milvus 存 embedding
-> Redis 缓存高频检索结果
-> OpenSearch / ELK 存日志
```

今天的设计重点不是追求最强检索性能，而是先把数据边界想清楚：

- 原始文档属于文档存储
- chunk 正文属于数据库
- embedding 属于向量索引
- metadata 用来过滤、权限和引用
- ingestion run 用来审计和排查

---

## 本地练习

项目路径：

```text
projects/day17_rag_ingestion/
```

运行：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

脚本会读取这些文件：

```text
notes/day12_sql_explainer_cli.md
notes/day13_sql_explainer_enhancement.md
notes/day15_rag_preparation.md
notes/day16_rag_basics.md
notes/terminology_glossary.md
```

输出：

```text
projects/day17_rag_ingestion/output/rag_index.sqlite
projects/day17_rag_ingestion/output/ingestion_manifest.json
```

---

## 生产级理解

面试里如果被问“RAG 入库链路怎么做”，不要只说“把文档向量化”。

更完整的说法是：

> 生产级 RAG 入库会先接入原始文档，解析正文，清洗去重和脱敏，
> 然后按业务语义切 chunk，为每个 chunk 补充 source、doc_id、权限、
> 版本、更新时间等 metadata，再生成 embedding，分别写入文档库、
> 元数据库和向量库。这样在线检索时才能做权限过滤、版本控制、引用溯源和质量排查。

---

## 面试沉淀

今天新增一个生产高频问题：

```text
RAG 知识入库和索引构建在生产环境里怎么设计？
```

这个问题已补充到：

```text
docs/interview_core_questions.md
```

---

## 术语更新

今天新增或强化这些术语：

- Ingestion / 入库
- Document Hash / 文档指纹
- Metadata / 元数据
- Index / 索引
- Incremental Update / 增量更新

这些术语已补充到：

```text
notes/terminology_glossary.md
```

---

## 今日复盘

今天要记住三句话：

1. RAG 入库不是简单存文件，而是把资料变成可检索、可过滤、可引用的知识单元。
2. 生产里不要把所有内容都塞进向量库，正文、向量、metadata、日志要分层存储。
3. 入库质量决定后面召回质量，召回质量决定最终回答质量。

---

## 每日核心问题自测

> 回答通过校验后，才把当天学习状态标记为完成。
> 用户回答通过校验前，不提前写参考答案；通过后在对应问题后追加参考答案。

### A. 今日核心问题

### 1. RAG 知识入库和索引构建在生产环境里怎么设计？
我的回答：

### 2. 为什么生产级 RAG 要分离线入库和在线问答两条链路？
我的回答：

### 3. chunk 的 metadata 应该包含哪些信息，为什么重要？
我的回答：

### 4. 文档 hash 和增量更新解决什么问题？
我的回答：

### 5. 入库质量差会如何影响后续召回和回答？
我的回答：

### B. 前两天核心回顾

### 6. [Day 15] 生产环境里的 RAG 系统一般怎么设计？
我的回答：

### 7. [Day 15] 为什么做 RAG 前要先整理知识库清单？
我的回答：

### 8. [Day 16] RAG 的基本流程是什么？
我的回答：

### 9. [Day 16] 为什么 RAG 需要返回引用来源，而不只是答案？
我的回答：
