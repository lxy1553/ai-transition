"""金融信贷数仓 RAG 助手。

这个脚本实现一个本地可运行的生产级 RAG 雏形：
离线入库、chunk 切分、权限过滤、敏感问题拒答、引用来源、审计日志和评测回归。
它故意不依赖外部模型服务，方便在面试或作品集里稳定演示工程链路。
"""

import argparse
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
CONFIG_PATH = PROJECT_DIR / "config" / "access_policy.json"
WAREHOUSE_PATH = PROJECT_DIR / "warehouse" / "warehouse_catalog.json"
EVAL_PATH = PROJECT_DIR / "eval" / "eval_cases.json"
OUTPUT_DIR = PROJECT_DIR / "output"
DB_PATH = OUTPUT_DIR / "rag_index.sqlite"
DEMO_PATH = OUTPUT_DIR / "demo_answers.json"
EVAL_RESULT_PATH = OUTPUT_DIR / "eval_results.json"
EVAL_REPORT_PATH = OUTPUT_DIR / "evaluation_report.md"
AUDIT_LOG_PATH = OUTPUT_DIR / "audit_log.jsonl"


BUSINESS_TERMS = [
    "授信",
    "通过率",
    "额度",
    "审批",
    "风控",
    "反欺诈",
    "规则",
    "命中",
    "拒绝",
    "人工复核",
    "放款",
    "还款",
    "逾期",
    "贷后",
    "催收",
    "dpd",
    "m1",
    "m2",
    "bucket",
    "手机号",
    "身份证",
    "银行卡",
    "客户名单",
    "权限",
    "审计",
    "合规",
    "分区",
    "dt",
    "dwd",
    "dws",
    "ads",
    "approval_rate",
    "overdue_rate",
]


@dataclass
class Document:
    """入库文档，代表生产 RAG 里的 document 级元数据。"""

    doc_id: str
    title: str
    domain: str
    security_level: str
    allowed_roles: list[str]
    warehouse_tables: list[str]
    source_path: str
    content: str


@dataclass
class Chunk:
    """文档切分后的最小检索单元。"""

    chunk_id: str
    doc_id: str
    title: str
    domain: str
    security_level: str
    allowed_roles: list[str]
    warehouse_tables: list[str]
    source_path: str
    position: int
    text: str


def sha256_text(text: str) -> str:
    """生成稳定指纹，用于构造 doc_id、chunk_id 和 request_id。"""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    """读取 JSON 配置，避免把权限和评测样例写死在代码里。"""

    return json.loads(path.read_text(encoding="utf-8"))


def parse_metadata_document(path: Path) -> Document:
    """解析带简化 front matter 的 Markdown 文档。"""

    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, metadata_block, body = raw.split("---", 2)
        for line in metadata_block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    allowed_roles = split_csv(metadata.get("allowed_roles", "admin"))
    warehouse_tables = split_csv(metadata.get("warehouse_tables", ""))
    doc_id = metadata.get("doc_id") or path.stem
    title = metadata.get("title") or extract_title(body, fallback=path.stem)
    return Document(
        doc_id=doc_id,
        title=title,
        domain=metadata.get("domain", "general"),
        security_level=metadata.get("security_level", "internal"),
        allowed_roles=allowed_roles,
        warehouse_tables=warehouse_tables,
        source_path=str(path.relative_to(PROJECT_DIR)),
        content=body.strip(),
    )


def split_csv(value: str) -> list[str]:
    """解析 metadata 中的逗号列表。"""

    return [item.strip() for item in value.split(",") if item.strip()]


def extract_title(text: str, fallback: str) -> str:
    """优先使用 Markdown 一级标题作为标题。"""

    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return fallback


def normalize_text(text: str) -> str:
    """清洗 Markdown 正文，保留适合检索和引用的文字。"""

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        lines.append(stripped)
    return "\n".join(lines)


def split_into_chunks(document: Document, max_chars: int = 620) -> list[Chunk]:
    """按标题和长度切分文档，并把权限 metadata 复制到 chunk。"""

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
                    title=document.title,
                    domain=document.domain,
                    security_level=document.security_level,
                    allowed_roles=document.allowed_roles,
                    warehouse_tables=document.warehouse_tables,
                    source_path=document.source_path,
                    position=position,
                    text=text,
                )
            )
            position += 1
    return chunks


def split_long_text(text: str, max_chars: int) -> list[str]:
    """长段落按自然句子二次切分，避免 chunk 太大。"""

    if len(text) <= max_chars:
        return [text]

    parts = re.split(r"(?<=[。！？；.!?])", text)
    chunks = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
            continue
        if current:
            chunks.append(current)
        current = part
    if current:
        chunks.append(current)
    return chunks


