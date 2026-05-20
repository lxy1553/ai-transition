"""Day 16 - RAG 基础本地模拟。

这个脚本不用真实向量库和大模型，而是用关键词计数模拟 embedding 和相似度检索。
用途是先看懂 RAG 的核心链路：文档切成 chunk、问题向量化、top-k 召回、带来源生成回答草稿。
"""

import math
from dataclasses import dataclass


DOCUMENTS = [
    {
        "source": "sql_explainer_readme",
        "text": "SQL 解释助手 CLI 可以输入 SQL，输出 summary、tables、fields、risk_level、can_publish、risks 和 suggestions。",
    },
    {
        "source": "sql_risk_rules",
        "text": "SQL 解释助手当前能识别 select *、缺少 where、缺少 dt 分区、group by、order by 等常见数仓风险。",
    },
    {
        "source": "tool_use_note",
        "text": "Tool Use 是让模型负责调度，把查表结构、查指标口径、检查 SQL 风险等确定性任务交给工具。",
    },
    {
        "source": "rag_definition",
        "text": "RAG 是先从知识库检索相关资料，再让模型基于资料生成回答，适合回答项目文档、指标口径和表结构问题。",
    },
]

VOCABULARY = [
    "sql",
    "解释",
    "风险",
    "where",
    "dt",
    "group",
    "order",
    "tool",
    "rag",
    "知识库",
    "检索",
    "指标",
    "表结构",
]


@dataclass
class Chunk:
    """知识库里的一个文档片段。

    RAG 不直接把整篇长文档塞给模型，而是把文档切成更小的 chunk，方便精准召回和引用。
    """

    chunk_id: str
    source: str
    text: str


@dataclass
class SearchResult:
    """一次检索命中的结果。

    chunk 是被召回的资料，score 表示它和用户问题的相似程度。
    """

    chunk: Chunk
    score: float


def chunk_documents() -> list[Chunk]:
    """把示例文档转换成 chunk 列表。

    这里每条示例文档直接变成一个 chunk，是为了简化学习。
    真实项目里会按标题、段落、表结构或指标口径切分。
    """
    chunks: list[Chunk] = []
    for index, document in enumerate(DOCUMENTS, start=1):
        chunks.append(
            Chunk(
                chunk_id=f"chunk_{index}",
                source=document["source"],
                text=document["text"],
            )
        )
    return chunks


def embed_text(text: str) -> list[float]:
    """用关键词出现次数模拟文本向量。

    真实 embedding 会用模型把文本转成高维向量。
    这里用词频向量，是为了在本地直观看懂“文本变数字后才能算相似度”。
    """
    lowered = text.lower()
    return [float(lowered.count(word.lower())) for word in VOCABULARY]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个向量的余弦相似度。

    分数越高，说明问题和 chunk 在当前词表下越相关。
    如果某个向量全是 0，说明没有命中任何关键词，直接返回 0。
    """
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieve(query: str, chunks: list[Chunk], top_k: int = 3) -> list[SearchResult]:
    """根据用户问题检索最相关的 top-k chunk。

    这一步对应 RAG 里的 retrieval。
    后续生成答案质量的上限，很大程度取决于这里能不能找对资料。
    """
    query_vector = embed_text(query)
    results = []
    for chunk in chunks:
        chunk_vector = embed_text(chunk.text)
        score = cosine_similarity(query_vector, chunk_vector)
        results.append(SearchResult(chunk=chunk, score=score))
    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def build_answer(query: str, results: list[SearchResult]) -> str:
    """基于召回结果拼一个回答草稿。

    这里不调用 LLM，而是直接把资料列出来。
    重点是让你看到答案应该带来源和分数，方便判断依据是否可靠。
    """
    lines = [
        f"问题：{query}",
        "回答草稿：",
        "根据当前知识库，相关信息如下：",
    ]
    for result in results:
        lines.append(f"- {result.chunk.text}（来源：{result.chunk.source}，score={result.score:.3f}）")
    return "\n".join(lines)


def main() -> None:
    """运行一次最小 RAG 流程：切分、检索、输出带来源的回答草稿。"""
    query = "SQL 解释助手能识别哪些风险？"
    chunks = chunk_documents()
    results = retrieve(query=query, chunks=chunks, top_k=3)

    print("=== Chunks ===")
    for chunk in chunks:
        print(f"{chunk.chunk_id} | {chunk.source} | {chunk.text}")

    print("\n=== Top-k Results ===")
    for result in results:
        print(f"{result.chunk.chunk_id} | score={result.score:.3f} | source={result.chunk.source}")

    print("\n=== Answer Draft With Citations ===")
    print(build_answer(query, results))


if __name__ == "__main__":
    main()
