"""Day 35 - NL2SQL 助手整合演示。

这个脚本把 Day 30-34 的产物串成一个端到端演示入口：
问题解析 -> SQL 生成 -> SQL 校验 -> 查询执行 -> 结果解释。
生产项目里这些步骤通常会拆成服务、队列或工具调用；本地 Day 35 先用稳定的
JSON 契约把链路打通，方便面试演示和后续服务化重构。
"""

import argparse
import json
from pathlib import Path
from typing import Any, Optional


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]

PARSE_RESULT_PATH = ROOT_DIR / "projects/day30_nl2sql_question_parser/output/question_parse_results.json"
GENERATION_RESULT_PATH = ROOT_DIR / "projects/day31_nl2sql_sql_generator/output/sql_generation_results.json"
VALIDATION_RESULT_PATH = ROOT_DIR / "projects/day32_nl2sql_sql_validator/output/sql_validation_results.json"
EXECUTION_RESULT_PATH = ROOT_DIR / "projects/day33_nl2sql_query_executor/output/query_execution_results.json"
INTERPRETATION_RESULT_PATH = (
    ROOT_DIR / "projects/day34_nl2sql_result_interpreter/output/result_interpretation_results.json"
)

OUTPUT_DIR = PROJECT_DIR / "output"
DEMO_RESULT_PATH = OUTPUT_DIR / "nl2sql_assistant_demo_results.json"
DEMO_REPORT_PATH = OUTPUT_DIR / "nl2sql_assistant_demo_report.md"


def load_json(path: Path) -> Any:
    """读取上游阶段产物。

    Day 35 的重点是整合，不重写前面每一天的业务规则。
    这样可以检查不同阶段之间的字段契约是否稳定，也方便后续拆成 API 服务。
    """

    return json.loads(path.read_text(encoding="utf-8"))


def index_by_question(items: list[dict]) -> dict[str, dict]:
    """按问题建立索引，让每个阶段的结果能合并到同一条演示链路。"""

    return {item["question"]: item for item in items}


def parse_items(payload: dict) -> list[dict]:
    """把 Day 30 的评测格式转成统一问题列表。"""

    return [item["parsed"] for item in payload["results"]]


def stage_status(stage_payload: Optional[dict], success_field: Optional[str] = None) -> str:
    """把不同阶段的状态归一成演示可读状态。"""

    if not stage_payload:
        return "missing"
    if success_field is None:
        return "available"
    return "passed" if stage_payload.get(success_field) else "blocked"


def build_case_trace(question: str, indexes: dict[str, dict[str, dict]]) -> dict:
    """合并单个问题在 Day 30-34 的完整链路。"""

    parsed = indexes["parse"].get(question)
    generated = indexes["generation"].get(question)
    validated = indexes["validation"].get(question)
    executed = indexes["execution"].get(question)
    interpreted = indexes["interpretation"].get(question)

    final_status = "answered"
    if interpreted and interpreted.get("status") != "executed":
        final_status = "safely_blocked"
    elif executed and executed.get("status") == "execution_error":
        final_status = "execution_error"
    elif not interpreted:
        final_status = "incomplete"

    return {
        "question": question,
        "final_status": final_status,
        "query_type": (parsed or {}).get("query_type"),
        "pipeline": {
            "parse": stage_status(parsed),
            "sql_generation": stage_status(generated, "can_generate_sql"),
            "sql_validation": stage_status(validated, "can_execute"),
            "query_execution": (executed or {}).get("status", "missing"),
            "result_interpretation": "available" if interpreted else "missing",
        },
        "parsed": {
            "metrics": (parsed or {}).get("metrics", []),
            "dimensions": (parsed or {}).get("dimensions", []),
            "time_range": (parsed or {}).get("time_range"),
            "filters": (parsed or {}).get("filters", {}),
            "risk_flags": (parsed or {}).get("risk_flags", []),
        },
        "sql": (generated or {}).get("sql"),
        "validation": {
            "can_execute": (validated or {}).get("can_execute", False),
            "risk_level": (validated or {}).get("risk_level"),
            "issues": (validated or {}).get("issues", []),
            "warnings": (validated or {}).get("warnings", []),
        },
        "execution": {
            "status": (executed or {}).get("status", "missing"),
            "response_type": (executed or {}).get("response_type", "-"),
            "row_count": (executed or {}).get("row_count", 0),
            "summary_text": (executed or {}).get("summary_text", ""),
        },
        "answer": {
            "business_answer": (interpreted or {}).get("business_answer", "暂无结果解释。"),
            "key_findings": (interpreted or {}).get("key_findings", []),
            "risk_notes": (interpreted or {}).get("risk_notes", []),
            "follow_up_questions": (interpreted or {}).get("follow_up_questions", []),
        },
    }


