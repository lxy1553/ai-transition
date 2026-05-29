"""Day 34 - NL2SQL 查询结果解释器。

这个脚本读取 Day 33 的查询执行结果，把结构化行列结果转成业务语言。
生产环境里这层不能编造数据，只能基于执行层返回的 rows、columns 和 summary_text
解释业务含义，并补充口径说明、风险提示和建议追问。
"""

import json
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
EXECUTION_RESULT_PATH = (
    ROOT_DIR / "projects/day33_nl2sql_query_executor/output/query_execution_results.json"
)
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "result_interpretation_results.json"
REPORT_PATH = OUTPUT_DIR / "result_interpretation_report.md"


FIELD_LABELS = {
    "channel": "渠道",
    "city": "城市",
    "product_type": "产品",
    "overdue_bucket": "逾期账龄",
    "dt": "日期",
    "application_count": "授信申请量",
    "approval_rate": "授信通过率",
    "disbursement_amount": "放款金额",
    "loan_count": "放款笔数",
    "overdue_amount": "逾期金额",
    "current_value": "当前值",
    "previous_value": "上期值",
    "diff_value": "变化值",
    "application_status": "审批状态",
    "approved_amount": "审批额度",
    "risk_level": "风险等级",
    "apply_time": "申请时间",
}

STATUS_LABELS = {
    "APPROVED": "审批通过",
    "REJECTED": "审批拒绝",
}


def load_json(path: Path) -> Any:
    """读取 Day 33 的执行结果，保持解释层只依赖稳定 JSON 契约。"""

    return json.loads(path.read_text(encoding="utf-8"))


def format_number(value: Any) -> str:
    """把数值格式化成业务更容易读的形式。"""

    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value * 100:.2f}%"
        if abs(value) >= 10000:
            return f"{value / 10000:.2f} 万"
        return f"{value:.2f}"
    if isinstance(value, int):
        if abs(value) >= 10000:
            return f"{value / 10000:.2f} 万"
        return str(value)
    return str(value)


def format_plain_number(value: Any) -> str:
    """保留原始数量单位，不把申请量、笔数这类整数改成百分比。"""

    if isinstance(value, float) and abs(value) >= 10000:
        return f"{value / 10000:.2f} 万"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def explain_scalar(case: dict) -> dict:
    """解释单指标结果，例如昨天授信申请量。"""

    row = case["rows"][0]
    field = case["columns"][0]
    value = row[field]
    label = FIELD_LABELS.get(field, field)
    unit = "笔" if field.endswith("_count") else ""
    text = f"{case['question']} 查询结果为：{label} {format_plain_number(value)}{unit}。"
    text = f"查询结果为：{label} {format_plain_number(value)}{unit}。"
    return {
        "business_answer": text,
        "key_findings": [f"{label} = {format_plain_number(value)}{unit}"],
        "risk_notes": ["该结果来自本地演示数据，生产环境需要说明数据日期和统计口径。"],
        "follow_up_questions": ["是否需要按渠道、产品或风险等级继续拆分？"],
    }


