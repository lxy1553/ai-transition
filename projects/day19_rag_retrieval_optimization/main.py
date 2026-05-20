"""Day 19 - RAG 召回优化实验。

这个脚本用固定测试问题对比不同召回策略的命中效果。
重点不是让答案更好看，而是评估正确资料有没有进入 top-k，以及 query rewrite 是否提升召回。
"""

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "projects/day17_rag_ingestion/output/rag_index.sqlite"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
EVAL_PATH = OUTPUT_DIR / "retrieval_eval.json"
REPORT_PATH = OUTPUT_DIR / "retrieval_report.md"

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
    "检索",
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
    "json",
]

QUERY_EXPANSIONS = {
    "dt": "分区 where 全表扫描 风险",
    "分区": "dt where 全表扫描 风险",
    "引用": "citation 来源 可追溯 chunk",
    "入库": "文档 chunk embedding metadata 索引",
    "结构化": "json 字段 校验 枚举",
    "tool": "工具 调用 函数 参数",
}

TEST_CASES = [
    {
        "id": "tc_001",
        "question": "RAG 知识入库在生产环境里怎么设计？",
        "expected_sources": ["notes/day17_rag_ingestion.md"],
    },
    {
        "id": "tc_002",
        "question": "SQL 解释助手为什么要检查 dt 分区？",
        "expected_sources": [
            "notes/day12_sql_explainer_cli.md",
            "notes/day13_sql_explainer_enhancement.md",
        ],
    },
    {
        "id": "tc_003",
        "question": "RAG 问答为什么要返回引用来源？",
        "expected_sources": ["notes/day18_rag_retrieval_citations.md"],
    },
    {
        "id": "tc_004",
        "question": "结构化输出为什么要校验 JSON 字段？",
        "expected_sources": ["notes/terminology_glossary.md"],
    },
]

STRATEGIES = [
    {"name": "baseline_top3", "top_k": 3, "expand_query": False},
    {"name": "expanded_top3", "top_k": 3, "expand_query": True},
    {"name": "expanded_top5", "top_k": 5, "expand_query": True},
]


@dataclass
class ChunkRecord:
    """从知识库索引中读出的 chunk 记录。

    这里把正文、来源、位置和 embedding 放在一起，方便评测不同检索策略。
    """

    chunk_id: str
    source_path: str
    title: str
    content: str
    position: int
    embedding: list[float]


def embed_text(text: str) -> list[float]:
    """用本地词表生成查询向量。

    这里必须和 Day 17 入库时的 embedding 思路保持一致，
    否则 query 和 chunk 的相似度比较就不可靠。
    """
    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算查询和 chunk 的相似度分数。"""
    if not left or not right:
        return 0.0
    return min(sum(a * b for a, b in zip(left, right)), 1.0)


def expand_query(question: str) -> str:
    """用简单规则做 query rewrite。

    用户问题可能没有使用文档里的标准词。
    这里通过关键词扩展补充分区、引用、结构化等相关词，观察召回是否更容易命中正确资料。
    """
    additions = []
    lowered = question.lower()
    for keyword, expansion in QUERY_EXPANSIONS.items():
        if keyword.lower() in lowered:
            additions.append(expansion)
    if not additions:
        return question
    return f"{question} {' '.join(additions)}"


def load_chunks() -> list[ChunkRecord]:
    """从 Day 17 SQLite 索引加载可检索 chunk。

    召回评测依赖离线入库结果。
    如果索引不存在，应该先跑入库脚本，而不是让评测使用空数据。
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


def retrieve(question: str, chunks: list[ChunkRecord], top_k: int) -> list[dict]:
    """执行一次 top-k 检索，并返回适合写入评测报告的结果。

    返回 preview 是为了人工看 bad case 时不用打开原文也能快速判断是否相关。
    """
    query_embedding = embed_text(question)
    results = []
    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk.embedding)
        if score <= 0:
            continue
        results.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "position": chunk.position,
                "score": round(score, 6),
                "preview": compact_text(chunk.content, max_chars=100),
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def compact_text(text: str, max_chars: int) -> str:
    """压缩 chunk 正文，控制报告长度。"""
    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars].rstrip()}..."


