# RAG 全链路详解：从文档到问答

> 目标：理解 RAG（检索增强生成）的完整流程，能独立构建端到端 RAG 系统。

---

## 一、RAG 解决了什么问题？（20min）

### 1.1 LLM 的三个"不知道"

```
问题 1: "什么是 night_ops_ratio_30d？"
  LLM 知识截止在训练数据 — 不知道你这个项目的特定概念

问题 2: "截至昨天，各渠道通过率是多少？"
  LLM 不知道实时数据 — 知识库是静态的

问题 3: "user_000042 为什么被拒？"
  LLM 没有企业内部数据的访问权限 — 这是隐私数据
```

### 1.2 RAG 的解决方案

```
用户提问
  │
  ▼
┌─────────────────┐
│  1. 检索阶段      │  ← 从知识库中找出最相关的文档片段
│  向量搜索          │
│  Top-K 检索        │
└────────┬────────┘
         │  "相关文档片段"
         ▼
┌─────────────────┐
│  2. 增强阶段      │  ← 把检索结果 + 用户问题 拼成 Prompt
│  Prompt 构造       │
│  Context 注入      │
└────────┬────────┘
         │  "完整 Prompt"
         ▼
┌─────────────────┐
│  3. 生成阶段      │  ← LLM 基于 Context 回答问题
│  LLM 回答         │
│  引用来源          │
└─────────────────┘
```

---

## 二、RAG 的核心步骤（1.5h）

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

## 参考文档

{context}

## 问题

{query}

## 要求
1. 基于参考文档回答，不要自行编造
2. 引用具体来源（文件名）
3. 如果文档内容不足以回答，说出来"""


def rag_answer(query: str, chunk_embeddings: list[dict]):
    """完整的 RAG 流程: 检索 → 增强 → 生成"""
    # Step 1: 检索 Top-3
    top_chunks = search(query, chunk_embeddings, k=3)

    # Step 2: 构造 Prompt
    prompt = build_rag_prompt(query, top_chunks)

    # Step 3: LLM 生成
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0  # RAG 场景不需要"创意"，需要"精确"
    )

    return response.choices[0].message.content
```

### 2.5 重排序（Re-ranking）— 进阶优化

```python
# 为什么需要重排序？
# 向量检索的 Top-K 可能有"语义相似但不回答问题"的 chunk
# 重排序用更强的模型（Cross-Encoder）重新打分

def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    用 Cross-Encoder 重排序。

    对比:
    向量检索（Bi-Encoder）: 快但浅 — 一次 embedding 全部存储
    重排序（Cross-Encoder）: 慢但准 — 每对(query, chunk)一起过模型
    """
    from sentence_transformers import CrossEncoder

    model = CrossEncoder('BAAI/bge-reranker-v2-m3')

    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)

    for i, c in enumerate(candidates):
        c["rerank_score"] = float(scores[i])

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates
```

---

## 三、动手练习：构建一个最小 RAG 系统（1.5h）

```python
"""
练习目标: 为项目的 Schema 文档构建 RAG 查询系统。

知识库: config/schemas/dws_wide_table.yaml
         config/rules/credit_policy.yaml
问题: "night_ops_ratio_30d 超过多少算异常？"

要求:
1. 实现文档切片（按 YAML 顶级 key 切）
2. 实现向量化（可以用 OpenAI API 或 sentence-transformers 本地模型）
3. 实现向量检索（余弦相似度，Top-3）
4. 实现 Prompt 构造 + LLM 回答
5. 验证回答质量
"""

import yaml
import numpy as np

# 这里简化: 用简单的关键词匹配替代向量检索（不需要 API key）
class MiniRAG:
    """最小 RAG 系统 — 用关键词匹配替代向量检索"""

    def __init__(self, docs_dir: str):
        self.chunks = []
        self._load_docs(docs_dir)

    def _load_docs(self, docs_dir):
        """加载 YAML 文档，按顶级 key 切分"""
        from pathlib import Path
        for yaml_file in Path(docs_dir).glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            for key, value in data.items():
                self.chunks.append({
                    "text": yaml.dump({key: value}),
                    "metadata": {"source": str(yaml_file), "key": key}
                })

    def search(self, query: str, k: int = 3) -> list[dict]:
        """用关键词匹配检索（生产中用向量检索）"""
        query_words = set(query.lower().split())
        scored = []
        for chunk in self.chunks:
            text_lower = chunk["text"].lower()
            # 计算关键词命中数量
            hits = sum(1 for w in query_words if w in text_lower)
            scored.append({"text": chunk["text"], "score": hits,
                           "metadata": chunk["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def answer(self, query: str) -> str:
        # 1. 检索
        top = self.search(query)

        # 2. 构造 Prompt
        context = "\n\n".join(c["text"] for c in top)
        prompt = f"根据以下文档回答:\n{context}\n\n问题: {query}"

        # 3. 如果是生产环境，这里调用 LLM
        # 演示: 返回检索到的文档作为模拟回答
        return f"检索到 {len(top)} 个相关文档片段:\n\n" + context


# 测试
rag = MiniRAG("credit_risk_control_system/config/schemas")
result = rag.answer("什么是 night_ops_ratio_30d？")
print(result)
```

---

## 四、RAG 的常见陷阱

| 陷阱 | 表现 | 解决方案 |
|------|------|---------|
| 检索了但没用 | LLM 忽略检索结果 | 在 Prompt 里强调"根据文档回答" |
| 切片太碎 | 丢失上下文 | 按语义边界切，500-1000 字 |
| Top-K 太大 | Context 太长，模型丢失重点 | K=3-5，结合 rerank |
| 向量不匹配 | query 和文档语义不对齐 | 用相同的 embedding 模型 |
| 知识库过时 | LLM 回答过时信息 | 定期重建索引 |
