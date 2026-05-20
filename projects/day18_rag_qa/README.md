# Day 18 - RAG 检索与引用

这个项目模拟 RAG 的在线问答链路。

它会读取 Day 17 生成的 SQLite 知识库索引，根据用户问题检索相关 chunk，
然后返回一个带引用来源的回答草稿。

## 前置步骤

先生成索引：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

## 运行

默认问题：

```bash
python3 projects/day18_rag_qa/main.py
```

自定义问题：

```bash
python3 projects/day18_rag_qa/main.py --question "RAG 知识入库怎么设计？" --top-k 4
```

保存样例输出：

```bash
python3 projects/day18_rag_qa/main.py --save-output
```

## 输出

```text
projects/day18_rag_qa/output/sample_answer.json
```

## 生产映射

| 本地 Demo | 生产环境 |
|-----------|----------|
| SQLite 读取 chunk | PostgreSQL / 文档库读取 chunk 正文 |
| 本地向量相似度 | pgvector / Milvus / Qdrant / OpenSearch |
| top-k 检索 | 召回候选文档片段 |
| citations | 用户可见引用和研发排查依据 |
| 本地 JSON 输出 | API 响应体和请求日志 |
