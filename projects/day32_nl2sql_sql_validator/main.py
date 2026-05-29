"""Day 32 - NL2SQL SQL 校验器。

这个脚本读取 Day 31 生成的 SQL 草稿，并在执行前做规则校验。
生产环境里 SQL 不能因为语法看起来正确就直接执行，必须先经过只读、
表字段白名单、敏感字段、时间范围、limit 和成本风险检查。
"""

import json
import re
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
CATALOG_PATH = ROOT_DIR / "projects/day29_nl2sql_schema_router/schema_catalog.json"
SQL_GENERATION_RESULT_PATH = (
    ROOT_DIR / "projects/day31_nl2sql_sql_generator/output/sql_generation_results.json"
)
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "sql_validation_results.json"
REPORT_PATH = OUTPUT_DIR / "sql_validation_report.md"

FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "merge",
}

SQL_KEYWORDS_AND_FUNCTIONS = {
    "as",
    "select",
    "from",
    "where",
    "and",
    "or",
    "group",
    "by",
    "order",
    "desc",
    "asc",
    "limit",
    "with",
    "cross",
    "join",
    "on",
    "between",
    "current_date",
    "interval",
    "day",
    "week",
    "month",
    "sum",
    "avg",
    "nullif",
    "date_trunc",
}


def load_json(path: Path) -> Any:
    """读取 JSON 文件，保持校验器和上游生成结果解耦。"""

    return json.loads(path.read_text(encoding="utf-8"))


def table_index(catalog: list[dict]) -> dict[str, dict]:
    """按表名建立索引，方便校验 SQL 中出现的表。"""

    return {table["table_name"]: table for table in catalog}


def table_fields(table: dict) -> set[str]:
    """收集一张表允许查询的字段。"""

    return {column["name"] for column in table.get("columns", [])}


def sensitive_fields(catalog: list[dict]) -> set[str]:
    """收集敏感字段名，执行前统一拦截。"""

    fields = set()
    for table in catalog:
        for column in table.get("columns", []):
            if column.get("role") == "sensitive":
                fields.add(column["name"])
    return fields


def normalize_sql(sql: str) -> str:
    """压缩 SQL 空白字符，方便做关键字和表名检查。"""

    return re.sub(r"\s+", " ", sql.strip().lower())


def extract_table_names(sql: str) -> list[str]:
    """抽取 from / join 后面的表名。

    这里使用轻量规则满足本地练习。生产里建议使用 SQL parser，
    因为复杂嵌套、schema 前缀和方言差异会让正则误判。
    """

    names = []
    for match in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.IGNORECASE):
        names.append(match.group(1))
    return names


def extract_cte_names(sql: str) -> set[str]:
    """抽取 with 子句里定义的 CTE 名称。

    CTE 在后续 `from current_period` 中看起来像表名，但它不是数据库真实表。
    如果不先识别 CTE，校验器会把合法对比查询误判成 unknown_table。
    """

    return set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", sql, re.IGNORECASE))


def extract_identifiers(sql: str) -> set[str]:
    """抽取 SQL 中出现的标识符，用于发现明显未知字段。"""

    identifiers = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", sql))
    return {identifier for identifier in identifiers if identifier.lower() not in SQL_KEYWORDS_AND_FUNCTIONS}


def has_time_predicate(sql: str, tables: list[dict]) -> bool:
    """判断 SQL 是否包含可用时间字段过滤。

    大表查询必须带时间范围，避免 NL2SQL 生成全量扫描。
    """

    normalized = normalize_sql(sql)
    if " where " not in f" {normalized} ":
        return False
    for table in tables:
        for field in table.get("time_fields", []):
            if re.search(rf"\b{re.escape(field.lower())}\b", normalized):
                return True
    return False


def has_precise_detail_filter(sql: str) -> bool:
    """判断明细查询是否带精确过滤条件。"""

    normalized = normalize_sql(sql)
    return bool(re.search(r"\bapplication_id\s*=", normalized) or re.search(r"\bcustomer_id\s*=", normalized))


