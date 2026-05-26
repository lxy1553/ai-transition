"""Day 30 - NL2SQL 问题解析器。

这个脚本先不用 LLM，而是用规则和字典把用户问题解析成结构化字段。
生产里这一步通常发生在 SQL 生成之前，用来降低模型编造字段、漏掉时间范围和绕过权限的风险。
"""

import json
import re
from pathlib import Path
from typing import Any, Optional


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
CATALOG_PATH = ROOT_DIR / "projects/day29_nl2sql_schema_router/schema_catalog.json"
QUESTION_PATH = PROJECT_DIR / "questions.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "question_parse_results.json"
REPORT_PATH = OUTPUT_DIR / "question_parse_report.md"

METRIC_ALIASES = {
    "application_count": ["授信申请量", "申请量", "申请数"],
    "approval_count": ["授信通过量", "通过量", "审批通过数"],
    "approval_rate": ["授信通过率", "通过率", "审批通过率"],
    "avg_credit_amount": ["平均授信额度", "平均额度"],
    "disbursement_amount": ["放款金额", "贷款发放金额", "发放金额"],
    "loan_count": ["放款笔数", "贷款笔数", "放款数"],
    "due_amount": ["应还金额"],
    "repayment_amount": ["实还金额", "还款金额"],
    "overdue_amount": ["逾期金额"],
    "overdue_rate": ["逾期率"],
}

DIMENSION_ALIASES = {
    "city": ["城市", "北京", "上海", "深圳", "广州"],
    "dt": ["每天", "每日", "趋势", "按天"],
    "product_type": ["产品", "信贷产品", "产品类型"],
    "channel": ["渠道", "申请渠道"],
    "risk_level": ["风险等级", "风控评级", "评级"],
    "overdue_bucket": ["账龄", "逾期账龄", "M1", "M2"],
    "application_status": ["审批状态", "授信状态", "申请状态"],
    "phone": ["手机号", "电话"],
    "id_card": ["身份证", "身份证号"],
}

TIME_PATTERNS = [
    ("this_week_vs_last_week", ["本周", "比上周"]),
    ("last_7_days", ["最近 7 天", "最近7天", "近 7 天", "近7天"]),
    ("last_week", ["上周"]),
    ("this_week", ["本周"]),
    ("yesterday", ["昨天"]),
    ("this_month", ["本月"]),
]

QUESTION_TYPE_KEYWORDS = {
    "sensitive": ["手机号", "身份证", "导出客户", "客户名单", "客户信息"],
    "detail": ["查询申请", "申请编号", "审批状态", "授信状态"],
    "topn": ["最高", "前", "top", "排名", "topn"],
    "comparison": ["比上周", "环比", "同比", "变化", "对比"],
    "trend": ["趋势", "最近 7 天", "最近7天", "每天", "每日"],
    "group_by": ["每个", "各", "按", "分城市", "城市", "渠道", "产品", "账龄", "风险等级"],
    "metric": ["多少", "数", "金额", "授信", "申请量", "通过率", "放款", "逾期率", "逾期金额"],
}


def load_json(path: Path) -> Any:
    """读取 JSON 配置或测试样本。"""

    return json.loads(path.read_text(encoding="utf-8"))


def contains_any(text: str, aliases: list[str]) -> bool:
    """判断文本是否包含任意别名。"""

    normalized = text.lower()
    return any(alias.lower() in normalized for alias in aliases)


def classify_question(question: str) -> str:
    """识别问题类型，给后续 SQL 模板选择提供依据。"""

    normalized = question.lower()
    for question_type in ["sensitive", "topn", "comparison", "trend", "group_by", "detail", "metric"]:
        if any(keyword.lower() in normalized for keyword in QUESTION_TYPE_KEYWORDS[question_type]):
            return question_type
    return "unknown"


def extract_metrics(question: str) -> list[str]:
    """抽取标准指标名。

    用户会说放款金额、授信通过率、逾期率、申请量等不同表达。
    这里统一映射到标准指标名，后续才能和 Schema Catalog 对齐。
    """

    metrics = []
    for metric, aliases in METRIC_ALIASES.items():
        if contains_any(question, aliases):
            metrics.append(metric)
    return metrics


def extract_dimensions(question: str, question_type: str) -> list[str]:
    """抽取维度字段。

    维度既可能用于 group by，也可能用于 where 过滤。
    这里先抽出候选维度，后续 SQL 生成时再结合 question_type 决定怎么使用。
    """

    dimensions = []
    for dimension, aliases in DIMENSION_ALIASES.items():
        if contains_any(question, aliases):
            dimensions.append(dimension)

    if question_type == "trend" and "dt" not in dimensions:
        dimensions.append("dt")
    return dimensions


def extract_time_range(question: str) -> Optional[str]:
    """把自然语言时间词转成标准时间范围。"""

    for time_name, aliases in TIME_PATTERNS:
        if contains_any(question, aliases):
            return time_name
    return None


def extract_top_n(question: str) -> Optional[int]:
    """抽取 TopN 的 N 值。"""

    match = re.search(r"(?:前|top\s*)(\d+)", question, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"前\s*(\d+)\s*名", question)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*个", question)
    if "最高" in question and match:
        return int(match.group(1))
    return None


