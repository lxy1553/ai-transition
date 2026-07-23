---
id: L081
source: learning
category: LLM与AI工程
title: 请讲讲RAG 全链路详解：从文档到问答中的要求
generated: 2026-07-23T15:41:19.869710
---

# 请讲讲RAG 全链路详解：从文档到问答中的要求

> 来源: 学习复习计划 | 分类: LLM与AI工程

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