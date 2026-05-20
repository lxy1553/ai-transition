"""Day 18 - RAG 在线问答脚本。

这个脚本读取 Day 17 生成的 SQLite 知识库索引，根据用户问题检索相关 chunk，
再返回答案草稿和 citations。它对应生产 RAG 的在线链路：用户提问 -> 检索 -> 组织答案 -> 返回引用。
"""

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "projects/day17_rag_ingestion/output/rag_index.sqlite"
OUTPUT_PATH = Path(__file__).resolve().parent / "output/sample_answer.json"

VOCABULARY = [
    "sql",
    "风险",
    "where",
    "dt",
    "分区",
    "rag",
    "生产",
    "文档",
    "知识库",
    "入库",
    "索引",
    "chunk",
    "embedding",
    "召回",
    "在线",
    "问答",
    "引用",
    "来源",
    "可追溯",
    "权限",
    "版本",
    "metadata",
    "query",
    "rewrite",
    "改写",
    "tool",
    "结构化",
]


@dataclass
class SearchResult:
    """一次在线检索命中的 chunk。

    除了文本内容，还保留 source_path、position、score 等字段，
    是为了让最终答案能追溯到原始资料。
    """

    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    content: str
    position: int
    score: float


def embed_text(text: str) -> list[float]:
    """用和 Day 17 一致的词表生成问题向量。

    检索时问题和文档必须用同一套 embedding 方式。
    如果两边模型或词表不一致，相似度分数就没有意义。
    """
    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算问题向量和 chunk 向量的相似度。

    Day 17 已经把 chunk embedding 做过归一化，所以这里点积就能近似余弦相似度。
    """
    if not left or not right:
        return 0.0
    return min(sum(a * b for a, b in zip(left, right)), 1.0)


def load_search_results(question: str, top_k: int) -> list[SearchResult]:
    """从 SQLite 索引中加载 chunk，并按问题相似度取 top-k。

    这是在线问答最核心的检索步骤。
    如果 Day 17 索引不存在，说明离线入库没跑，在线问答不能继续。
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Day 17 索引不存在，请先运行：python3 projects/day17_rag_ingestion/main.py"
        )

    question_embedding = embed_text(question)
    results = []

    # 只检索 active chunk，模拟生产里过滤掉已下线、废弃或无效的知识片段。
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            select
                c.chunk_id,
                c.doc_id,
                c.source_path,
                c.title,
                c.content,
                c.position,
                e.embedding_json
            from chunks c
            join embeddings e on c.chunk_id = e.chunk_id
            where json_extract(c.metadata_json, '$.status') = 'active'
            """
        ).fetchall()

    for row in rows:
        embedding = json.loads(row[6])
        score = cosine_similarity(question_embedding, embedding)
        if score <= 0:
            continue
        results.append(
            SearchResult(
                chunk_id=row[0],
                doc_id=row[1],
                source_path=row[2],
                title=row[3],
                content=row[4],
                position=row[5],
                score=round(score, 6),
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)
    return deduplicate_results(results)[:top_k]


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """按来源和位置去重，避免同一个 chunk 重复进入上下文。

    重复上下文会浪费 token，也可能让模型过度相信同一段资料。
    """
    deduplicated = []
    seen = set()
    for result in results:
        key = (result.source_path, result.position)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(result)
    return deduplicated


def build_answer(question: str, results: list[SearchResult]) -> dict:
    """基于检索结果构造回答和引用。

    当前版本不调用真实 LLM，而是把相关资料摘要列出来。
    重点是保证 citations 字段完整，方便用户核对依据和研发排查问题。
    """
    if not results:
        # 没有资料时明确拒答，比编一个看起来合理的答案更符合生产质量要求。
        return {
            "question": question,
            "answer": "当前知识库没有检索到足够相关的资料，无法基于已有内容回答。",
            "citations": [],
            "retrieved_chunks": [],
        }

    answer_lines = [
        "基于当前知识库，相关资料主要来自以下片段：",
    ]
    for index, result in enumerate(results, start=1):
        answer_lines.append(
            f"[{index}] {compact_text(result.content, max_chars=180)}"
        )

    citations = [
        {
            "ref": index,
            "chunk_id": result.chunk_id,
            "doc_id": result.doc_id,
            "source_path": result.source_path,
            "title": result.title,
            "position": result.position,
            "score": result.score,
        }
        for index, result in enumerate(results, start=1)
    ]

    return {
        "question": question,
        "answer": "\n".join(answer_lines),
        "citations": citations,
        "retrieved_chunks": [
            {
                "chunk_id": result.chunk_id,
                "score": result.score,
                "preview": compact_text(result.content, max_chars=120),
            }
            for result in results
        ],
    }


def compact_text(text: str, max_chars: int) -> str:
    """压缩长文本，避免回答和调试输出过长。

    RAG 里进入 prompt 的上下文也需要类似控制，否则 token 成本和噪声都会增加。
    """
    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars].rstrip()}..."


def print_answer(payload: dict) -> None:
    """把回答和 citations 打印到控制台。

    控制台输出用于本地验证；真实 API 会把同样结构返回给前端或业务系统。
    """
    print("=== Day 18 RAG QA ===")
    print(f"question: {payload['question']}")
    print("\nanswer:")
    print(payload["answer"])

    print("\n引用来源:")
    if not payload["citations"]:
        print("- 无")
        return

    for citation in payload["citations"]:
        print(
            f"- [{citation['ref']}] {citation['source_path']} "
            f"position={citation['position']} "
            f"chunk_id={citation['chunk_id']} "
            f"score={citation['score']}"
        )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    支持自定义问题、top-k 和保存输出，方便用不同问题做回归测试。
    """
    parser = argparse.ArgumentParser(description="Day 18 RAG QA with citations")
    parser.add_argument(
        "--question",
        default="RAG 知识入库在生产环境里怎么设计？",
        help="要检索和回答的问题",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="返回最相关的 chunk 数量",
    )
    parser.add_argument(
        "--save-output",
        action="store_true",
        help="保存回答样例到 output/sample_answer.json",
    )
    return parser.parse_args()


def main() -> None:
    """运行一次完整在线问答流程，并按需保存样例输出。"""
    args = parse_args()
    results = load_search_results(question=args.question, top_k=args.top_k)
    payload = build_answer(question=args.question, results=results)
    print_answer(payload)

    if args.save_output:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\noutput: {OUTPUT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
