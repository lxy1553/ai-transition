# Day 17 - RAG 知识入库

这个项目模拟生产级 RAG 的离线入库链路。

它会读取本地学习资料，切分成 chunk，生成模拟 embedding，
并把 documents、chunks、embeddings、ingestion_runs 写入 SQLite。

## 运行

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

## 输出

```text
projects/day17_rag_ingestion/output/rag_index.sqlite
projects/day17_rag_ingestion/output/ingestion_manifest.json
```

## 生产映射

| 本地 Demo | 生产环境 |
|-----------|----------|
| SQLite documents 表 | PostgreSQL / MySQL 文档元数据表 |
| SQLite chunks 表 | PostgreSQL / MongoDB chunk 正文表 |
| SQLite embeddings 表 | pgvector / Milvus / Qdrant |
| ingestion_manifest.json | 入库任务日志和审计记录 |
| 本地 Markdown | 飞书、Confluence、Git、PDF、对象存储 |
