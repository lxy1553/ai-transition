"""Day 31 - NL2SQL SQL 生成器。

这个脚本把 Day 30 的问题解析结果转成只读 SQL 草稿。
生产环境里这一步不能直接执行 SQL，必须先经过 Day 32 这类 SQL 校验层，
检查只读约束、表字段合法性、权限、时间范围和扫描成本。
"""

import json
from pathlib import Path
from typing import Any, Optional


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
CATALOG_PATH = ROOT_DIR / "projects/day29_nl2sql_schema_router/schema_catalog.json"
PARSE_RESULT_PATH = ROOT_DIR / "projects/day30_nl2sql_question_parser/output/question_parse_results.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "sql_generation_results.json"
REPORT_PATH = OUTPUT_DIR / "sql_generation_report.md"

BLOCKING_RISKS = {"sensitive_field", "missing_time_range"}

AGGREGATE_EXPRESSIONS = {
    "application_count": "sum(application_count) as application_count",
    "approval_count": "sum(approval_count) as approval_count",
    "approval_rate": "sum(approval_count) / nullif(sum(application_count), 0) as approval_rate",
    "avg_credit_amount": "avg(avg_credit_amount) as avg_credit_amount",
    "disbursement_amount": "sum(disbursement_amount) as disbursement_amount",
    "loan_count": "sum(loan_count) as loan_count",
    "due_amount": "sum(due_amount) as due_amount",
    "repayment_amount": "sum(repayment_amount) as repayment_amount",
    "overdue_amount": "sum(overdue_amount) as overdue_amount",
    "overdue_rate": "sum(overdue_amount) / nullif(sum(due_amount), 0) as overdue_rate",
    "approved_amount": "sum(approved_amount) as approved_amount",
}

DETAIL_SELECT_FIELDS = {
    "application_status": ["application_id", "application_status", "approved_amount", "risk_level", "apply_time"],
}

TIME_PREDICATES = {
    "yesterday": "dt = current_date - interval '1' day",
    "last_7_days": "dt between current_date - interval '7' day and current_date - interval '1' day",
    "last_week": (
        "dt between date_trunc('week', current_date) - interval '7' day "
        "and date_trunc('week', current_date) - interval '1' day"
    ),
    "this_week": "dt >= date_trunc('week', current_date) and dt < current_date + interval '1' day",
    "this_month": "dt >= date_trunc('month', current_date) and dt < current_date + interval '1' day",
}

COMPARISON_WINDOWS = {
    "this_week_vs_last_week": {
        "current": "dt >= date_trunc('week', current_date) and dt < current_date + interval '1' day",
        "previous": (
            "dt between date_trunc('week', current_date) - interval '7' day "
            "and date_trunc('week', current_date) - interval '1' day"
        ),
    }
}


def load_json(path: Path) -> Any:
    """读取 JSON 文件，避免把上游解析结果和 Schema Catalog 写死在代码里。"""

    return json.loads(path.read_text(encoding="utf-8"))


def table_fields(table: dict) -> set[str]:
    """收集单表里所有可用字段，生成 SQL 前用来做字段白名单检查。"""

    fields = {column["name"] for column in table.get("columns", [])}
    fields.update(table.get("metrics", []))
    fields.update(table.get("dimensions", []))
    fields.update(table.get("time_fields", []))
    return fields


def build_table_index(catalog: list[dict]) -> dict[str, dict]:
    """按表名建立索引，方便报告和调试。"""

    return {table["table_name"]: table for table in catalog}


def choose_table(parse_result: dict, catalog: list[dict]) -> Optional[dict]:
    """根据指标、维度和过滤字段选择最合适的表。

    这里故意使用确定性打分，而不是让模型自由选择表。
    生产里可以把这一步替换成 Schema Router、metadata 检索或 LLM rerank，
    但最终仍然要落到白名单表字段。
    """

    needed_metrics = set(parse_result.get("metrics") or [])
    needed_dimensions = set(parse_result.get("dimensions") or [])
    needed_filters = set(parse_result.get("filters") or [])
    query_type = parse_result.get("query_type")

    if query_type == "detail":
        needed_dimensions.add("application_id")

    scored = []
    for table in catalog:
        fields = table_fields(table)
        if needed_metrics and not needed_metrics.issubset(fields):
            continue
        if needed_filters and not needed_filters.issubset(fields):
            continue

        dimension_hits = len(needed_dimensions & fields)
        metric_hits = len(needed_metrics & fields)
        filter_hits = len(needed_filters & fields)
        score = metric_hits * 3 + dimension_hits * 2 + filter_hits

        if query_type == "detail" and table["grain"] == "application_id":
            score += 5
        if query_type != "detail" and table["permission_level"] == "internal":
            score += 1

        if score > 0:
            scored.append((score, table))

    if not scored:
        return None
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]


