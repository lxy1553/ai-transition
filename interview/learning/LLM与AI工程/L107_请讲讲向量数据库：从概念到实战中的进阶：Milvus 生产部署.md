---
id: L107
source: learning
category: LLM与AI工程
title: 请讲讲向量数据库：从概念到实战中的进阶：Milvus 生产部署
generated: 2026-07-23T15:41:19.873508
---

# 请讲讲向量数据库：从概念到实战中的进阶：Milvus 生产部署

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 5.1 Docker 部署


```bash
# docker-compose.yml
version: '3.5'
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin

  milvus:
    image: milvusdb/milvus:v2.4.0
    depends_on: [etcd, minio]
    ports:
      - "19530:19530"

```

### 5.2 连接 Milvus


```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 连接
connections.connect(host="localhost", port="19530")

# 定义 schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
]
schema = CollectionSchema(fields, description="知识库")

# 创建 collection
collection = Collection(name="knowledge_base", schema=schema)

# 创建索引（HNSW）
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index(field_name="embedding", index_params=index_params)

```

---