def validate_sql_case(case: dict, catalog: list[dict]) -> dict:
    """校验单条 SQL，并输出可解释的风险项。"""

    sql = case.get("sql")
    source_status = case.get("source_status", "generated")
    issues = []
    warnings = []

    if not sql:
        return {
            **case,
            "can_execute": False,
            "risk_level": "blocked",
            "issues": ["no_sql_to_validate"],
            "warnings": [],
        }

    normalized = normalize_sql(sql)
    table_map = table_index(catalog)
    cte_names = extract_cte_names(sql)
    table_names = [name for name in extract_table_names(sql) if name not in cte_names]
    tables = [table_map[name] for name in table_names if name in table_map]

    if not (normalized.startswith("select") or normalized.startswith("with")):
        issues.append("not_read_only")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            issues.append(f"forbidden_keyword:{keyword}")

    unknown_tables = [name for name in table_names if name not in table_map]
    if unknown_tables:
        issues.append("unknown_table:" + ",".join(sorted(unknown_tables)))

    if re.search(r"select\s+\*", normalized):
        issues.append("select_star")

    sensitive = sensitive_fields(catalog)
    used_sensitive = sorted(field for field in sensitive if re.search(rf"\b{field}\b", normalized))
    if used_sensitive:
        issues.append("sensitive_field:" + ",".join(used_sensitive))

    if tables:
        allowed_fields = set().union(*(table_fields(table) for table in tables))
        allowed_names = allowed_fields | set(table_names)
        identifiers = extract_identifiers(sql)
        unknown_identifiers = sorted(
            identifier
            for identifier in identifiers
            if identifier not in allowed_names
            and identifier.lower() not in {name.lower() for name in table_names}
            and not re.fullmatch(r"[a-zA-Z]+", identifier)
        )
        # CTE 和别名会产生额外标识符。这里仅保留明显的字段命名风险，
        # 避免把 current_period、current_value 这类 CTE 名误判成真实字段。
        suspicious = [
            identifier
            for identifier in unknown_identifiers
            if identifier.endswith("_id") or identifier.endswith("_amount") or identifier.endswith("_count")
        ]
        if suspicious:
            issues.append("unknown_field:" + ",".join(suspicious))

        requires_time = any(table.get("permission_level") == "internal" for table in tables)
        if requires_time and not has_time_predicate(sql, tables):
            issues.append("missing_time_predicate")

        restricted_detail = any(table.get("permission_level") == "restricted" for table in tables)
        if restricted_detail:
            if " limit " not in f" {normalized} ":
                issues.append("missing_limit_for_detail")
            if not has_precise_detail_filter(sql):
                issues.append("missing_precise_detail_filter")

    if " order by " in f" {normalized} " and " limit " not in f" {normalized} ":
        warnings.append("order_by_without_limit")

    if " join " in f" {normalized} " and " cross join " not in f" {normalized} " and not re.search(r"\bon\b", normalized):
        warnings.append("join_without_on_or_cross_join")

    risk_level = "low"
    if warnings:
        risk_level = "medium"
    if issues:
        risk_level = "high"
    if source_status == "blocked_before_generation":
        risk_level = "blocked"

    return {
        **case,
        "can_execute": not issues,
        "risk_level": risk_level,
        "issues": issues,
        "warnings": warnings,
    }