def sql_literal(value: str) -> str:
    """生成 SQL 字符串字面量，避免测试样例里的单引号破坏 SQL。"""

    return "'" + value.replace("'", "''") + "'"


def build_filter_predicates(filters: dict[str, str]) -> list[str]:
    """把结构化 filters 转成 where 条件。"""

    return [f"{field} = {sql_literal(value)}" for field, value in filters.items()]


def build_select_sql(parse_result: dict, table: dict) -> str:
    """生成普通聚合、分组、趋势和 TopN SQL。"""

    metrics = parse_result.get("metrics") or []
    dimensions = [dimension for dimension in parse_result.get("dimensions", []) if dimension not in {"phone", "id_card"}]
    filters = parse_result.get("filters") or {}

    select_parts = []
    group_by_fields = []
    for dimension in dimensions:
        if dimension in table_fields(table):
            select_parts.append(dimension)
            group_by_fields.append(dimension)

    for metric in metrics:
        select_parts.append(AGGREGATE_EXPRESSIONS[metric])

    predicates = []
    time_range = parse_result.get("time_range")
    if time_range in TIME_PREDICATES:
        predicates.append(TIME_PREDICATES[time_range])
    predicates.extend(build_filter_predicates(filters))

    lines = [
        "select",
        "  " + ",\n  ".join(select_parts),
        f"from {table['table_name']}",
    ]
    if predicates:
        lines.append("where " + "\n  and ".join(predicates))
    if group_by_fields:
        lines.append("group by " + ", ".join(group_by_fields))
    if parse_result.get("query_type") == "topn" and metrics:
        lines.append(f"order by {metrics[0]} desc")
        lines.append(f"limit {parse_result.get('top_n') or 10}")
    return "\n".join(lines) + ";"


def build_comparison_sql(parse_result: dict, table: dict) -> Optional[str]:
    """生成本周和上周这类对比 SQL。

    对比查询不用一个 where 时间条件解决，而是生成两个时间窗口，再计算差值。
    """

    metrics = parse_result.get("metrics") or []
    if not metrics:
        return None
    metric = metrics[0]
    windows = COMPARISON_WINDOWS.get(parse_result.get("time_range"))
    if not windows:
        return None

    expression = AGGREGATE_EXPRESSIONS[metric].replace(f" as {metric}", "")
    return "\n".join(
        [
            "with current_period as (",
            f"  select {expression} as current_value",
            f"  from {table['table_name']}",
            f"  where {windows['current']}",
            "),",
            "previous_period as (",
            f"  select {expression} as previous_value",
            f"  from {table['table_name']}",
            f"  where {windows['previous']}",
            ")",
            "select",
            "  current_value,",
            "  previous_value,",
            "  current_value - previous_value as diff_value",
            "from current_period",
            "cross join previous_period;",
        ]
    )


def build_detail_sql(parse_result: dict, table: dict) -> str:
    """生成明细查询 SQL。

    明细查询必须有精确过滤条件，并且默认加 limit，避免变成大表扫描。
    """

    fields = DETAIL_SELECT_FIELDS.get("application_status", ["application_id", "application_status"])
    available_fields = table_fields(table)
    select_fields = [field for field in fields if field in available_fields]
    predicates = build_filter_predicates(parse_result.get("filters") or {})

    lines = [
        "select",
        "  " + ",\n  ".join(select_fields),
        f"from {table['table_name']}",
    ]
    if predicates:
        lines.append("where " + "\n  and ".join(predicates))
    lines.append("limit 50;")
    return "\n".join(lines)


def should_block(parse_result: dict) -> list[str]:
    """识别 SQL 生成阶段必须拦截的问题。"""

    risks = set(parse_result.get("risk_flags") or [])
    blocking = sorted(risk for risk in risks if risk in BLOCKING_RISKS)
    if parse_result.get("query_type") == "sensitive":
        blocking.append("sensitive_query")
    return sorted(set(blocking))


