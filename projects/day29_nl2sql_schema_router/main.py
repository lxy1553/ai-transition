"""Day 29 - NL2SQL Schema Router。

这个脚本负责 NL2SQL 的第一步：不直接生成 SQL，而是先判断用户问题类型、
推荐候选表字段，并识别权限和敏感风险。
生产环境里这一步通常接在 API 入参之后、SQL 生成之前，用来降低模型编造和误查大表的风险。
"""

import json
from pathlib import Path
from typing import Union


PROJECT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = PROJECT_DIR / "schema_catalog.json"
QUESTION_PATH = PROJECT_DIR / "questions.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "schema_routing_results.json"
REPORT_PATH = OUTPUT_DIR / "schema_routing_report.md"


TYPE_KEYWORDS = {
    "topn": ["最高", "前", "top", "排名", "最大"],
    "trend": ["趋势", "最近", "每天", "近 7 天", "近7天"],
    "comparison": ["比上周", "环比", "同比", "变化", "对比"],
    "detail": ["查询申请", "申请编号", "审批状态", "授信状态"],
    "sensitive": ["手机号", "身份证", "导出客户", "客户名单", "客户信息"],
    "group_by": ["每个", "各", "按", "分城市", "城市", "渠道", "产品", "账龄"],
    "metric": ["多少", "数", "金额", "授信", "申请量", "通过率", "放款", "逾期率", "逾期金额"],
}


def load_json(path: Path) -> Union[list[dict], list[str]]:
    """读取 JSON 配置，避免把 schema 和问题样例写死在代码里。"""

    return json.loads(path.read_text(encoding="utf-8"))


def classify_question(question: str) -> str:
    """根据关键词判断问题类型，给后续 SQL 生成选择不同模板。"""

    normalized = question.lower()
    for question_type in ["sensitive", "detail", "topn", "comparison", "trend", "group_by", "metric"]:
        if any(keyword.lower() in normalized for keyword in TYPE_KEYWORDS[question_type]):
            return question_type
    return "unknown"


def score_table(question: str, table: dict) -> int:
    """给候选表打分，分数来自表别名、指标、维度和字段描述的命中情况。"""

    normalized = question.lower()
    searchable_terms = []
    searchable_terms.extend(table.get("aliases", []))
    searchable_terms.extend(table.get("metrics", []))
    searchable_terms.extend(table.get("dimensions", []))
    for column in table.get("columns", []):
        searchable_terms.append(column["name"])
        searchable_terms.append(column["description"])

    return sum(1 for term in searchable_terms if term and term.lower() in normalized)


def select_candidates(question: str, catalog: list[dict]) -> list[dict]:
    """选择与问题最相关的候选表，生产里可以替换成向量检索或 metadata 检索。"""

    scored = []
    for table in catalog:
        score = score_table(question, table)
        if score > 0:
            scored.append({"score": score, "table": table})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:3]


def collect_fields(candidates: list[dict], role: str) -> list[str]:
    """从候选表中收集指定角色的字段，方便生成 SQL 前缩小字段范围。"""

    fields: list[str] = []
    for candidate in candidates:
        for column in candidate["table"].get("columns", []):
            if column["role"] == role and column["name"] not in fields:
                fields.append(column["name"])
    return fields


def build_routing_result(question: str, catalog: list[dict]) -> dict:
    """构造单个问题的路由结果，决定是否建议进入 SQL 生成阶段。"""

    question_type = classify_question(question)
    candidates = select_candidates(question, catalog)
    candidate_tables = [candidate["table"]["table_name"] for candidate in candidates]
    candidate_metrics = []
    candidate_dimensions = []
    time_fields = []
    risk_flags = []

    for candidate in candidates:
        table = candidate["table"]
        for metric in table.get("metrics", []):
            if metric not in candidate_metrics:
                candidate_metrics.append(metric)
        for dimension in table.get("dimensions", []):
            if dimension not in candidate_dimensions:
                candidate_dimensions.append(dimension)
        for time_field in table.get("time_fields", []):
            if time_field not in time_fields:
                time_fields.append(time_field)
        if table["permission_level"] in {"restricted", "sensitive"}:
            risk_flags.append(f"permission:{table['permission_level']}")

    if question_type == "sensitive":
        risk_flags.append("sensitive_query")
    if question_type in {"metric", "group_by", "trend", "topn", "comparison"} and not time_fields:
        risk_flags.append("missing_time_field")
    if not candidate_tables:
        risk_flags.append("no_candidate_table")

    should_generate_sql = bool(candidate_tables) and "sensitive_query" not in risk_flags
    return {
        "question": question,
        "question_type": question_type,
        "candidate_tables": candidate_tables,
        "candidate_metrics": candidate_metrics,
        "candidate_dimensions": candidate_dimensions,
        "time_fields": time_fields,
        "risk_flags": risk_flags,
        "should_generate_sql": should_generate_sql,
    }


def build_report(results: list[dict]) -> str:
    """把路由结果输出成 Markdown，方便学习复盘和面试讲解。"""

    lines = [
        "# Day 29 - NL2SQL Schema Router 报告",
        "",
        "## 总览",
        "",
        f"- questions: {len(results)}",
        f"- can_generate_sql: {sum(1 for item in results if item['should_generate_sql'])}",
        f"- blocked_or_need_review: {sum(1 for item in results if not item['should_generate_sql'])}",
        "",
        "## 明细",
        "",
        "| question | type | candidate_tables | risk_flags | should_generate_sql |",
        "|----------|------|------------------|------------|---------------------|",
    ]
    for item in results:
        lines.append(
            "| {question} | {question_type} | {tables} | {risks} | {should} |".format(
                question=item["question"],
                question_type=item["question_type"],
                tables=", ".join(item["candidate_tables"]) or "-",
                risks=", ".join(item["risk_flags"]) or "-",
                should=item["should_generate_sql"],
            )
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "Day 29 的重点是先做 schema 路由，而不是直接生成 SQL。",
            "如果候选表、指标、维度、时间字段和权限边界不清楚，后面的 SQL 生成越自动越危险。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行 Schema Router，并写出 JSON 与 Markdown 报告。"""

    catalog = load_json(SCHEMA_PATH)
    questions = load_json(QUESTION_PATH)
    results = [build_routing_result(question, catalog) for question in questions]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report(results), encoding="utf-8")

    summary = {
        "questions": len(results),
        "can_generate_sql": sum(1 for item in results if item["should_generate_sql"]),
        "blocked_or_need_review": sum(1 for item in results if not item["should_generate_sql"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