def build_validation_cases(generation_results: dict) -> list[dict]:
    """把 Day 31 结果转成待校验样例，并补充高风险对照样例。"""

    cases = []
    for item in generation_results["results"]:
        if item.get("sql"):
            cases.append(
                {
                    "question": item["question"],
                    "query_type": item["query_type"],
                    "table": item["table"],
                    "sql": item["sql"],
                    "source_status": "generated",
                }
            )
        else:
            cases.append(
                {
                    "question": item["question"],
                    "query_type": item["query_type"],
                    "table": item["table"],
                    "sql": None,
                    "source_status": "blocked_before_generation",
                }
            )

    cases.extend(
        [
            {
                "question": "危险样例：删除逾期表数据",
                "query_type": "adversarial",
                "table": "dws_repayment_overdue_daily",
                "sql": "delete from dws_repayment_overdue_daily where dt < current_date - interval '365' day;",
                "source_status": "manual_risk_case",
            },
            {
                "question": "危险样例：全量导出客户手机号",
                "query_type": "adversarial",
                "table": "dim_credit_customer",
                "sql": "select customer_id, phone, id_card from dim_credit_customer;",
                "source_status": "manual_risk_case",
            },
            {
                "question": "危险样例：缺少时间范围的授信汇总",
                "query_type": "adversarial",
                "table": "dws_credit_application_daily",
                "sql": "select risk_level, sum(approval_count) as approval_count from dws_credit_application_daily group by risk_level;",
                "source_status": "manual_risk_case",
            },
        ]
    )
    return cases


def summarize(results: list[dict]) -> dict:
    """汇总校验结果，方便报告和后续回归。"""

    return {
        "total": len(results),
        "passed": sum(1 for item in results if item["can_execute"]),
        "failed": sum(
            1
            for item in results
            if item["issues"] and item["source_status"] != "blocked_before_generation"
        ),
        "blocked_before_generation": sum(
            1 for item in results if item["source_status"] == "blocked_before_generation"
        ),
        "warnings": sum(1 for item in results if item["warnings"]),
    }


def write_report(payload: dict) -> None:
    """生成 Markdown 报告，方便人工复盘每条 SQL 为什么通过或失败。"""

    lines = [
        "# Day 32 - NL2SQL SQL 校验报告",
        "",
        "## 总览",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 明细",
            "",
            "| question | source_status | can_execute | risk_level | issues | warnings |",
            "|----------|---------------|-------------|------------|--------|----------|",
        ]
    )

    for item in payload["results"]:
        issues = ", ".join(item["issues"]) if item["issues"] else "-"
        warnings = ", ".join(item["warnings"]) if item["warnings"] else "-"
        lines.append(
            f"| {item['question']} | {item['source_status']} | {item['can_execute']} | "
            f"{item['risk_level']} | {issues} | {warnings} |"
        )

    lines.extend(["", "## SQL 校验样例", ""])
    for index, item in enumerate(payload["results"], start=1):
        lines.append(f"### {index}. {item['question']}")
        if item.get("sql"):
            lines.extend(["", "```sql", item["sql"], "```", ""])
        else:
            lines.append("")
            lines.append("未进入 SQL 校验：上游 SQL 生成阶段已经阻断。")
            lines.append("")
        if item["issues"]:
            lines.append("阻断原因：" + ", ".join(item["issues"]))
        elif item["warnings"]:
            lines.append("可执行，但有警告：" + ", ".join(item["warnings"]))
        else:
            lines.append("校验通过：可进入查询执行层。")
        lines.append("")

    lines.extend(
        [
            "## 结论",
            "",
            "Day 32 的重点是把 SQL 生成层和查询执行层隔开。",
            "生产环境里，NL2SQL 生成的 SQL 必须先经过只读、权限、字段、时间范围、敏感信息和成本校验，",
            "再决定是否允许执行、要求用户补充信息，或进入人工审批流程。",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 32 SQL 校验流程。"""

    catalog = load_json(CATALOG_PATH)
    generation_results = load_json(SQL_GENERATION_RESULT_PATH)
    cases = build_validation_cases(generation_results)
    results = [validate_sql_case(case, catalog) for case in cases]
    payload = {"summary": summarize(results), "results": results}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"结果文件: {RESULT_PATH}")
    print(f"报告文件: {REPORT_PATH}")


if __name__ == "__main__":
    main()