def validate_sql(sql: Optional[str], table: Optional[dict]) -> list[str]:
    """做最小静态检查，Day 32 会继续扩展成完整 SQL 校验器。"""

    if not sql:
        return ["empty_sql"]

    normalized = sql.strip().lower()
    issues = []
    if not (normalized.startswith("select") or normalized.startswith("with")):
        issues.append("not_read_only")
    for forbidden in [" insert ", " update ", " delete ", " drop ", " alter ", " truncate "]:
        if forbidden in f" {normalized} ":
            issues.append(f"forbidden_keyword:{forbidden.strip()}")
    if table and table["table_name"].lower() not in normalized:
        issues.append("missing_table_name")
    return issues


def generate_sql(parse_result: dict, catalog: list[dict]) -> dict:
    """生成单个问题的 SQL 草稿和决策信息。"""

    blocking_reasons = should_block(parse_result)
    if blocking_reasons:
        return {
            "question": parse_result["question"],
            "query_type": parse_result["query_type"],
            "can_generate_sql": False,
            "blocking_reasons": blocking_reasons,
            "table": None,
            "sql": None,
            "validation_issues": ["blocked_before_generation"],
        }

    table = choose_table(parse_result, catalog)
    if not table:
        return {
            "question": parse_result["question"],
            "query_type": parse_result["query_type"],
            "can_generate_sql": False,
            "blocking_reasons": ["no_candidate_table"],
            "table": None,
            "sql": None,
            "validation_issues": ["no_candidate_table"],
        }

    if parse_result["query_type"] == "detail":
        sql = build_detail_sql(parse_result, table)
    elif parse_result["query_type"] == "comparison":
        sql = build_comparison_sql(parse_result, table)
    else:
        sql = build_select_sql(parse_result, table)

    validation_issues = validate_sql(sql, table)
    return {
        "question": parse_result["question"],
        "query_type": parse_result["query_type"],
        "can_generate_sql": not validation_issues,
        "blocking_reasons": [],
        "table": table["table_name"],
        "sql": sql,
        "validation_issues": validation_issues,
    }


def build_report(results: list[dict], summary: dict) -> str:
    """生成 Markdown 报告，方便复盘 SQL 生成质量。"""

    lines = [
        "# Day 31 - NL2SQL SQL 生成报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- generated: {summary['generated']}",
        f"- blocked: {summary['blocked']}",
        f"- validation_failed: {summary['validation_failed']}",
        "",
        "## 明细",
        "",
        "| question | type | table | can_generate_sql | blocking_reasons | validation_issues |",
        "|----------|------|-------|------------------|------------------|-------------------|",
    ]
    for item in results:
        lines.append(
            "| {question} | {query_type} | {table} | {can_generate_sql} | {blocking} | {issues} |".format(
                question=item["question"],
                query_type=item["query_type"],
                table=item["table"] or "-",
                can_generate_sql=item["can_generate_sql"],
                blocking=", ".join(item["blocking_reasons"]) or "-",
                issues=", ".join(item["validation_issues"]) or "-",
            )
        )

    lines.extend(["", "## SQL 草稿", ""])
    for index, item in enumerate(results, start=1):
        lines.append(f"### {index}. {item['question']}")
        if item["sql"]:
            lines.extend(["", "```sql", item["sql"], "```", ""])
        else:
            lines.extend(["", f"未生成 SQL：{', '.join(item['blocking_reasons'])}", ""])

    lines.extend(
        [
            "## 结论",
            "",
            "Day 31 的重点不是让 SQL 直接上线执行，而是把解析结果、Schema Catalog 和只读约束结合起来，",
            "生成一份可审查、可校验、可追踪的 SQL 草稿。",
            "生产环境里还必须接 Day 32 的 SQL 校验层，继续检查权限、字段白名单、时间范围、扫描成本和危险关键字。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行 SQL 生成实验，并写出 JSON 与 Markdown 报告。"""

    catalog = load_json(CATALOG_PATH)
    parse_payload = load_json(PARSE_RESULT_PATH)
    parse_results = [item["parsed"] for item in parse_payload["results"]]

    results = [generate_sql(parse_result, catalog) for parse_result in parse_results]
    summary = {
        "total": len(results),
        "generated": sum(1 for item in results if item["can_generate_sql"]),
        "blocked": sum(1 for item in results if not item["can_generate_sql"] and item["blocking_reasons"]),
        "validation_failed": sum(1 for item in results if item["validation_issues"] and not item["blocking_reasons"]),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(results, summary), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