def evaluate_case(test_case: dict, strategy: dict, chunks: list[ChunkRecord]) -> dict:
    """评估单个测试问题在某个策略下是否命中期望来源。

    hit_rank 能说明正确资料排在第几名。
    只知道命中还不够，如果正确资料排得太后，也可能进不了最终上下文。
    """
    query = test_case["question"]
    rewritten_query = expand_query(query) if strategy["expand_query"] else query
    results = retrieve(
        question=rewritten_query,
        chunks=chunks,
        top_k=strategy["top_k"],
    )
    expected_sources = set(test_case["expected_sources"])
    hit_rank = None
    for index, result in enumerate(results, start=1):
        if result["source_path"] in expected_sources:
            hit_rank = index
            break

    return {
        "case_id": test_case["id"],
        "question": query,
        "strategy": strategy["name"],
        "rewritten_query": rewritten_query,
        "expected_sources": test_case["expected_sources"],
        "hit": hit_rank is not None,
        "hit_rank": hit_rank,
        "results": results,
    }


def summarize(evaluations: list[dict]) -> list[dict]:
    """按策略汇总命中率和平均命中排名。

    这一步把单条 case 结果变成可比较的指标，方便判断哪种召回策略更稳。
    """
    summaries = []
    for strategy in STRATEGIES:
        items = [item for item in evaluations if item["strategy"] == strategy["name"]]
        hits = [item for item in items if item["hit"]]
        avg_rank = (
            sum(item["hit_rank"] for item in hits) / len(hits)
            if hits
            else None
        )
        summaries.append(
            {
                "strategy": strategy["name"],
                "case_count": len(items),
                "hit_count": len(hits),
                "hit_rate": round(len(hits) / len(items), 4) if items else 0,
                "avg_hit_rank": round(avg_rank, 2) if avg_rank else None,
            }
        )
    return summaries


def write_outputs(evaluations: list[dict], summary: list[dict]) -> None:
    """写出 JSON 明细和 Markdown 报告。

    JSON 方便程序继续处理，Markdown 方便人工复盘。
    两种产物都保留，后续优化策略时可以对比历史结果。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "evaluations": evaluations,
    }
    EVAL_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Day 19 - RAG 召回优化实验报告",
        "",
        "## 策略汇总",
        "",
        "| 策略 | 测试数 | 命中数 | 命中率 | 平均命中排名 |",
        "|------|--------|--------|--------|--------------|",
    ]
    for item in summary:
        lines.append(
            f"| {item['strategy']} | {item['case_count']} | {item['hit_count']} | "
            f"{item['hit_rate']} | {item['avg_hit_rank']} |"
        )

    lines.extend(["", "## Bad Case", ""])
    bad_cases = [item for item in evaluations if not item["hit"]]
    if not bad_cases:
        lines.append("- 本次实验没有未命中的 case。")
    else:
        for item in bad_cases:
            lines.append(
                f"- {item['case_id']} / {item['strategy']}：{item['question']}"
            )
            lines.append(f"  - rewritten_query: {item['rewritten_query']}")
            lines.append(f"  - expected: {', '.join(item['expected_sources'])}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """运行完整召回评测流程。

    顺序是：加载 chunk -> 对每个测试问题跑每种策略 -> 汇总指标 -> 写报告。
    """
    chunks = load_chunks()
    evaluations = [
        evaluate_case(test_case=test_case, strategy=strategy, chunks=chunks)
        for test_case in TEST_CASES
        for strategy in STRATEGIES
    ]
    summary = summarize(evaluations)
    write_outputs(evaluations=evaluations, summary=summary)

    print("=== Day 19 RAG Retrieval Optimization ===")
    for item in summary:
        print(
            f"{item['strategy']}: hit_rate={item['hit_rate']} "
            f"hit_count={item['hit_count']}/{item['case_count']} "
            f"avg_hit_rank={item['avg_hit_rank']}"
        )
    print(f"eval: {EVAL_PATH.relative_to(ROOT_DIR)}")
    print(f"report: {REPORT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