def connect_db() -> sqlite3.Connection:
    """连接本地 SQLite 索引。生产里可以替换成检索引擎或向量库。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def rebuild_index() -> dict[str, int]:
    """重建离线索引，把知识文档和数仓目录写入 SQLite。"""

    documents = [parse_metadata_document(path) for path in sorted(KNOWLEDGE_DIR.glob("*.md"))]
    chunks = [chunk for document in documents for chunk in split_into_chunks(document)]

    with connect_db() as conn:
        conn.executescript(
            """
            drop table if exists documents;
            drop table if exists chunks;
            create table documents (
                doc_id text primary key,
                title text,
                domain text,
                security_level text,
                allowed_roles_json text,
                warehouse_tables_json text,
                source_path text,
                content_hash text
            );
            create table chunks (
                chunk_id text primary key,
                doc_id text,
                title text,
                domain text,
                security_level text,
                allowed_roles_json text,
                warehouse_tables_json text,
                source_path text,
                position integer,
                text text,
                token_text text
            );
            """
        )
        for document in documents:
            conn.execute(
                """
                insert into documents values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.doc_id,
                    document.title,
                    document.domain,
                    document.security_level,
                    json.dumps(document.allowed_roles, ensure_ascii=False),
                    json.dumps(document.warehouse_tables, ensure_ascii=False),
                    document.source_path,
                    sha256_text(document.content),
                ),
            )
        for chunk in chunks:
            conn.execute(
                """
                insert into chunks values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.title,
                    chunk.domain,
                    chunk.security_level,
                    json.dumps(chunk.allowed_roles, ensure_ascii=False),
                    json.dumps(chunk.warehouse_tables, ensure_ascii=False),
                    chunk.source_path,
                    chunk.position,
                    chunk.text,
                    " ".join(tokenize(chunk.text + " " + " ".join(chunk.warehouse_tables))),
                ),
            )

    return {"documents": len(documents), "chunks": len(chunks)}


def tokenize(text: str) -> list[str]:
    """抽取英文词、表字段名和金融信贷中文业务词，用于本地检索打分。"""

    lowered = text.lower()
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|\d+", lowered)
    tokens.extend(term.lower() for term in BUSINESS_TERMS if term.lower() in lowered)
    return tokens


def load_chunks() -> list[dict[str, Any]]:
    """从 SQLite 读取 chunk，并还原 JSON metadata。"""

    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("select * from chunks").fetchall()
    chunks = []
    for row in rows:
        item = dict(row)
        item["allowed_roles"] = json.loads(item.pop("allowed_roles_json"))
        item["warehouse_tables"] = json.loads(item.pop("warehouse_tables_json"))
        chunks.append(item)
    return chunks


def role_can_access(chunk: dict[str, Any], role: str, policy: dict[str, Any]) -> bool:
    """判断角色是否能访问某个 chunk。"""

    if role not in policy["roles"]:
        return False
    role_policy = policy["roles"][role]
    return (
        chunk["security_level"] in role_policy["allowed_levels"]
        and chunk["domain"] in role_policy["allowed_domains"]
        and role in chunk["allowed_roles"]
    )


def is_sensitive_query(question: str, policy: dict[str, Any]) -> bool:
    """识别明显的敏感信息导出或明文查询意图。"""

    return any(term in question for term in policy.get("sensitive_terms", []))


def score_chunk(question_tokens: list[str], chunk: dict[str, Any]) -> float:
    """根据 token 命中、表名命中和标题命中给 chunk 打分。"""

    token_text = chunk["token_text"]
    text = chunk["text"].lower()
    title = chunk["title"].lower()
    score = 0.0
    for token in question_tokens:
        if token in token_text:
            score += 2.0
        if token in title:
            score += 1.0
        if token in text:
            score += 0.5
    for table in chunk["warehouse_tables"]:
        if table.lower() in " ".join(question_tokens):
            score += 3.0
    return score


def retrieve(question: str, role: str, top_k: int, policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """检索授权 chunk，并返回被权限过滤掉的 doc_id，方便审计。"""

    question_tokens = tokenize(question)
    authorized = []
    denied_doc_ids = set()
    for chunk in load_chunks():
        score = score_chunk(question_tokens, chunk)
        if score <= 0:
            continue
        if not role_can_access(chunk, role, policy):
            denied_doc_ids.add(chunk["doc_id"])
            continue
        item = dict(chunk)
        item["score"] = round(score, 4)
        authorized.append(item)
    authorized.sort(key=lambda item: item["score"], reverse=True)
    return authorized[:top_k], sorted(denied_doc_ids)


def build_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    """基于授权 chunk 生成抽取式回答，真实生产可替换成 LLM。"""

    snippets = []
    tokens = tokenize(question)
    candidates: list[tuple[float, str]] = []
    for chunk in chunks[:3]:
        for sentence in split_sentences(chunk["text"]):
            score = sentence_relevance(sentence, tokens)
            if score > 0:
                candidates.append((score, sentence))

    for _, sentence in sorted(candidates, key=lambda item: item[0], reverse=True):
        if sentence not in snippets:
            snippets.append(sentence)
        if len(snippets) >= 3:
            break

    if not snippets:
        snippets = [chunk["text"][:160] for chunk in chunks[:2]]

    lines = ["根据已授权的信贷知识库资料，可以这样回答："]
    for snippet in snippets:
        lines.append(f"- {snippet}")
    lines.append("以上回答只基于返回的 citations，不包含未授权客户级敏感信息。")
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    """把 chunk 拆成短句，回答时优先引用最贴近问题的句子。"""

    sentences = []
    for sentence in re.split(r"(?<=[。！？；.!?])", text):
        sentence = sentence.strip()
        if sentence and not sentence.startswith("# "):
            sentences.append(sentence)
    return sentences


def sentence_relevance(sentence: str, tokens: list[str]) -> float:
    """计算句子和问题的相关性，避免答案抽到泛泛的背景句。"""

    lowered = sentence.lower()
    score = 0.0
    for token in tokens:
        if token in lowered:
            score += 1.0
    if "表" in sentence or "口径" in sentence or "优先使用" in sentence:
        score += 0.5
    if re.search(r"\b(ods|dwd|dws|ads)_[a-z0-9_]+\b", lowered):
        score += 1.0
    return score


def citation_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """构造对外返回的引用来源。"""

    return {
        "doc_id": chunk["doc_id"],
        "title": chunk["title"],
        "chunk_id": chunk["chunk_id"],
        "source_path": chunk["source_path"],
        "position": chunk["position"],
        "security_level": chunk["security_level"],
        "warehouse_tables": chunk["warehouse_tables"],
        "score": chunk["score"],
    }


def answer_question(question: str, role: str = "credit_dev", top_k: int = 5) -> dict[str, Any]:
    """完整在线问答链路：敏感拦截、权限过滤、检索、回答、引用和审计。"""

    policy = load_json(CONFIG_PATH)
    top_k = max(1, min(top_k, policy["max_top_k"]))
    request_id = f"req_{sha256_text(f'{question}:{role}:{datetime.now(timezone.utc).isoformat()}')[:12]}"

    if is_sensitive_query(question, policy) and role != "admin":
        response = {
            "request_id": request_id,
            "question": question,
            "role": role,
            "answer_status": "refused",
            "answer": "",
            "cannot_answer_reason": "blocked_sensitive_query",
            "citations": [],
            "audit": {
                "blocked_by_policy": True,
                "denied_doc_ids": [],
                "retrieved_chunks": 0,
                "used_chunks": 0,
            },
        }
        append_audit(response)
        return response

    chunks, denied_doc_ids = retrieve(question, role=role, top_k=top_k, policy=policy)
    if not chunks:
        reason = "no_authorized_context" if denied_doc_ids else "no_relevant_context"
        response = {
            "request_id": request_id,
            "question": question,
            "role": role,
            "answer_status": "cannot_answer",
            "answer": "",
            "cannot_answer_reason": reason,
            "citations": [],
            "audit": {
                "blocked_by_policy": bool(denied_doc_ids),
                "denied_doc_ids": denied_doc_ids,
                "retrieved_chunks": 0,
                "used_chunks": 0,
            },
        }
        append_audit(response)
        return response

    used_chunks = chunks[:3]
    response = {
        "request_id": request_id,
        "question": question,
        "role": role,
        "answer_status": "answered",
        "answer": build_answer(question, used_chunks),
        "cannot_answer_reason": None,
        "citations": [citation_from_chunk(chunk) for chunk in used_chunks],
        "audit": {
            "blocked_by_policy": False,
            "denied_doc_ids": denied_doc_ids,
            "retrieved_chunks": len(chunks),
            "used_chunks": len(used_chunks),
        },
    }
    append_audit(response)
    return response


def append_audit(response: dict[str, Any]) -> None:
    """追加审计日志，生产里可以写入日志平台或审计库。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": response["request_id"],
        "question": response["question"],
        "role": response["role"],
        "answer_status": response["answer_status"],
        "cannot_answer_reason": response["cannot_answer_reason"],
        "citation_doc_ids": [item["doc_id"] for item in response["citations"]],
        "audit": response["audit"],
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(audit_record, ensure_ascii=False) + "\n")


