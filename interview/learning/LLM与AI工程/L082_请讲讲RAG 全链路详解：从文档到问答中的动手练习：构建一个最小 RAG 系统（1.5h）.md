---
id: L082
source: learning
category: LLM与AI工程
title: 请讲讲RAG 全链路详解：从文档到问答中的动手练习：构建一个最小 RAG 系统（1.5h）
generated: 2026-07-23T15:41:19.869830
---

# 请讲讲RAG 全链路详解：从文档到问答中的动手练习：构建一个最小 RAG 系统（1.5h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

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