"""Day 17 - RAG 离线入库脚本。

这个脚本负责把学习笔记和项目文档整理成可检索的本地知识库：
读取 Markdown、清洗文本、切成 chunk、生成简化 embedding、写入 SQLite 索引。
它对应生产 RAG 的离线链路，在线问答只应该使用已经入库和建好索引的资料。
"""

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
DB_PATH = OUTPUT_DIR / "rag_index.sqlite"
MANIFEST_PATH = OUTPUT_DIR / "ingestion_manifest.json"

# 本次要入库的知识文件清单，生产里通常来自文档平台、Git、数据字典或对象存储。
SOURCE_FILES = [
    "notes/day12_sql_explainer_cli.md",
    "notes/day13_sql_explainer_enhancement.md",
    "notes/day15_rag_preparation.md",
    "notes/day16_rag_basics.md",
    "notes/day17_rag_ingestion.md",
    "notes/day18_rag_retrieval_citations.md",
    "notes/day19_rag_retrieval_optimization.md",
    "notes/day20_rag_api.md",
    "notes/day21_rag_project_review.md",
    "notes/day22_query_rewrite.md",
    "notes/day23_rag_eval_testset.md",
    "notes/day24_hallucination_guardrails.md",
    "notes/day25_security_controls.md",
    "docs/day25_security_control_checklist.md",
    "notes/day26_rag_performance_cost.md",
    "notes/day27_rag_demo_stability.md",
    "notes/day28_week4_review_application.md",
    "docs/day28_application_tracking.md",
    "notes/day29_nl2sql_schema_preparation.md",
    "docs/day29_nl2sql_schema_scenarios.md",
    "notes/terminology_glossary.md",
]

# 学习版 embedding 词表：用关键词计数模拟文本向量，生产里会替换成真实 embedding 模型。
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
    "幻觉",
    "边界",
    "澄清",
    "敏感",
    "guardrail",
    "grounded",
    "insufficient",
    "脱敏",
    "安全",
    "审计",
    "角色",
    "allow",
    "deny",
    "mask",
    "pii",
    "缓存",
    "成本",
    "上下文",
    "演示",
    "稳定性",
    "投递",
    "简历",
    "试投",
    "面试",
    "nl2sql",
    "schema",
    "catalog",
    "表结构",
    "指标",
    "维度",
    "粒度",
    "候选表",
    "问题类型",
]


@dataclass
class SourceDocument:
    """原始文档对象，对应 RAG 入库链路里的 document 级元数据。"""

    doc_id: str
    path: str
    title: str
    content: str
    content_hash: str


@dataclass
class Chunk:
    """文档切分后的知识片段，对应后续检索和引用的最小单元。"""

    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    text: str
    position: int


