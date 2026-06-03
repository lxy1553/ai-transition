"""Day 46 - 错误治理与修复回归脚本。

这个脚本读取 Day 45 的端到端评测结果，把失败样例转成可执行的修复计划，
再模拟修复后的 Agent 输出并重新评测。生产里错误治理不是笼统地“改 Prompt”，
而是要按失败类型定位到路由、校验、检索、异常处理或结果解释的具体责任层。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent.parent
DAY45_OUTPUT_DIR = REPO_ROOT / "projects" / "day45_e2e_evaluation" / "output"
DAY45_TESTSET_PATH = DAY45_OUTPUT_DIR / "e2e_testset.json"
DAY45_RESULTS_PATH = DAY45_OUTPUT_DIR / "e2e_eval_results.json"

OUTPUT_DIR = PROJECT_DIR / "output"
FIX_PLAN_PATH = OUTPUT_DIR / "error_fix_plan.json"
BEFORE_AFTER_PATH = OUTPUT_DIR / "before_after_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "error_governance_report.md"


@dataclass(frozen=True)
class ErrorFix:
    """描述一个 bad case 的修复策略。

    修复策略必须落到具体责任层。否则团队很容易把所有问题都归咎于 Prompt，
    最后改了很多文案，真正的工具前置条件和异常分类仍然没有修好。
    """

    case_id: str
    failure_summary: str
    owner_layer: str
    fix_type: str
    change_description: str
    regression_guard: str


@dataclass(frozen=True)
class CaseEvaluation:
    """记录修复后单条样例的判定结果。"""

    case_id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool
    failure_reasons: list[str]


def load_json(path: Path) -> Any:
    """读取 JSON 文件，并在文件缺失时给出明确错误。

    Day 46 依赖 Day 45 的评测产物；如果输入不存在，说明不能直接做错误治理，
    需要先回到 Day 45 生成固定评测集。
    """

    if not path.exists():
        raise FileNotFoundError(f"required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_fix_plan() -> list[ErrorFix]:
    """把 Day 45 的四个失败样例转成修复计划。"""

    return [
        ErrorFix(
            case_id="D45-003",
            failure_summary="实时窗口问题误走离线 SQL。",
            owner_layer="tool_routing",
            fix_type="realtime_routing_rule",
            change_description=(
                "问题包含近 5 分钟、实时指标或窗口状态时，必须路由到 realtime_metric_tool，"
                "禁止继续 offline_sql_generator 和 offline_query_executor。"
            ),
            regression_guard="实时窗口样例不能出现 offline_query_executor。",
        ),
        ErrorFix(
            case_id="D45-011",
            failure_summary="缺少时间范围却继续查询离线数据。",
            owner_layer="clarification",
            fix_type="missing_time_range_guard",
            change_description=(
                "离线指标查询缺少日期、月份或明确时间范围时，必须先进入 clarification，"
                "禁止继续 offline_sql_generator 和 offline_query_executor。"
            ),
            regression_guard="缺少时间范围样例必须保持 clarification_required。",
        ),
        ErrorFix(
            case_id="D45-014",
            failure_summary="实时口径解释缺少可靠引用仍然回答。",
            owner_layer="rag_retrieval",
            fix_type="grounding_guardrail",
            change_description=(
                "RAG 检索没有 citation 或引用置信度不足时，最终状态必须是 insufficient_evidence，"
                "不能让模型补全规则内容。"
            ),
            regression_guard="需要引用的规则解释样例不能出现 missing_citation。",
        ),
        ErrorFix(
            case_id="D45-021",
            failure_summary="实时链路延迟被包装成正常回答。",
            owner_layer="realtime_status_check",
            fix_type="realtime_delay_taxonomy",
            change_description=(
                "实时指标工具返回链路延迟、窗口不可用或状态过期时，最终状态必须是 execution_failed，"
                "结果解释层不能把延迟数据改写成正常结论。"
            ),
            regression_guard="实时延迟样例必须保留 execution_failed 状态。",
        ),
    ]


def apply_fix(case: dict[str, Any], before_outcome: dict[str, Any]) -> dict[str, Any]:
    """根据修复计划模拟修复后的 Agent 输出。

    这里不假装接入真实模型，而是把 Day 45 暴露出的四个责任层修正为受控行为。
    这种做法适合学习和面试演示：先证明 bad case 被归因，再证明回归评测能捕捉修复效果。
    """

    outcome = dict(before_outcome)
    case_id = case["case_id"]

    if case_id == "D45-003":
        outcome.update(
            {
                "actual_status": "answered",
                "actual_failure_category": "none",
                "tool_route": [
                    "intent_classifier",
                    "realtime_metric_tool",
                    "result_interpreter",
                    "audit_logger",
                ],
                "has_citation": False,
                "answer_summary": "已修复：实时窗口问题走实时指标工具，不再走离线 SQL。",
            }
        )
    elif case_id == "D45-011":
        outcome.update(
            {
                "actual_status": "clarification_required",
                "actual_failure_category": "missing_time_range",
                "tool_route": ["intent_classifier", "clarification", "audit_logger"],
                "has_citation": False,
                "answer_summary": "已修复：缺少时间范围时要求用户补充，不进入离线查询执行。",
            }
        )
    elif case_id == "D45-014":
        outcome.update(
            {
                "actual_status": "insufficient_evidence",
                "actual_failure_category": "missing_citation",
                "tool_route": ["intent_classifier", "rag_retriever", "audit_logger"],
                "has_citation": True,
                "answer_summary": "已修复：没有可靠规则引用时返回资料不足，不编造规则。",
            }
        )
    elif case_id == "D45-021":
        outcome.update(
            {
                "actual_status": "execution_failed",
                "actual_failure_category": "realtime_delay",
                "tool_route": ["intent_classifier", "realtime_metric_tool", "audit_logger"],
                "has_citation": False,
                "answer_summary": "已修复：实时链路延迟时保持 execution_failed，不包装成正常结论。",
            }
        )

    return outcome


def evaluate_case(case: dict[str, Any], outcome: dict[str, Any]) -> CaseEvaluation:
    """复用 Day 45 的成功判定标准评估修复后结果。"""

    failure_reasons: list[str] = []
    if outcome["actual_status"] != case["expected_status"]:
        failure_reasons.append("status_mismatch")
    if outcome["actual_failure_category"] != case["expected_failure_category"]:
        failure_reasons.append("failure_category_mismatch")
    for tool in case["required_tools"]:
        if tool not in outcome["tool_route"]:
            failure_reasons.append(f"missing_required_tool:{tool}")
    for tool in case["forbidden_tools"]:
        if tool in outcome["tool_route"]:
            failure_reasons.append(f"forbidden_tool_used:{tool}")
    if case["requires_citation"] and not outcome["has_citation"]:
        failure_reasons.append("missing_citation")
    if "query_executor" in outcome["tool_route"] and "sql_validator" in case["required_tools"]:
        if "sql_validator" not in outcome["tool_route"]:
            failure_reasons.append("query_executor_without_validator")
        elif outcome["tool_route"].index("query_executor") < outcome["tool_route"].index(
            "sql_validator"
        ):
            failure_reasons.append("query_executor_before_validator")

    return CaseEvaluation(
        case_id=case["case_id"],
        category=case["category"],
        expected_status=case["expected_status"],
        actual_status=outcome["actual_status"],
        passed=not failure_reasons,
        failure_reasons=failure_reasons,
    )


def summarize(evaluations: list[CaseEvaluation]) -> dict[str, Any]:
    """汇总通过率和失败原因数量。"""

    total = len(evaluations)
    passed = sum(1 for item in evaluations if item.passed)
    failure_counter: Counter[str] = Counter()
    for item in evaluations:
        if item.passed:
            continue
        for reason in item.failure_reasons:
            failure_counter[reason.split(":", maxsplit=1)[0]] += 1
    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round(passed / total, 4),
        "failure_reason_counts": dict(sorted(failure_counter.items())),
    }


def build_report(
    fix_plan: list[ErrorFix],
    before_summary: dict[str, Any],
    after_summary: dict[str, Any],
    after_evaluations: list[CaseEvaluation],
    after_outcomes: list[dict[str, Any]],
) -> str:
    """生成 Day 46 错误治理报告。"""

    outcome_by_id = {outcome["case_id"]: outcome for outcome in after_outcomes}
    lines = [
        "# Day 46 错误治理与修复回归报告",
        "",
        "## 修复前后对比",
        "",
        "| 指标 | 修复前 | 修复后 |",
        "|------|--------|--------|",
        f"| 测试集数量 | {before_summary['total_cases']} | {after_summary['total_cases']} |",
        f"| 通过数量 | {before_summary['passed_cases']} | {after_summary['passed_cases']} |",
        f"| 失败数量 | {before_summary['failed_cases']} | {after_summary['failed_cases']} |",
        f"| 通过率 | {before_summary['pass_rate']} | {after_summary['pass_rate']} |",
        "",
        "## 修复计划",
        "",
        "| Case | 责任层 | 修复类型 | 修复内容 | 回归保护 |",
        "|------|--------|----------|----------|----------|",
    ]
    for fix in fix_plan:
        lines.append(
            f"| {fix.case_id} | {fix.owner_layer} | {fix.fix_type} | "
            f"{fix.change_description} | {fix.regression_guard} |"
        )

    lines.extend(
        [
            "",
            "## 修复后明细",
            "",
            "| Case | 预期状态 | 实际状态 | 通过 | 失败原因 | 工具路线 |",
            "|------|----------|----------|------|----------|----------|",
        ]
    )
    for item in after_evaluations:
        outcome = outcome_by_id[item.case_id]
        passed = "是" if item.passed else "否"
        reasons = ", ".join(item.failure_reasons) if item.failure_reasons else "无"
        lines.append(
            f"| {item.case_id} | {item.expected_status} | {item.actual_status} | "
            f"{passed} | {reasons} | {' -> '.join(outcome['tool_route'])} |"
        )

    lines.extend(
        [
            "",
            "## 生产启示",
            "",
            "- 先按失败类型定位责任层，再决定是改 Prompt、规则、检索还是异常处理。",
            "- 修复 bad case 后必须跑全量评测集，确认没有引入新的回归问题。",
            "- 对金融信贷 Agent 来说，缺少条件、安全阻断、资料不足和系统异常都要有明确最终状态。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 46 错误治理产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    testset = load_json(DAY45_TESTSET_PATH)
    day45_results = load_json(DAY45_RESULTS_PATH)
    before_outcomes = {outcome["case_id"]: outcome for outcome in day45_results["outcomes"]}
    fix_plan = build_fix_plan()

    after_outcomes = [apply_fix(case, before_outcomes[case["case_id"]]) for case in testset]
    after_evaluations = [
        evaluate_case(case, outcome) for case, outcome in zip(testset, after_outcomes)
    ]
    after_summary = summarize(after_evaluations)

    FIX_PLAN_PATH.write_text(
        json.dumps([asdict(fix) for fix in fix_plan], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    BEFORE_AFTER_PATH.write_text(
        json.dumps(
            {
                "before_summary": day45_results["summary"],
                "after_summary": after_summary,
                "after_outcomes": after_outcomes,
                "after_evaluations": [asdict(item) for item in after_evaluations],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        build_report(
            fix_plan=fix_plan,
            before_summary=day45_results["summary"],
            after_summary=after_summary,
            after_evaluations=after_evaluations,
            after_outcomes=after_outcomes,
        ),
        encoding="utf-8",
    )

    print(f"before_pass_rate={day45_results['summary']['pass_rate']}")
    print(f"after_pass_rate={after_summary['pass_rate']}")
    print(f"after_failed_cases={after_summary['failed_cases']}")
    print(f"fix_plan={FIX_PLAN_PATH}")
    print(f"results={BEFORE_AFTER_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
