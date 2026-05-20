"""Day 20 - RAG 问答 API。

这个文件把 Day 18 的本地 RAG 问答脚本封装成 FastAPI 服务。
用途是让 RAG 能力不只在命令行里跑，而是可以被前端、机器人或其他业务系统通过 HTTP 调用。
第一版只做最小闭环：输入问题，检索 Day 17 索引，返回答案、引用和排查字段。
"""

import json
import math
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "projects/day17_rag_ingestion/output/rag_index.sqlite"

# 学习版词表必须和 Day 17 入库时保持一致。
# 真实生产里这里会替换成同一个 embedding 模型，而不是手写关键词词表。
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


class AskRequest(BaseModel):
    """RAG 问答接口的请求体。

    请求体不只包含 question，还预留 user_id 和 business_domain。
    这两个字段当前只返回和记录，后续可以接权限过滤、业务域过滤和审计日志。
    """

    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    top_k: int = Field(3, ge=1, le=8, description="返回最相关的 chunk 数量")
    user_id: Optional[str] = Field(None, max_length=80, description="用户标识，用于后续审计和权限")
    business_domain: Optional[str] = Field(None, max_length=80, description="业务域，用于后续过滤")


class Citation(BaseModel):
    """答案引用来源。

    citations 是 RAG API 和普通问答 API 的关键区别。
    它让用户能核对答案依据，也让研发能排查是检索错、资料错还是生成错。
    """

    ref: int
    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    position: int
    score: float


class RetrievedChunk(BaseModel):
    """返回给研发排查用的召回摘要。

    生产接口不一定把 retrieved_chunks 全量暴露给普通用户，
    但学习阶段保留它能帮助理解 top-k 到底召回了什么。
    """

    chunk_id: str
    score: float
    preview: str


class AskResponse(BaseModel):
    """RAG 问答接口响应体。

    响应里同时返回答案、引用、置信度和 request_id。
    这样接口不仅能给用户展示，也能用于日志排查和回归测试。
    """

    request_id: str
    question: str
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    confidence: float
    cannot_answer_reason: Optional[str]
    latency_ms: int


@dataclass
class SearchResult:
    """一次在线检索命中的 chunk。

    这里保留正文、来源、位置和分数。
    后续构造答案和 citations 都依赖这些字段。
    """

    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    content: str
    position: int
    score: float


app = FastAPI(
    title="Day 20 RAG API",
    description="把本地 RAG 检索问答能力封装成 HTTP API",
    version="1.0.0",
)


def embed_text(text: str) -> list[float]:
    """把文本转成学习版向量。

    这里用关键词出现次数模拟 embedding，是为了本地可运行、可解释。
    真实 RAG 会调用 embedding 模型，并保证入库和查询使用同一模型。
    """

    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算问题向量和 chunk 向量的相似度。

    分数越高，说明当前词表下越相关。
    如果向量为空，说明没有可比较的信息，直接返回 0。
    """

    if not left or not right:
        return 0.0
    return min(sum(a * b for a, b in zip(left, right)), 1.0)


def compact_text(text: str, max_chars: int) -> str:
    """压缩长文本，避免 API 响应过长。

    RAG API 需要控制返回体大小。
    真实生产里还会控制进入 prompt 的上下文长度，避免 token 成本过高。
    """

    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars].rstrip()}..."


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """按来源和位置去重。

    同一段资料重复进入上下文会浪费 token，也会让答案看起来依据很多但其实来源单一。
    """

    deduplicated: list[SearchResult] = []
    seen = set()
    for result in results:
        key = (result.source_path, result.position)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(result)
    return deduplicated


def load_search_results(question: str, top_k: int) -> list[SearchResult]:
    """从 Day 17 SQLite 索引里检索 top-k chunk。

    这是 API 背后的核心 RAG 检索步骤。
    如果索引不存在，说明离线入库链路还没跑，API 应该明确报错而不是返回空答案。
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Day 17 索引不存在，请先运行：python3 projects/day17_rag_ingestion/main.py"
        )

    question_embedding = embed_text(question)
    results: list[SearchResult] = []

    # 只检索 active chunk，模拟生产里过滤掉废弃、下线或无效资料。
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


def build_response(request: AskRequest, request_id: str, started_at: float) -> AskResponse:
    """把检索结果转换成稳定 API 响应。

    这个函数是接口层和检索层之间的组装层：
    检索层只关心 chunk，API 层需要 answer、citations、confidence、latency 等字段。
    """

    results = load_search_results(question=request.question, top_k=request.top_k)
    latency_ms = int((time.time() - started_at) * 1000)

    if not results:
        return AskResponse(
            request_id=request_id,
            question=request.question,
            answer="当前知识库没有检索到足够相关的资料，无法基于已有内容回答。",
            citations=[],
            retrieved_chunks=[],
            confidence=0.0,
            cannot_answer_reason="no_relevant_chunks",
            latency_ms=latency_ms,
        )

    answer_lines = ["基于当前知识库，相关资料主要来自以下片段："]
    for index, result in enumerate(results, start=1):
        answer_lines.append(f"[{index}] {compact_text(result.content, max_chars=180)}")

    citations = [
        Citation(
            ref=index,
            chunk_id=result.chunk_id,
            doc_id=result.doc_id,
            source_path=result.source_path,
            title=result.title,
            position=result.position,
            score=result.score,
        )
        for index, result in enumerate(results, start=1)
    ]

    retrieved_chunks = [
        RetrievedChunk(
            chunk_id=result.chunk_id,
            score=result.score,
            preview=compact_text(result.content, max_chars=120),
        )
        for result in results
    ]

    return AskResponse(
        request_id=request_id,
        question=request.question,
        answer="\n".join(answer_lines),
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        confidence=max(result.score for result in results),
        cannot_answer_reason=None,
        latency_ms=latency_ms,
    )


@app.get("/health")
def health() -> dict:
    """健康检查接口。

    用来确认 API 进程是否正常，并顺手暴露 Day 17 索引是否存在。
    真实生产里监控系统会定期请求 health 接口。
    """

    return {
        "status": "ok",
        "service": "day20-rag-api",
        "index_ready": DB_PATH.exists(),
        "index_path": str(DB_PATH.relative_to(ROOT_DIR)),
    }


@app.post("/rag/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """RAG 问答接口。

    外部系统只需要传 question，就能拿到答案和 citations。
    request_id 每次请求都生成一个，方便以后把用户反馈和服务日志串起来。
    """

    request_id = f"req_{uuid4().hex[:12]}"
    started_at = time.time()

    try:
        return build_response(request=request, request_id=request_id, started_at=started_at)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        # 数据库异常属于服务端问题，不能把底层堆栈直接暴露给用户。
        raise HTTPException(status_code=500, detail=f"知识库索引读取失败: {exc}") from exc