def sha256_text(text: str) -> str:
    """生成文本指纹，用于构造稳定的 doc_id、chunk_id 和 run_id。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_source_document(relative_path: str) -> SourceDocument:
    """读取单个源文件，并提取标题、内容 hash 和文档 ID。"""
    path = ROOT_DIR / relative_path
    content = path.read_text(encoding="utf-8")
    title = extract_title(content=content, fallback=path.stem)
    content_hash = sha256_text(content)
    doc_id = f"doc_{content_hash[:12]}"
    return SourceDocument(
        doc_id=doc_id,
        path=relative_path,
        title=title,
        content=content,
        content_hash=content_hash,
    )


def extract_title(content: str, fallback: str) -> str:
    """优先使用 Markdown 一级标题作为文档标题，找不到则回退到文件名。"""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return fallback


def normalize_text(text: str) -> str:
    """清洗 Markdown 文本：去掉空行和代码块，保留适合检索的正文。"""
    lines = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines)


def split_into_chunks(document: SourceDocument, max_chars: int = 520) -> list[Chunk]:
    """按标题和长度把文档切成 chunk，并保留来源与位置，方便后续引用。"""
    normalized = normalize_text(document.content)
    sections = re.split(r"\n(?=#{1,3}\s)", normalized)
    chunks: list[Chunk] = []
    position = 1

    for section in sections:
        section = section.strip()
        if not section:
            continue
        for text in split_long_text(section, max_chars=max_chars):
            chunk_hash = sha256_text(f"{document.doc_id}:{position}:{text}")
            chunks.append(
                Chunk(
                    chunk_id=f"chunk_{chunk_hash[:12]}",
                    doc_id=document.doc_id,
                    source_path=document.path,
                    title=document.title,
                    text=text,
                    position=position,
                )
            )
            position += 1
    return chunks


def split_long_text(text: str, max_chars: int) -> list[str]:
    """当某个标题段落太长时，再按句子边界二次切分。"""
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[。！？；.!?])", text)
    chunks = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) <= max_chars:
            current = f"{current}{sentence}"
            continue
        if current:
            chunks.append(current)
        current = sentence
    if current:
        chunks.append(current)
    return chunks


def embed_text(text: str) -> list[float]:
    """用关键词出现次数生成简化向量，模拟真实 embedding。"""
    lowered = text.lower()
    vector = [float(lowered.count(word.lower())) for word in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def init_database(connection: sqlite3.Connection) -> None:
    """初始化本地 SQLite 表结构，模拟文档库、chunk 库、向量库和入库任务表。"""
    connection.executescript(
        """
        create table if not exists documents (
            doc_id text primary key,
            source_path text not null,
            title text not null,
            content_hash text not null,
            status text not null,
            created_at text not null
        );

        create table if not exists chunks (
            chunk_id text primary key,
            doc_id text not null,
            source_path text not null,
            title text not null,
            content text not null,
            position integer not null,
            metadata_json text not null,
            created_at text not null,
            foreign key (doc_id) references documents(doc_id)
        );

        create table if not exists embeddings (
            chunk_id text primary key,
            embedding_json text not null,
            embedding_model text not null,
            created_at text not null,
            foreign key (chunk_id) references chunks(chunk_id)
        );

        create table if not exists ingestion_runs (
            run_id text primary key,
            document_count integer not null,
            chunk_count integer not null,
            created_at text not null
        );
        """
    )


def reset_database(connection: sqlite3.Connection) -> None:
    """清空旧索引数据；当前 Demo 每次全量重建，生产里通常做增量更新。"""
    connection.executescript(
        """
        delete from embeddings;
        delete from chunks;
        delete from documents;
        delete from ingestion_runs;
        """
    )


def save_index(
    connection: sqlite3.Connection,
    documents: list[SourceDocument],
    chunks: list[Chunk],
    run_id: str,
    created_at: str,
) -> None:
    """把 documents、chunks、embeddings 和本次入库任务写入 SQLite。"""
    for document in documents:
        connection.execute(
            """
            insert into documents (
                doc_id, source_path, title, content_hash, status, created_at
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                document.doc_id,
                document.path,
                document.title,
                document.content_hash,
                "active",
                created_at,
            ),
        )

    for chunk in chunks:
        # metadata 用于在线检索时做来源追溯、业务域过滤、权限过滤和状态过滤。
        metadata = {
            "source_path": chunk.source_path,
            "title": chunk.title,
            "business_domain": "ai_transition",
            "permission": "local_learning",
            "status": "active",
        }
        connection.execute(
            """
            insert into chunks (
                chunk_id, doc_id, source_path, title, content, position,
                metadata_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.source_path,
                chunk.title,
                chunk.text,
                chunk.position,
                json.dumps(metadata, ensure_ascii=False),
                created_at,
            ),
        )
        # 每个 chunk 都生成一条 embedding，在线问答时用它做相似度检索。
        connection.execute(
            """
            insert into embeddings (
                chunk_id, embedding_json, embedding_model, created_at
            ) values (?, ?, ?, ?)
            """,
            (
                chunk.chunk_id,
                json.dumps(embed_text(chunk.text), ensure_ascii=False),
                "local_keyword_embedding_v1",
                created_at,
            ),
        )

    connection.execute(
        """
        insert into ingestion_runs (
            run_id, document_count, chunk_count, created_at
        ) values (?, ?, ?, ?)
        """,
        (run_id, len(documents), len(chunks), created_at),
    )


def write_manifest(
    documents: list[SourceDocument],
    chunks: list[Chunk],
    run_id: str,
    created_at: str,
) -> None:
    """写出本次入库摘要，方便检查入库了哪些文档、生成多少 chunk。"""
    manifest = {
        "run_id": run_id,
        "created_at": created_at,
        "database_path": str(DB_PATH.relative_to(ROOT_DIR)),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedding_model": "local_keyword_embedding_v1",
        "documents": [
            {
                "doc_id": document.doc_id,
                "source_path": document.path,
                "title": document.title,
                "content_hash": document.content_hash,
            }
            for document in documents
        ],
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    """编排完整离线入库流程：读取、切分、向量化、写库、输出摘要。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    run_id = f"run_{sha256_text(created_at)[:12]}"

    # 1. 文档接入：读取清单里的 Markdown 文件。
    documents = [read_source_document(path) for path in SOURCE_FILES]

    # 2. 文档切分：把每篇文档切成可检索、可引用的 chunk。
    chunks = [
        chunk
        for document in documents
        for chunk in split_into_chunks(document=document)
    ]

    # 3. 索引构建：把文档、chunk、embedding 和任务记录写入 SQLite。
    with sqlite3.connect(DB_PATH) as connection:
        init_database(connection)
        reset_database(connection)
        save_index(
            connection=connection,
            documents=documents,
            chunks=chunks,
            run_id=run_id,
            created_at=created_at,
        )

    # 4. 任务审计：输出 manifest，记录本次入库摘要。
    write_manifest(
        documents=documents,
        chunks=chunks,
        run_id=run_id,
        created_at=created_at,
    )

    # 5. 控制台输出：便于本地确认入库规模和样例 chunk。
    print("=== Day 17 RAG Ingestion ===")
    print(f"run_id: {run_id}")
    print(f"documents: {len(documents)}")
    print(f"chunks: {len(chunks)}")
    print(f"database: {DB_PATH.relative_to(ROOT_DIR)}")
    print(f"manifest: {MANIFEST_PATH.relative_to(ROOT_DIR)}")
    print("\n=== Sample Chunks ===")
    for chunk in chunks[:5]:
        preview = chunk.text.replace("\n", " ")[:90]
        print(f"{chunk.chunk_id} | {chunk.source_path} | {preview}")


if __name__ == "__main__":
    main()
