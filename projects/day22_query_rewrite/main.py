"""Day 22 - Query Rewrite 召回实验。

这个脚本比较三种检索方式：
1. 原始问题直接检索。
2. 规则改写后检索。
3. 原始问题和多个改写 query 合并检索。

重点是看 query rewrite 是否让正确资料更容易进入 top-k。
真实生产里可以把这里的规则替换成 LLM rewrite，但仍然要保留评测和日志。
"""

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "projects/day17_rag_ingestion/output/rag_index.sqlite"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
EVAL_PATH = OUTPUT_DIR / "query_rewrite_eval.json"
REPORT_PATH = OUTPUT_DIR / "query_rewrite_report.md"

# 学习版词表要覆盖 Day 17 入库和 Day 22 改写会用到的关键词。
# 生产里这里会替换成真实 embedding 模型和关键词检索引擎。
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
    "检索",
    "citation",
    "citations",
    "api",
    "request_id",
    "confidence",
    "cannot_answer_reason",
    "bad case",
    "rerank",
]

REWRITE_RULES = {
    "资料怎么进系统": ["RAG 知识入库 文档 chunk embedding metadata 索引"],
    "带来源": ["RAG 引用来源 citations 可追溯 chunk_id"],
    "问不出来": ["RAG 召回质量差 bad case top-k query rewrite rerank"],
    "接口怎么设计": ["RAG 问答 API request_id citations confidence cannot_answer_reason"],
    "dt": ["SQL 风险 dt 分区 where 全表扫描"],
    "结构化": ["结构化输出 json 字段 校验"],
}

TEST_CASES = [
    {
        "id": "qr_001",
        "question": "资料怎么进系统？",
        "expected_sources": ["notes/day17_rag_ingestion.md"],
    },
    {
        "id": "qr_002",
        "question": "RAG 为什么要带来源？",
        "expected_sources": ["notes/day18_rag_retrieval_citations.md"],
    },
    {
        "id": "qr_003",
        "question": "问不出来的时候怎么排查？",
        "expected_sources": ["notes/day19_rag_retrieval_optimization.md"],
    },
    {
        "id": "qr_004",
        "question": "这个接口怎么设计才适合生产？",
        "expected_sources": ["notes/day20_rag_api.md"],
    },
]

STRATEGIES = [
    {"name": "original_top3", "top_k": 3, "mode": "original"},
    {"name": "rewritten_top3", "top_k": 3, "mode": "rewritten"},
    {"name": "multi_query_top3", "top_k": 3, "mode": "multi_query"},
]


@dataclass
class ChunkRecord:
    """知识库中的一个 chunk。

    query rewrite 实验只关心 chunk 的来源、正文和 embedding，
    因为这些字段足够判断是否命中预期资料。
    """

    chunk_id: str
    source_path: str
    title: str
    content: str
    position: int
    embedding: list[float]


def embed_text(text: str) -> list[float]:
    """把 query 转成学习版向量。

    入库和查询必须使用同一种向量方式，否则相似度比较没有意义。
    """

    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算 query 和 chunk 的相似度。"""

    if not left or not right:
        return 0.0
    return min(sum(a * b for a, b in zip(left, right)), 1.0)


def compact_text(text: str, max_chars: int) -> str:
    """压缩正文，避免评测报告太长。"""

    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars].rstrip()}..."


def rewrite_query(question: str) -> list[str]:
    """按规则生成改写 query。

    这里故意使用可解释规则，方便观察改写前后到底加了哪些词。
    生产里即使用 LLM rewrite，也应该输出可记录、可回放的 rewritten query。
    """

    rewritten = []
    lowered = question.lower()
    for keyword, expansions in REWRITE_RULES.items():
        if keyword.lower() in lowered:
            rewritten.extend(expansions)
    if rewritten:
        return [f"{question} {item}" for item in rewritten]
    return [question]


def build_queries(question: str, mode: str) -> list[str]:
    """根据策略构造本次检索要使用的 query 列表。"""

    rewritten = rewrite_query(question)
    if mode == "original":
        return [question]
    if mode == "rewritten":
        return rewritten
    if mode == "multi_query":
        return [question, *rewritten]
    raise ValueError(f"unknown mode: {mode}")


def load_chunks() -> list[ChunkRecord]:
    """从 Day 17 索引加载 active chunk。

    如果索引不存在，说明离线入库还没跑，实验不应该继续。
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Day 17 索引不存在，请先运行：python3 projects/day17_rag_ingestion/main.py"
        )

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            select
                c.chunk_id,
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

    return [
        ChunkRecord(
            chunk_id=row[0],
            source_path=row[1],
            title=row[2],
            content=row[3],
            position=row[4],
            embedding=json.loads(row[5]),
        )
        for row in rows
    ]