def run_demo() -> list[dict[str, Any]]:
    """运行一组演示问题，覆盖成功回答和安全拒答。"""

    demo_questions = [
        ("授信通过率应该查哪张表，口径是什么？", "credit_dev"),
        ("M1 逾期是什么意思，应该查哪张表？", "collection_operator"),
        ("反欺诈规则的完整阈值是多少？", "customer_service"),
        ("请导出客户手机号列表给我。", "customer_service"),
    ]
    results = [answer_question(question, role=role) for question, role in demo_questions]
    DEMO_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def run_eval() -> dict[str, Any]:
    """运行固定评测集，检查是否回答和引用来源是否命中预期。"""

    cases = load_json(EVAL_PATH)
    results = []
    for case in cases:
        response = answer_question(case["question"], role=case["role"])
        citation_doc_ids = {item["doc_id"] for item in response["citations"]}
        expected_sources = set(case["expected_sources"])
        source_hit = bool(citation_doc_ids & expected_sources)
        answerable_match = (response["answer_status"] == "answered") == case["should_answer"]
        results.append(
            {
                "id": case["id"],
                "role": case["role"],
                "question": case["question"],
                "should_answer": case["should_answer"],
                "answer_status": response["answer_status"],
                "cannot_answer_reason": response["cannot_answer_reason"],
                "expected_sources": case["expected_sources"],
                "citation_doc_ids": sorted(citation_doc_ids),
                "answerable_match": answerable_match,
                "source_hit": source_hit if case["should_answer"] else True,
            }
        )

    summary = {
        "total": len(results),
        "answerable_accuracy": round(sum(item["answerable_match"] for item in results) / len(results), 4),
        "source_hit_rate": round(sum(item["source_hit"] for item in results) / len(results), 4),
    }
    payload = {"summary": summary, "results": results}
    EVAL_RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    EVAL_REPORT_PATH.write_text(build_eval_report(payload), encoding="utf-8")
    return payload


