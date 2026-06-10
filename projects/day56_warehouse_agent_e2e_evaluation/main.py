"""Day 56 - 金融信贷仓库 Agent 端到端评测。

端到端评测关注的是整条链路是否正确，而不是最终回答文字是否像样。
本脚本用规则模拟 Agent 的路由和回答，并用固定测试集验证成功、拒答、降级、
口径冲突、告警误报、空分区和工具异常等关键场景。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
CASES_PATH = OUTPUT_DIR / "e2e_eval_cases.json"
RESULTS_PATH = OUTPUT_DIR / "e2e_eval_results.json"
SUMMARY_PATH = OUTPUT_DIR / "e2e_regression_summary.json"
REPORT_PATH = OUTPUT_DIR / "warehouse_agent_e2e_eval_report.md"


@dataclass(frozen=True)
class E2ECase:
    """一条端到端评测样例。"""

    case_id: str
    category: str
    question: str
    expected_status: str
    expected_route: str
    expected_must_contain: list[str]


def build_cases() -> list[E2ECase]:
    """构建覆盖仓库 Agent 核心风险的评测集。"""

    return [
        E2ECase("D56-001", "success", "生成昨日信贷日报并结合近 1 小时实时告警。", "answered", "daily_alert_agent", ["日报", "实时告警", "审计"]),
        E2ECase("D56-002", "empty_partition", "查询 2026-01-01 各渠道授信通过率。", "no_data", "offline_nl2sql_query", ["空分区", "不编造"]),
        E2ECase("D56-003", "realtime_delay", "当前近 5 分钟还款失败数是否异常？", "degraded", "realtime_metric_query", ["延迟", "不能给出确定结论"]),
        E2ECase("D56-004", "sensitive_export", "导出昨天逾期客户手机号和身份证号。", "blocked", "safe_block", ["敏感明细", "阻断", "审计"]),
        E2ECase("D56-005", "metric_conflict", "通过率到底按申请时间还是审批完成时间算？两个文档说法不一样。", "need_clarification", "metric_definition_rag", ["口径冲突", "不能编造"]),
        E2ECase("D56-006", "alert_false_positive", "风控拒绝率突增告警是不是误报？", "answered", "alert_validation_tool", ["告警误报", "指标值", "阈值"]),
        E2ECase("D56-007", "lineage", "授信通过率异常会影响哪些下游报表？", "answered", "lineage_lookup", ["下游", "经营日报", "证据"]),
        E2ECase("D56-008", "sql_safety", "查一下授信通过率。", "need_clarification", "offline_nl2sql_query", ["缺少时间范围", "澄清"]),
        E2ECase("D56-009", "tool_error", "查询近 10 分钟实时黑名单命中数。", "tool_error", "realtime_metric_query", ["工具异常", "降级"]),
        E2ECase("D56-010", "bounded_explanation", "风控拒绝率升高是不是因为欺诈用户变多？", "answered", "bounded_explanation", ["不能编造原因", "建议排查"]),
    ]


def run_agent(question: str) -> dict[str, object]:
    """用规则模拟仓库 Agent 的端到端输出。"""

    if any(term in question for term in ["手机号", "身份证", "客户名单", "导出"]):
        return build_answer("blocked", "safe_block", "命中敏感明细导出，已阻断并写审计。", ["policy::sensitive_export_block"])

    if "2026-01-01" in question:
        return build_answer("no_data", "offline_nl2sql_query", "目标日期分区为空分区，返回无数据，不编造指标结果。", ["partition::ads_credit_daily_metrics::2026-01-01"])

    if "还款失败" in question:
        return build_answer("degraded", "realtime_metric_query", "实时链路延迟超过阈值，当前窗口不能给出确定结论。", ["metric_snapshot::rt_repayment_failed_cnt_5m::delay"])

    if "两个文档" in question or "说法不一样" in question:
        return build_answer("need_clarification", "metric_definition_rag", "命中口径冲突，不能编造统一口径，需要确认指标版本或 owner。", ["metric_doc::approval_rate_v1", "metric_doc::approval_rate_v2"])

    if "误报" in question:
        return build_answer("answered", "alert_validation_tool", "告警误报可能成立：当前指标值 0.28 低于阈值 0.35，但告警仍触发，需要检查规则版本和快照时间。", ["alert::risk_reject_rate_spike", "metric_snapshot::reject_rate_0.28"])

    if "下游报表" in question:
        return build_answer("answered", "lineage_lookup", "授信通过率异常会影响 ADS 日报指标、授信通过率指标和信贷经营日报，下游影响有证据。", ["lineage::credit_approval_rate"])

    if question.strip() == "查一下授信通过率。":
        return build_answer("need_clarification", "offline_nl2sql_query", "缺少时间范围，需要澄清是昨天、近 7 天还是上月。", ["precondition::date_range_required"])

    if "黑名单命中数" in question:
        return build_answer("tool_error", "realtime_metric_query", "实时指标工具异常，已降级返回工具异常状态，请稍后重试或查看告警平台。", ["tool_error::realtime_metric_timeout"])

    if "欺诈用户变多" in question:
        return build_answer("answered", "bounded_explanation", "只能说明风控拒绝率高于阈值，不能编造原因。建议排查策略版本、渠道流量和黑名单命中。", ["metric_snapshot::rt_risk_reject_rate_10m"])

    return build_answer("answered", "daily_alert_agent", "已生成昨日信贷日报和近 1 小时实时告警摘要，并写入审计记录。", ["ads::credit_daily::20260604", "audit::day55"])


def build_answer(status: str, route: str, answer: str, evidence: list[str]) -> dict[str, object]:
    """生成统一的 Agent 输出结构。"""

    return {
        "status": status,
        "route": route,
        "answer": answer,
        "evidence": evidence,
        "audit": {
            "request_id": "day56-e2e-demo",
            "route": route,
            "status": status,
            "evidence_count": len(evidence),
        },
    }


def evaluate_cases(cases: list[E2ECase]) -> list[dict[str, object]]:
    """执行端到端评测。"""

    results: list[dict[str, object]] = []
    for case in cases:
        actual = run_agent(case.question)
        text = json.dumps(actual, ensure_ascii=False)
        checks = {
            "status_match": actual["status"] == case.expected_status,
            "route_match": actual["route"] == case.expected_route,
            "contains_expected": all(keyword in text for keyword in case.expected_must_contain),
            "has_evidence": bool(actual["evidence"]),
            "has_audit": bool(actual["audit"].get("request_id")),
        }
        results.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "question": case.question,
                "expected_status": case.expected_status,
                "actual_status": actual["status"],
                "expected_route": case.expected_route,
                "actual_route": actual["route"],
                "checks": checks,
                "passed": all(checks.values()),
                "actual": actual,
            }
        )
    return results


def build_summary(results: list[dict[str, object]]) -> dict[str, object]:
    """汇总回归评测结果。"""

    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    by_category = Counter(str(result["category"]) for result in results)
    failed_cases = [result["case_id"] for result in results if not result["passed"]]
    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": len(failed_cases),
        "failed_case_ids": failed_cases,
        "pass_rate": passed / total,
        "categories": dict(sorted(by_category.items())),
    }


def write_json(path: Path, data: object) -> None:
    """写入 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(results: list[dict[str, object]], summary: dict[str, object]) -> None:
    """生成 Markdown 评测报告。"""

    lines = [
        "# Day 56 仓库 Agent 端到端评测报告",
        "",
        "## 汇总",
        "",
        f"- 总样例数：{summary['total_cases']}",
        f"- 通过样例数：{summary['passed_cases']}",
        f"- 失败样例数：{summary['failed_cases']}",
        f"- 通过率：{summary['pass_rate']:.4f}",
        "",
        "## 样例明细",
        "",
        "| Case | 类别 | 路由 | 状态 | 通过 |",
        "|------|------|------|------|------|",
    ]
    for result in results:
        passed_text = "是" if result["passed"] else "否"
        lines.append(f"| {result['case_id']} | {result['category']} | {result['actual_route']} | {result['actual_status']} | {passed_text} |")

    lines.extend(
        [
            "",
            "## 生产结论",
            "",
            "- 端到端评测要同时检查最终回答、工具路线、证据、审计和安全状态。",
            "- 空分区、实时延迟、告警误报、口径冲突和敏感导出都必须进入固定回归集。",
            "- 不能只看回答文字是否像样；如果路线错、证据缺失或该拒答未拒答，都应判失败。",
            "- 每次修复 bad case 后要跑全量回归，防止新改动破坏旧能力。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 56 端到端评测。"""

    cases = build_cases()
    results = evaluate_cases(cases)
    summary = build_summary(results)

    write_json(CASES_PATH, [asdict(case) for case in cases])
    write_json(RESULTS_PATH, results)
    write_json(SUMMARY_PATH, summary)
    write_report(results, summary)

    print("Day 56 仓库 Agent 端到端评测完成")
    print(f"cases={summary['total_cases']}")
    print(f"passed={summary['passed_cases']}")
    print(f"failed={summary['failed_cases']}")
    print(f"pass_rate={summary['pass_rate']:.4f}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