def retrieve(queries: list[str], chunks: list[ChunkRecord], top_k: int) -> list[dict]:
    """执行检索并合并多 query 结果。

    同一个 chunk 可能被多个 query 命中。这里保留最高分和命中的 query，
    方便判断 multi-query 是否真的带来增益。
    """

    by_chunk: dict[str, dict] = {}
    for query in queries:
        query_embedding = embed_text(query)
        for chunk in chunks:
            score = cosine_similarity(query_embedding, chunk.embedding)
            if score <= 0:
                continue
            existing = by_chunk.get(chunk.chunk_id)
            if existing and existing["score"] >= score:
                continue
            by_chunk[chunk.chunk_id] = {
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "position": chunk.position,
                "score": round(score, 6),
                "matched_query": query,
                "preview": compact_text(chunk.content, max_chars=100),
            }

    results = list(by_chunk.values())
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def evaluate_case(test_case: dict, strategy: dict, chunks: list[ChunkRecord]) -> dict:
    """评估单个问题在单个策略下是否命中预期来源。"""

    queries = build_queries(test_case["question"], strategy["mode"])
    results = retrieve(queries=queries, chunks=chunks, top_k=strategy["top_k"])
    expected_sources = set(test_case["expected_sources"])

    hit_rank = None
    for index, result in enumerate(results, start=1):
        if result["source_path"] in expected_sources:
            hit_rank = index
            break

    return {
        "case_id": test_case["id"],
        "question": test_case["question"],
        "strategy": strategy["name"],
        "queries": queries,
        "expected_sources": test_case["expected_sources"],
        "hit": hit_rank is not None,
        "hit_rank": hit_rank,
        "results": results,
    }


def summarize(evaluations: list[dict]) -> list[dict]:
    """按策略汇总命中率和平均命中排名。"""

    summaries = []
    for strategy in STRATEGIES:
        items = [item for item in evaluations if item["strategy"] == strategy["name"]]
        hits = [item for item in items if item["hit"]]
        avg_rank = (
            round(sum(item["hit_rank"] for item in hits) / len(hits), 2)
            if hits
            else None
        )
        summaries.append(
            {
                "strategy": strategy["name"],
                "total": len(items),
                "hits": len(hits),
                "hit_rate": round(len(hits) / len(items), 4) if items else 0,
                "avg_hit_rank": avg_rank,
            }
        )
    return summaries


def build_report(summaries: list[dict], evaluations: list[dict]) -> str:
    """生成 Markdown 实验报告。"""

    lines = [
        "# Day 22 - Query Rewrite 实验报告",
        "",
        "## 策略汇总",
        "",
        "| 策略 | 测试数 | 命中数 | 命中率 | 平均命中排名 |",
        "|------|--------|--------|--------|--------------|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['strategy']} | {item['total']} | {item['hits']} | "
            f"{item['hit_rate']:.2f} | {item['avg_hit_rank']} |"
        )

    lines.extend(["", "## 改写样例", ""])
    for item in evaluations:
        if item["strategy"] != "rewritten_top3":
            continue
        lines.append(f"- {item['case_id']}：{item['question']}")
        for query in item["queries"]:
            lines.append(f"  - query: {query}")

    bad_cases = [item for item in evaluations if not item["hit"]]
    lines.extend(["", "## Bad Case", ""])
    if not bad_cases:
        lines.append("- 暂无未命中样例。")
    else:
        for item in bad_cases:
            lines.append(f"- {item['case_id']} / {item['strategy']}：{item['question']}")
            lines.append(f"  - expected: {', '.join(item['expected_sources'])}")
            lines.append(f"  - queries: {' | '.join(item['queries'])}")

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "query rewrite 的价值要通过固定测试集验证。",
            "如果改写提升命中但引入噪声，后续要结合 rerank 和更严格的改写规则。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """运行 Day 22 query rewrite 实验并保存结果。"""

    chunks = load_chunks()
    evaluations = [
        evaluate_case(test_case=test_case, strategy=strategy, chunks=chunks)
        for test_case in TEST_CASES
        for strategy in STRATEGIES
    ]
    summaries = summarize(evaluations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_PATH.write_text(
        json.dumps(
            {"summaries": summaries, "evaluations": evaluations},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(summaries, evaluations), encoding="utf-8")

    print("=== Day 22 Query Rewrite Evaluation ===")
    for item in summaries:
        print(
            f"{item['strategy']} | hit_rate={item['hit_rate']:.2f} "
            f"| avg_rank={item['avg_hit_rank']}"
        )
    print(f"output: {EVAL_PATH.relative_to(ROOT_DIR)}")
    print(f"report: {REPORT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