def explain_group_or_topn(case: dict) -> dict:
    """解释分组或 TopN 结果。"""

    rows = case["rows"]
    metric_field = next((col for col in case["columns"] if col not in {"channel", "city", "product_type", "overdue_bucket", "risk_level", "dt"}), case["columns"][-1])
    dimension_fields = [col for col in case["columns"] if col != metric_field]
    dimension_labels = [FIELD_LABELS.get(field, field) for field in dimension_fields]
    label = FIELD_LABELS.get(metric_field, metric_field)

    sorted_rows = sorted(rows, key=lambda item: item.get(metric_field) or 0, reverse=True)
    top = sorted_rows[0] if sorted_rows else {}
    bottom = sorted_rows[-1] if len(sorted_rows) > 1 else None
    top_name = " / ".join(str(top[field]) for field in dimension_fields)
    findings = [f"{top_name} 的{label}最高，为 {format_number(top[metric_field])}。"]

    if bottom:
        bottom_name = " / ".join(str(bottom[field]) for field in dimension_fields)
        findings.append(f"{bottom_name} 的{label}最低，为 {format_number(bottom[metric_field])}。")

    if case.get("query_type") == "topn":
        answer = f"本次返回 {len(rows)} 条排序结果，{top_name} 排名第一，{label}为 {format_number(top[metric_field])}。"
    else:
        answer = f"本次按 {'、'.join(dimension_labels)} 分组返回 {len(rows)} 行结果，{top_name} 表现最高。"

    return {
        "business_answer": answer,
        "key_findings": findings,
        "risk_notes": ["分组结果只能说明当前查询周期内的表现，不能直接代表长期趋势。"],
        "follow_up_questions": ["是否需要继续按产品、城市或风险等级交叉拆分？"],
    }


def explain_trend(case: dict) -> dict:
    """解释趋势结果。"""

    rows = case["rows"]
    metric_field = next((col for col in case["columns"] if col not in {"dt", "city"}), case["columns"][-1])
    label = FIELD_LABELS.get(metric_field, metric_field)
    first = rows[0][metric_field]
    last = rows[-1][metric_field]
    total = sum(row[metric_field] for row in rows)
    peak = max(rows, key=lambda item: item[metric_field])
    trough = min(rows, key=lambda item: item[metric_field])
    direction = "上升" if last > first else "下降" if last < first else "持平"

    answer = (
        f"最近 {len(rows)} 天{label}整体{direction}，"
        f"首日为 {format_number(first)}，末日为 {format_number(last)}。"
    )
    findings = [
        f"累计{label}为 {format_number(total)}。",
        f"最高点出现在 {peak['dt']}，数值为 {format_number(peak[metric_field])}。",
        f"最低点出现在 {trough['dt']}，数值为 {format_number(trough[metric_field])}。",
    ]
    return {
        "business_answer": answer,
        "key_findings": findings,
        "risk_notes": ["趋势解释只基于当前查询窗口，生产分析还需要结合节假日、渠道活动和样本量。"],
        "follow_up_questions": ["是否需要按渠道、城市或产品拆分趋势？"],
    }


def explain_comparison(case: dict) -> dict:
    """解释当前周期和上一周期的对比结果。"""

    row = case["rows"][0]
    current = row["current_value"]
    previous = row["previous_value"]
    diff = row["diff_value"]
    direction = "下降" if diff < 0 else "上升" if diff > 0 else "持平"
    answer = (
        f"当前周期逾期率为 {format_number(current)}，上期为 {format_number(previous)}，"
        f"较上期{direction} {abs(diff) * 100:.2f} 个百分点。"
    )
    return {
        "business_answer": answer,
        "key_findings": [
            f"当前值：{format_number(current)}。",
            f"上期值：{format_number(previous)}。",
            f"变化值：{diff * 100:.2f} 个百分点。",
        ],
        "risk_notes": ["比例指标必须说明分子分母口径，不能只看差值判断风险已经改善。"],
        "follow_up_questions": ["是否需要按产品、风险等级或逾期账龄拆分变化原因？"],
    }


def explain_detail(case: dict) -> dict:
    """解释明细查询结果。"""

    row = case["rows"][0]
    status = STATUS_LABELS.get(row.get("application_status"), row.get("application_status"))
    amount = format_number(row.get("approved_amount"))
    answer = (
        f"申请 {row.get('application_id')} 当前审批状态为{status}，"
        f"审批额度为 {amount}，风险等级为 {row.get('risk_level')}。"
    )
    return {
        "business_answer": answer,
        "key_findings": [
            f"审批状态：{status}。",
            f"审批额度：{amount}。",
            f"申请时间：{row.get('apply_time')}。",
        ],
        "risk_notes": ["明细结果涉及单个申请，生产环境需要确认当前用户是否有查看该申请的权限。"],
        "follow_up_questions": ["是否需要查看审批拒绝原因、规则命中情况或贷后表现？"],
    }