def extract_filters(question: str) -> dict[str, str]:
    """抽取明确过滤条件，例如申请编号、城市、风险等级和审批状态。"""

    filters: dict[str, str] = {}
    application_match = re.search(r"申请\s*([A-Za-z]\d+)", question)
    if application_match:
        filters["application_id"] = application_match.group(1)

    for city in ["北京", "上海", "深圳", "广州"]:
        if city in question:
            filters["city"] = city

    for level in ["A", "B", "C", "D", "高风险", "中风险", "低风险"]:
        if f"{level}级" in question or level in question and "风险" in question:
            filters["risk_level"] = level

    for status in ["审批通过", "审批拒绝", "待审批", "已放款", "已结清"]:
        if status in question:
            filters["application_status"] = status
    return filters


def collect_catalog_fields(catalog: list[dict]) -> set[str]:
    """收集 Schema Catalog 中允许出现的字段名。"""

    fields = set()
    for table in catalog:
        for column in table.get("columns", []):
            fields.add(column["name"])
        fields.update(table.get("metrics", []))
        fields.update(table.get("dimensions", []))
    return fields


def build_risk_flags(parse_result: dict, catalog_fields: set[str]) -> list[str]:
    """根据解析结果识别风险，避免坏问题直接进入 SQL 生成。"""

    risk_flags = []
    if parse_result["query_type"] in {"metric", "group_by", "trend", "topn", "comparison"}:
        if not parse_result["time_range"]:
            risk_flags.append("missing_time_range")
    if parse_result["query_type"] == "sensitive" or any(
        field in {"phone", "id_card"} for field in parse_result["dimensions"]
    ):
        risk_flags.append("sensitive_field")
    if not parse_result["metrics"] and parse_result["query_type"] not in {"detail", "sensitive"}:
        risk_flags.append("missing_metric")

    used_fields = set(parse_result["metrics"]) | set(parse_result["dimensions"]) | set(parse_result["filters"].keys())
    unknown_fields = sorted(field for field in used_fields if field not in catalog_fields)
    if unknown_fields:
        risk_flags.append(f"unknown_fields:{','.join(unknown_fields)}")
    return risk_flags


def parse_question(question: str, catalog_fields: set[str]) -> dict:
    """解析单个用户问题。"""

    question_type = classify_question(question)
    parse_result = {
        "question": question,
        "query_type": question_type,
        "metrics": extract_metrics(question),
        "dimensions": extract_dimensions(question, question_type),
        "time_range": extract_time_range(question),
        "top_n": extract_top_n(question),
        "filters": extract_filters(question),
        "risk_flags": [],
    }
    parse_result["risk_flags"] = build_risk_flags(parse_result, catalog_fields)
    return parse_result


def compare_expected(actual: dict, expected: dict) -> dict:
    """对比解析结果和预期结果，输出字段级通过情况。"""

    checks = {}
    for field in ["query_type", "time_range", "top_n"]:
        if field in expected:
            checks[field] = actual.get(field) == expected[field]
    for field in ["metrics", "dimensions", "risk_flags"]:
        if field in expected:
            checks[field] = set(actual.get(field) or []) >= set(expected[field])
    if "filters" in expected:
        checks["filters"] = all(actual["filters"].get(key) == value for key, value in expected["filters"].items())
    return {
        "checks": checks,
        "passed": all(checks.values()) if checks else True,
    }


def build_report(results: list[dict], summary: dict) -> str:
    """生成 Markdown 解析报告。"""

    lines = [
        "# Day 30 - NL2SQL 问题解析报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- passed: {summary['passed']}",
        f"- accuracy: {summary['accuracy']}",
        f"- risk_cases: {summary['risk_cases']}",
        "",
        "## 明细",
        "",
        "| question | type | metrics | dimensions | time_range | filters | risks | passed |",
        "|----------|------|---------|------------|------------|---------|-------|--------|",
    ]
    for item in results:
        parsed = item["parsed"]
        lines.append(
            "| {question} | {query_type} | {metrics} | {dimensions} | {time_range} | {filters} | {risks} | {passed} |".format(
                question=parsed["question"],
                query_type=parsed["query_type"],
                metrics=", ".join(parsed["metrics"]) or "-",
                dimensions=", ".join(parsed["dimensions"]) or "-",
                time_range=parsed["time_range"] or "-",
                filters=json.dumps(parsed["filters"], ensure_ascii=False) if parsed["filters"] else "-",
                risks=", ".join(parsed["risk_flags"]) or "-",
                passed=item["evaluation"]["passed"],
            )
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "Day 30 的重点是先把自然语言问题解析成结构化字段，再交给 Schema Router 和 SQL 生成。",
            "问题解析越清楚，后面的 SQL 生成、权限校验、成本控制和错误排查越稳定。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行问题解析实验，并生成报告。"""

    catalog = load_json(CATALOG_PATH)
    samples = load_json(QUESTION_PATH)
    catalog_fields = collect_catalog_fields(catalog)

    results = []
    for sample in samples:
        parsed = parse_question(sample["question"], catalog_fields)
        evaluation = compare_expected(parsed, sample["expected"])
        results.append(
            {
                "question": sample["question"],
                "expected": sample["expected"],
                "parsed": parsed,
                "evaluation": evaluation,
            }
        )

    total = len(results)
    passed = sum(1 for item in results if item["evaluation"]["passed"])
    summary = {
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total, 4) if total else 0,
        "risk_cases": sum(1 for item in results if item["parsed"]["risk_flags"]),
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