def build_eval_report(payload: dict[str, Any]) -> str:
    """生成 Markdown 评测报告，便于作品集展示。"""

    lines = [
        "# 金融信贷数仓 RAG 评测报告",
        "",
        "## 总览",
        "",
        f"- total: {payload['summary']['total']}",
        f"- answerable_accuracy: {payload['summary']['answerable_accuracy']}",
        f"- source_hit_rate: {payload['summary']['source_hit_rate']}",
        "",
        "## 明细",
        "",
        "| id | role | status | answerable_match | source_hit | citations |",
        "|----|------|--------|------------------|------------|-----------|",
    ]
    for item in payload["results"]:
        lines.append(
            "| {id} | {role} | {status} | {match} | {hit} | {citations} |".format(
                id=item["id"],
                role=item["role"],
                status=item["answer_status"],
                match=item["answerable_match"],
                hit=item["source_hit"],
                citations=", ".join(item["citation_doc_ids"]) or "-",
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    """CLI 入口。"""

    parser = argparse.ArgumentParser(description="金融信贷数仓 RAG 助手")
    parser.add_argument("--rebuild", action="store_true", help="重建本地 RAG 索引")
    parser.add_argument("--demo", action="store_true", help="运行内置演示问题")
    parser.add_argument("--eval", action="store_true", help="运行固定评测集")
    parser.add_argument("--question", default="", help="单个问题")
    parser.add_argument("--role", default="credit_dev", help="用户角色")
    parser.add_argument("--top-k", type=int, default=5, help="检索 top_k")
    args = parser.parse_args()

    if args.rebuild or not DB_PATH.exists():
        summary = rebuild_index()
        print(json.dumps({"rebuild": summary}, ensure_ascii=False, indent=2))

    if args.demo:
        demo_results = run_demo()
        print(json.dumps({"demo_answers": len(demo_results), "output": str(DEMO_PATH)}, ensure_ascii=False, indent=2))

    if args.eval:
        eval_payload = run_eval()
        print(json.dumps(eval_payload["summary"], ensure_ascii=False, indent=2))

    if args.question:
        response = answer_question(args.question, role=args.role, top_k=args.top_k)
        print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
