---
id: L080
source: learning
category: LLM与AI工程
title: 请讲讲RAG 全链路详解：从文档到问答中的RAG 的核心步骤（1.5h）
generated: 2026-07-23T15:41:19.869540
---

# 请讲讲RAG 全链路详解：从文档到问答中的RAG 的核心步骤（1.5h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 2.1 文档切片（Chunking）— 最重要但最容易被忽略


```python
# 为什么切片策略比向量模型更重要？

# 错误做法: 按固定长度切（500字一刀）
# 正文: "特征分为三类: 申请画像、行为衍生、还款表现。
#        申请画像包括 apply_amount_avg, monthly_income..."
# 切片1: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括"
# 切片2: "apply_amount_avg, monthly_income..."
# ❌ 检索到切片2 → LLM 不知道这是"申请画像"的一部分 → 回答不完整

# 正确做法: 按语义边界切
# YAML: 每个顶级 key 一个 chunk
# SQL:  每个 CREATE TABLE 一个 chunk
# MD:   每个 ## 标题一个 chunk

```

**不同文档类型的切片策略**：


```python
def chunk_document(file_path: str) -> list[dict]:
    """根据文件类型选择不同的切片策略"""
    if file_path.endswith('.yaml'):
        # YAML: 按顶级 key 切
        with open(file_path) as f:
            data = yaml.safe_load(f)
        return [
            {"text": yaml.dump({k: v}), "metadata": {"key": k, "source": file_path}}
            for k, v in data.items()
        ]

    elif file_path.endswith('.sql'):
        # SQL: 按 CREATE TABLE 切
        with open(file_path) as f:
            content = f.read()
        stmts = [s.strip() for s in content.split(';') if 'CREATE TABLE' in s]
        return [
            {"text": s, "metadata": {"type": "ddl", "source": file_path}}
            for s in stmts
        ]

    elif file_path.endswith('.md'):
        # Markdown: 按 ## 标题切
        with open(file_path) as f:
            content = f.read()
        chunks = re.split(r'\n## ', content)
        return [
            {"text": f"## {chunk}", "metadata": {"source": file_path}}
            for chunk in chunks if chunk.strip()
        ]

    else:
        # 其他: 按段落切（每段至少 100 字）
        ...

```

### 2.2 向量化（Embedding）


```python
def embed_chunks(chunks: list[dict], embedding_model: str = "text-embedding-3-small"):
    """
    将文本片段转为向量。

    为什么向量？因为文本不能直接做相似度搜索。
    向量化的目标是: 语义相近的文本 → 向量距离近 → 检索准确

    三种选择:
    1. OpenAI text-embedding-3-small  — 性价比最高, 1536 维
    2. BAAI/bge-large-zh              — 中文场景最强开源
    3. text-embedding-3-large         — 精度最高, 3072 维
    """
    import openai

    texts = [chunk["text"] for chunk in chunks]
    response = openai.embeddings.create(
        model=embedding_model,
        input=texts
    )
    embeddings = [item.embedding for item in response.data]

    # 每个 chunk 带上 embedding 和 metadata
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i]

    return chunks

```

### 2.3 向量检索（Similarity Search）


```python
import numpy as np

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度 — 衡量两个向量的方向一致性"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(query: str, chunk_embeddings: list[dict],
           query_embedding_model: str = "text-embedding-3-small", k: int = 3):
    """
    检索最相关的 K 个文档片段。

    Step 1: 用户问题 → 向量
    Step 2: 向量 vs 所有 chunk → 算相似度
    Step 3: 排序 → 取 Top-K

    为什么用余弦相似度不是欧氏距离？
    余弦: 只关心方向 — 适合检索语义相似的文本
    欧氏: 关心距离 — 不适合高维向量（维度灾难）
    """
    # Step 1: 用户问题向量化
    query_vector = embed_chunks([{"text": query}])

    # Step 2: 算相似度
    results = []
    for chunk in chunk_embeddings:
        score = cosine_similarity(query_vector, chunk["embedding"])
        results.append({"text": chunk["text"], "score": score,
                        "metadata": chunk.get("metadata", {})})

    # Step 3: 取 Top-K
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]

```

### 2.4 Prompt 构造 + LLM 回答


```python
def build_rag_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    """构造 RAG 的 Prompt — 把检索结果作为 Context 注入"""
    context = "\n\n".join(
        f"[来源: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
        for chunk in retrieved_chunks
    )

    return f"""请根据以下文档内容回答问题。如果文档中没有相关信息，请明确说"未找到相关信息"。