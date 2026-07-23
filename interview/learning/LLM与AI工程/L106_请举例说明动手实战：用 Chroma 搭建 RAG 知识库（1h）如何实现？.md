---
id: L106
source: learning
category: LLM与AI工程
title: 请举例说明动手实战：用 Chroma 搭建 RAG 知识库（1h）如何实现？
generated: 2026-07-23T15:41:19.873372
---

# 请举例说明动手实战：用 Chroma 搭建 RAG 知识库（1h）如何实现？

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 4.1 安装与初始化


```bash
pip install chromadb sentence-transformers

```

### 4.2 完整代码


```python
import chromadb
from sentence_transformers import SentenceTransformer
import yaml
from pathlib import Path

class LocalKnowledgeBase:
    """基于 Chroma 的本地知识库"""

    def __init__(self, persist_dir: str = "./knowledge_base"):
        # 使用本地 embedding 模型（不需要 API key）
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # 持久化存储 — 下次启动不需要重建
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 创建 collection（类似 MySQL 中的表）
        self.collection = self.client.get_or_create_collection(
            name="credit_risk_docs",
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    # ═══ 写入: 文档 → 切片 → embedding → 存储 ═══
    def add_yaml_file(self, file_path: str):
        """
        添加 YAML 文件到知识库。

        切片策略: 按顶级 key 切（每张表/每条规则一个 chunk）
        metadata 包含: 源文件、chunk 名称
        """
        with open(file_path) as f:
            data = yaml.safe_load(f)

        for key, value in data.items():
            text = yaml.dump({key: value})
            embedding = self.embedder.encode(text).tolist()

            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"source": str(file_path), "key": key}],
                ids=[f"{Path(file_path).stem}__{key}"]
            )

        print(f"  已添加 {len(data)} 个 chunk 到知识库: {file_path}")

    # ═══ 读取: 问题 → embedding → 向量检索 → Top-K ═══
    def search(self, query: str, k: int = 5) -> list[dict]:
        """
        向量检索 — 核心操作

        query_embedding: 用户的自然语言问题 → embedding
        n_results: 返回多少个最相关的文档片段
        """
        query_embedding = self.embedder.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        # 格式化返回
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "text": results['documents'][0][i],
                "score": 1 - results['distances'][0][i],  # 余弦距离 → 相似度
                "metadata": results['metadatas'][0][i],
            })
        return formatted


# ═══════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════

def build_project_knowledge_base():
    """为项目构建完整的向量知识库"""
    kb = LocalKnowledgeBase()

    # 添加 Schema 文档
    schemas_dir = Path("config/schemas")
    for yaml_file in schemas_dir.glob("*.yaml"):
        kb.add_yaml_file(yaml_file)

    # 添加规则文档
    kb.add_yaml_file("config/rules/credit_policy.yaml")

    return kb


def demo_query():
    kb = build_project_knowledge_base()

    queries = [
        "night_ops_ratio_30d 超过多少算异常？",
        "什么情况下会被拒绝贷款？",
        "on_time_rate 新用户默认值是多少？",
    ]

    for q in queries:
        print(f"\n🔍 查询: {q}")
        results = kb.search(q, k=2)
        for r in results:
            print(f"  [相似度 {r['score']:.3f}] {r['text'][:80]}...")


if __name__ == "__main__":
    demo_query()

```

### 4.3 查询结果示例


```
🔍 查询: night_ops_ratio_30d 超过多少算异常？
  [相似度 0.89] type: DOUBLE | 范围: [0.0, 1.0] | >60%→高度可疑
  [相似度 0.72] aggregation: mean(event_time.hour IN [22,23,0,1,2,3,4,5])

🔍 查询: 什么情况下会被拒绝贷款？
  [相似度 0.83] id: BLACKLIST_HIT | condition: user_id_in_blacklist == True
  [相似度 0.76] id: FRAUD_SCORE_HIGH | condition: fraud_score > 0.8

```

---