def explain_skipped(case: dict) -> dict:
    """解释未执行查询，让业务知道是安全拦截而不是系统无结果。"""

    reason = case.get("skip_reason", "unknown")
    answer = f"该问题没有执行数据库查询，原因是：{reason}。这不是空结果，而是系统安全或校验策略主动拦截。"
    return {
        "business_answer": answer,
        "key_findings": ["执行层未访问数据库。"],
        "risk_notes": ["被 SQL Validator 或上游生成阶段阻断的问题不能绕过执行层继续查询。"],
        "follow_up_questions": ["是否可以补充时间范围、改查汇总指标，或走敏感数据审批流程？"],
    }


def interpret_case(case: dict) -> dict:
    """根据 response_type 选择解释策略。"""

    if case.get("status") != "executed":
        explanation = explain_skipped(case)
    elif case.get("response_type") == "scalar":
        explanation = explain_scalar(case)
    elif case.get("response_type") == "trend_table":
        explanation = explain_trend(case)
    elif case.get("response_type") == "comparison":
        explanation = explain_comparison(case)
    elif case.get("response_type") == "detail_table":
        explanation = explain_detail(case)
    else:
        explanation = explain_group_or_topn(case)

    return {
        "question": case["question"],
        "query_type": case["query_type"],
        "status": case["status"],
        "response_type": case.get("response_type", "-"),
        "business_answer": explanation["business_answer"],
        "key_findings": explanation["key_findings"],
        "risk_notes": explanation["risk_notes"],
        "follow_up_questions": explanation["follow_up_questions"],
    }


def summarize(results: list[dict]) -> dict:
    """汇总解释结果。"""

    return {
        "total": len(results),
        "interpreted": sum(1 for item in results if item["status"] == "executed"),
        "safe_explanations": sum(1 for item in results if item["status"] != "executed"),
    }


def write_report(payload: dict) -> None:
    """输出 Markdown 报告，方便直接阅读解释效果。"""

    lines = [
        "# Day 34 - NL2SQL 结果解释报告",
        "",
        "## 总览",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 解释明细",
            "",
            "| question | status | response_type | business_answer |",
            "|----------|--------|---------------|-----------------|",
        ]
    )
    for item in payload["results"]:
        answer = item["business_answer"].replace("|", "｜")
        lines.append(f"| {item['question']} | {item['status']} | {item['response_type']} | {answer} |")

    lines.extend(["", "## 业务解释样例", ""])
    for index, item in enumerate(payload["results"], start=1):
        lines.append(f"### {index}. {item['question']}")
        lines.append("")
        lines.append(item["business_answer"])
        lines.append("")
        lines.append("关键发现：")
        for finding in item["key_findings"]:
            lines.append(f"- {finding}")
        lines.append("")
        lines.append("风险提示：")
        for note in item["risk_notes"]:
            lines.append(f"- {note}")
        lines.append("")
        lines.append("建议追问：")
        for question in item["follow_up_questions"]:
            lines.append(f"- {question}")
        lines.append("")

    lines.extend(
        [
            "## 结论",
            "",
            "Day 34 的重点是把查询结果从“数据库返回的行列”转成“业务可理解的解释”。",
            "结果解释层必须忠于查询结果，不能编造未查询到的原因或结论；",
            "对被阻断的查询，要明确说明是安全拦截，而不是数据库没有数据。",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 34 结果解释流程。"""

    execution_payload = load_json(EXECUTION_RESULT_PATH)
    results = [interpret_case(item) for item in execution_payload["results"]]
    payload = {"summary": summarize(results), "results": results}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"结果文件: {RESULT_PATH}")
    print(f"报告文件: {REPORT_PATH}")


if __name__ == "__main__":
    main()
