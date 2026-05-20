"""Day 23 - RAG 测试集评估脚本。

这个脚本读取 20 条固定测试样本，检查 expected source 是否进入 top-k。
它的目标不是自动判断最终答案好不好，而是先把 RAG 最关键的检索层评估做稳定。
生产里通常会在这个基础上继续增加答案正确率、引用准确率、拒答准确率和人工评分。
"""

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "projects/day17_rag_ingestion/output/rag_index.sqlite"
TESTSET_PATH = Path(__file__).resolve().parent / "testset.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
RESULT_PATH = OUTPUT_DIR / "rag_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "rag_eval_report.md"

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
    "测试集",
    "评测",
    "expected",
    "source",
    "hit",
    "拒答",
]


@dataclass
class ChunkRecord:
    """知识库中的 chunk 记录。

    评测只需要知道 chunk 来源、位置、正文和向量，就能判断 expected source 是否命中。
    """

    chunk_id: str
    source_path: str
    title: str
    content: str
    position: int
    embedding: list[float]


def embed_text(text: str) -> list[float]:
    """用学习版词表生成 query 向量。

    这里保持和 Day 17 入库词表同序，避免相似度计算失真。
    """

    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算 query 和 chunk 的余弦相似度。"""

    if not left or not right:
        return 0.0
    return min(sum(a * b for a, b in zip(left, right)), 1.0)


def compact_text(text: str, max_chars: int = 90) -> str:
    """压缩长文本，方便写入报告。"""

    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars].rstrip()}..."


def load_testset() -> list[dict]:
    """加载固定测试集。"""

    return json.loads(TESTSET_PATH.read_text(encoding="utf-8"))


def load_chunks() -> list[ChunkRecord]:
    """从 Day 17 SQLite 索引加载 active chunk。"""

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


def retrieve(question: str, chunks: list[ChunkRecord], top_k: int = 5) -> list[dict]:
    """执行一次 top-k 检索。"""

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
                "preview": compact_text(chunk.content),
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def evaluate_sample(sample: dict, chunks: list[ChunkRecord], top_k: int = 5) -> dict:
    """评估单条样本。

    should_answer=false 的样本用于记录边界问题。第一版只检查它是否仍然召回了内容，
    后续接拒答策略时再加入更严格的拒答准确率。
    """

    results = retrieve(sample["question"], chunks, top_k=top_k)
    expected_sources = set(sample["expected_sources"])
    hit_rank = None
    if expected_sources:
        for index, result in enumerate(results, start=1):
            if result["source_path"] in expected_sources:
                hit_rank = index
                break

    return {
        "id": sample["id"],
        "question": sample["question"],
        "question_type": sample["question_type"],
        "should_answer": sample["should_answer"],
        "expected_sources": sample["expected_sources"],
        "hit": hit_rank is not None if sample["should_answer"] else None,
        "hit_rank": hit_rank,
        "retrieved_count": len(results),
        "top_results": results,
        "risk_tags": sample["risk_tags"],
    }


def summarize(evaluations: list[dict]) -> dict:
    """汇总评测指标。"""

    answerable = [item for item in evaluations if item["should_answer"]]
    hits = [item for item in answerable if item["hit"]]
    avg_rank = (
        round(sum(item["hit_rank"] for item in hits) / len(hits), 2)
        if hits
        else None
    )
    return {
        "total": len(evaluations),
        "answerable_total": len(answerable),
        "cannot_answer_cases": len([item for item in evaluations if not item["should_answer"]]),
        "hits": len(hits),
        "hit_rate": round(len(hits) / len(answerable), 4) if answerable else 0,
        "avg_hit_rank": avg_rank,
        "bad_cases": [item for item in answerable if not item["hit"]],
    }


def build_report(summary: dict, evaluations: list[dict]) -> str:
    """生成 Markdown 评测报告。"""

    lines = [
        "# Day 23 - RAG 测试集评测报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- answerable_total: {summary['answerable_total']}",
        f"- cannot_answer_cases: {summary['cannot_answer_cases']}",
        f"- hits: {summary['hits']}",
        f"- hit_rate: {summary['hit_rate']:.2f}",
        f"- avg_hit_rank: {summary['avg_hit_rank']}",
        "",
        "## 样本结果",
        "",
        "| id | type | should_answer | hit | hit_rank | question |",
        "|----|------|---------------|-----|----------|----------|",
    ]
    for item in evaluations:
        lines.append(
            f"| {item['id']} | {item['question_type']} | {item['should_answer']} | "
            f"{item['hit']} | {item['hit_rank']} | {item['question']} |"
        )

    lines.extend(["", "## Bad Case", ""])
    if not summary["bad_cases"]:
        lines.append("- 暂无未命中样本。")
    else:
        for item in summary["bad_cases"]:
            top_sources = [result["source_path"] for result in item["top_results"][:3]]
            lines.append(f"- {item['id']}：{item['question']}")
            lines.append(f"  - expected: {', '.join(item['expected_sources'])}")
            lines.append(f"  - top_sources: {', '.join(top_sources)}")

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 对 bad case 补充 query rewrite、关键词和 chunk 策略。",
            "- 增加引用准确率、拒答准确率和答案正确率评估。",
            "- 把测试集分成核心回归集和扩展问题集。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """运行 Day 23 RAG 测试集评估。"""

    testset = load_testset()
    chunks = load_chunks()
    evaluations = [evaluate_sample(sample, chunks) for sample in testset]
    summary = summarize(evaluations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps({"summary": summary, "evaluations": evaluations}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(summary, evaluations), encoding="utf-8")

    print("=== Day 23 RAG Evaluation Set ===")
    print(f"total={summary['total']} answerable={summary['answerable_total']}")
    print(f"hit_rate={summary['hit_rate']:.2f} avg_hit_rank={summary['avg_hit_rank']}")
    print(f"output: {RESULT_PATH.relative_to(ROOT_DIR)}")
    print(f"report: {REPORT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