def build_demo_payload() -> dict:
    """构建完整演示包。

    这里保留被安全阻断的问题，不只展示成功样例。
    面试或生产评审时，安全阻断链路本身也是 NL2SQL 项目的关键能力。
    """

    parse_payload = load_json(PARSE_RESULT_PATH)
    generation_payload = load_json(GENERATION_RESULT_PATH)
    validation_payload = load_json(VALIDATION_RESULT_PATH)
    execution_payload = load_json(EXECUTION_RESULT_PATH)
    interpretation_payload = load_json(INTERPRETATION_RESULT_PATH)

    indexes = {
        "parse": index_by_question(parse_items(parse_payload)),
        "generation": index_by_question(generation_payload["results"]),
        "validation": index_by_question(validation_payload["results"]),
        "execution": index_by_question(execution_payload["results"]),
        "interpretation": index_by_question(interpretation_payload["results"]),
    }

    # 以解释层问题集为主，因为它代表端到端链路最终能展示给用户的样例。
    questions = [item["question"] for item in interpretation_payload["results"]]
    cases = [build_case_trace(question, indexes) for question in questions]

    summary = {
        "total": len(cases),
        "answered": sum(1 for item in cases if item["final_status"] == "answered"),
        "safely_blocked": sum(1 for item in cases if item["final_status"] == "safely_blocked"),
        "execution_errors": sum(1 for item in cases if item["final_status"] == "execution_error"),
        "incomplete": sum(1 for item in cases if item["final_status"] == "incomplete"),
    }
    summary["demo_ready"] = summary["answered"] > 0 and summary["execution_errors"] == 0

    return {
        "summary": summary,
        "cases": cases,
        "source_artifacts": {
            "parse": str(PARSE_RESULT_PATH.relative_to(ROOT_DIR)),
            "sql_generation": str(GENERATION_RESULT_PATH.relative_to(ROOT_DIR)),
            "sql_validation": str(VALIDATION_RESULT_PATH.relative_to(ROOT_DIR)),
            "query_execution": str(EXECUTION_RESULT_PATH.relative_to(ROOT_DIR)),
            "result_interpretation": str(INTERPRETATION_RESULT_PATH.relative_to(ROOT_DIR)),
        },
    }


def find_case(payload: dict, question: str) -> Optional[dict]:
    """按问题查找演示样例，支持精确匹配和简单包含匹配。"""

    normalized = question.strip()
    for item in payload["cases"]:
        if item["question"] == normalized:
            return item
    for item in payload["cases"]:
        if normalized in item["question"] or item["question"] in normalized:
            return item
    return None


def format_case_for_console(case: dict) -> str:
    """把单个演示样例格式化成命令行输出。"""

    lines = [
        f"问题: {case['question']}",
        f"最终状态: {case['final_status']}",
        f"问题类型: {case.get('query_type')}",
        "",
        "链路状态:",
    ]
    for stage, status in case["pipeline"].items():
        lines.append(f"- {stage}: {status}")
    if case.get("sql"):
        lines.extend(["", "SQL:", case["sql"]])
    lines.extend(["", "业务回答:", case["answer"]["business_answer"]])
    if case["answer"]["key_findings"]:
        lines.append("")
        lines.append("关键发现:")
        lines.extend(f"- {item}" for item in case["answer"]["key_findings"])
    if case["answer"]["risk_notes"]:
        lines.append("")
        lines.append("风险提示:")
        lines.extend(f"- {item}" for item in case["answer"]["risk_notes"])
    return "\n".join(lines)


def markdown_list(items: list[str]) -> str:
    """把列表转成 Markdown 单元格内可读文本。"""

    return "<br>".join(items) if items else "-"


def write_report(payload: dict) -> None:
    """生成 Day 35 演示报告，方便面试时按链路讲项目。"""

    lines = [
        "# Day 35 - NL2SQL 助手整合演示报告",
        "",
        "## 总览",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 来源产物",
            "",
        ]
    )
    for stage, path in payload["source_artifacts"].items():
        lines.append(f"- {stage}: `{path}`")

    lines.extend(
        [
            "",
            "## 演示样例",
            "",
            "| question | final_status | pipeline | business_answer |",
            "|----------|--------------|----------|-----------------|",
        ]
    )
    for item in payload["cases"]:
        pipeline = "<br>".join(f"{stage}: {status}" for stage, status in item["pipeline"].items())
        answer = item["answer"]["business_answer"].replace("|", "｜")
        lines.append(f"| {item['question']} | {item['final_status']} | {pipeline} | {answer} |")

    lines.extend(["", "## 重点样例拆解", ""])
    for index, item in enumerate(payload["cases"], start=1):
        lines.append(f"### {index}. {item['question']}")
        lines.append("")
        lines.append(f"- 最终状态：{item['final_status']}")
        lines.append(f"- 执行摘要：{item['execution']['summary_text'] or '-'}")
        lines.append(f"- 业务回答：{item['answer']['business_answer']}")
        lines.append(f"- 关键发现：{markdown_list(item['answer']['key_findings'])}")
        lines.append(f"- 风险提示：{markdown_list(item['answer']['risk_notes'])}")
        lines.append("")
        if item.get("sql"):
            lines.extend(["```sql", item["sql"], "```", ""])

    lines.extend(
        [
            "## 结论",
            "",
            "Day 35 已把 NL2SQL 的主要链路串成一个可演示版本：",
            "自然语言问题先被解析，再生成 SQL、校验 SQL、执行安全查询，最后输出业务解释。",
            "这个版本保留了成功查询和安全阻断两类样例，能说明项目不只是能查数，",
            "还具备 Schema 约束、权限安全、成本控制和结果解释能力。",
        ]
    )
    DEMO_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 NL2SQL 助手整合演示。"""

    parser = argparse.ArgumentParser(description="Day 35 NL2SQL assistant demo")
    parser.add_argument("--question", help="演示单个已收录问题；不传则生成完整报告。")
    args = parser.parse_args()

    payload = build_demo_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)

    if args.question:
        case = find_case(payload, args.question)
        if not case:
            available = "\n".join(f"- {item['question']}" for item in payload["cases"])
            raise SystemExit(f"未找到匹配问题。可用问题：\n{available}")
        print(format_case_for_console(case))
        return

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"结果文件: {DEMO_RESULT_PATH}")
    print(f"报告文件: {DEMO_REPORT_PATH}")


if __name__ == "__main__":
    main()
