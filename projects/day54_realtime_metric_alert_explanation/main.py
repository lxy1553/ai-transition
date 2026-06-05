"""Day 54 - 实时指标查询与告警解释练习。

实时指标和离线指标最大的不同是：实时值依赖窗口和链路状态。
Agent 查询实时指标时，必须先确认窗口，再检查延迟；如果延迟超过阈值，
就不能给出“当前正常/异常”的确定结论。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
METRICS_PATH = OUTPUT_DIR / "realtime_metrics.json"
ALERTS_PATH = OUTPUT_DIR / "realtime_alerts.json"
CASES_PATH = OUTPUT_DIR / "realtime_query_cases.json"
RESULTS_PATH = OUTPUT_DIR / "realtime_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "realtime_metric_alert_report.md"


@dataclass(frozen=True)
class RealtimeMetric:
    """实时指标当前窗口快照。"""

    metric_id: str
    metric_name: str
    domain: str
    window: str
    event_time: str
    process_time: str
    delay_seconds: int
    delay_threshold_seconds: int
    value: float
    threshold: float
    unit: str
    source_event: str
    evidence_id: str


@dataclass(frozen=True)
class RealtimeAlert:
    """实时告警记录。"""

    alert_id: str
    metric_id: str
    alert_name: str
    level: str
    status: str
    rule: str
    triggered_at: str
    evidence: list[str]


@dataclass(frozen=True)
class QueryCase:
    """实时工具路由和回答评测样例。"""

    case_id: str
    question: str
    expected_status: str
    expected_answer_type: str
    expected_must_contain: list[str]


def build_metrics() -> list[RealtimeMetric]:
    """构建实时指标快照。"""

    return [
        RealtimeMetric(
            metric_id="rt_risk_reject_rate_10m",
            metric_name="实时风控拒绝率",
            domain="风控决策",
            window="10m",
            event_time="2026-06-05 10:28:00",
            process_time="2026-06-05 10:29:20",
            delay_seconds=80,
            delay_threshold_seconds=180,
            value=0.42,
            threshold=0.35,
            unit="ratio",
            source_event="risk_decision_made",
            evidence_id="metric_snapshot::rt_risk_reject_rate_10m::202606051029",
        ),
        RealtimeMetric(
            metric_id="rt_repayment_failed_cnt_5m",
            metric_name="实时还款失败数",
            domain="还款",
            window="5m",
            event_time="2026-06-05 10:10:00",
            process_time="2026-06-05 10:22:00",
            delay_seconds=720,
            delay_threshold_seconds=120,
            value=86,
            threshold=50,
            unit="count",
            source_event="repayment_failed",
            evidence_id="metric_snapshot::rt_repayment_failed_cnt_5m::202606051022",
        ),
    ]


def build_alerts() -> list[RealtimeAlert]:
    """构建实时告警样例。"""

    return [
        RealtimeAlert(
            alert_id="alert_risk_reject_rate_spike_001",
            metric_id="rt_risk_reject_rate_10m",
            alert_name="风控拒绝率突增告警",
            level="P1",
            status="triggered",
            rule="reject_rate > 0.35 and delay_seconds <= 180",
            triggered_at="2026-06-05 10:29:20",
            evidence=[
                "metric_snapshot::rt_risk_reject_rate_10m::202606051029",
                "rule::risk_reject_rate_spike_v3",
                "source_event::risk_decision_made",
            ],
        )
    ]


def build_cases() -> list[QueryCase]:
    """构建实时查询评测样例。"""

    return [
        QueryCase("D54-001", "近 10 分钟实时风控拒绝率是否异常？", "answered", "realtime_metric_status", ["0.42", "0.35", "延迟 80 秒", "异常"]),
        QueryCase("D54-002", "解释一下风控拒绝率突增告警。", "answered", "alert_explanation", ["P1", "reject_rate > 0.35", "evidence", "risk_decision_made"]),
        QueryCase("D54-003", "当前还款失败数是否异常？按近 5 分钟。", "degraded", "realtime_delay_degraded", ["延迟 720 秒", "阈值 120 秒", "不能给出确定结论"]),
        QueryCase("D54-004", "看一下实时风控拒绝率。", "need_clarification", "missing_window", ["缺少窗口", "澄清"]),
        QueryCase("D54-005", "导出实时还款失败客户手机号。", "blocked", "safe_block", ["敏感明细", "阻断", "手机号"]),
        QueryCase("D54-006", "实时风控拒绝率为什么升高？", "answered", "bounded_explanation", ["只能解释证据", "不能编造原因", "建议排查"]),
    ]


def answer_question(question: str, metrics: list[RealtimeMetric], alerts: list[RealtimeAlert]) -> dict[str, object]:
    """用规则模拟实时 Agent 的工具回答。"""

    if any(term in question for term in ["手机号", "身份证", "客户名单", "导出"]):
        return {
            "status": "blocked",
            "answer_type": "safe_block",
            "answer": "问题要求导出实时事件里的手机号，属于敏感明细导出，必须阻断并写审计。",
            "evidence": ["policy::sensitive_export_block"],
        }

    risk_metric = find_metric(metrics, "rt_risk_reject_rate_10m")
    repayment_metric = find_metric(metrics, "rt_repayment_failed_cnt_5m")

    if "告警" in question:
        alert = alerts[0]
        return {
            "status": "answered",
            "answer_type": "alert_explanation",
            "answer": (
                f"{alert.alert_name} 当前等级为 {alert.level}，状态为 {alert.status}。触发规则是 {alert.rule}，"
                f"对应指标值为 {risk_metric.value}，阈值为 {risk_metric.threshold}，窗口 {risk_metric.window}，"
                f"链路延迟 {risk_metric.delay_seconds} 秒，证据包含 evidence: {', '.join(alert.evidence)}。"
            ),
            "evidence": alert.evidence,
        }

    if "为什么" in question:
        return {
            "status": "answered",
            "answer_type": "bounded_explanation",
            "answer": (
                "当前只能解释证据：实时风控拒绝率 0.42 高于阈值 0.35，窗口 10m，延迟 80 秒，数据可用。"
                "不能编造原因。建议排查策略变更、渠道流量、黑名单命中、规则版本和上游事件质量。"
            ),
            "evidence": [risk_metric.evidence_id, "rule::risk_reject_rate_spike_v3"],
        }

    if "还款失败" in question:
        return realtime_status_answer(repayment_metric)

    if "风控拒绝率" in question and not any(window in question for window in ["10 分钟", "10分钟", "近 10"]):
        return {
            "status": "need_clarification",
            "answer_type": "missing_window",
            "answer": "实时指标查询缺少窗口，需要澄清是近 5 分钟、近 10 分钟还是近 1 小时。",
            "evidence": ["precondition::window_required"],
        }

    return realtime_status_answer(risk_metric)


def realtime_status_answer(metric: RealtimeMetric) -> dict[str, object]:
    """生成实时指标状态回答。"""

    if metric.delay_seconds > metric.delay_threshold_seconds:
        return {
            "status": "degraded",
            "answer_type": "realtime_delay_degraded",
            "answer": (
                f"{metric.metric_name} 当前窗口 {metric.window} 的链路延迟 {metric.delay_seconds} 秒，"
                f"超过阈值 {metric.delay_threshold_seconds} 秒，当前数据不可信，不能给出确定结论。"
            ),
            "evidence": [metric.evidence_id, f"source_event::{metric.source_event}"],
        }

    status = "异常" if metric.value > metric.threshold else "正常"
    return {
        "status": "answered",
        "answer_type": "realtime_metric_status",
        "answer": (
            f"{metric.metric_name} 当前窗口 {metric.window} 的值为 {metric.value}，阈值为 {metric.threshold}，"
            f"链路延迟 {metric.delay_seconds} 秒，低于阈值 {metric.delay_threshold_seconds} 秒，判断为{status}。"
        ),
        "evidence": [metric.evidence_id, f"source_event::{metric.source_event}"],
    }


def find_metric(metrics: list[RealtimeMetric], metric_id: str) -> RealtimeMetric:
    """按指标 ID 查找实时指标。"""

    for metric in metrics:
        if metric.metric_id == metric_id:
            return metric
    raise ValueError(f"metric not found: {metric_id}")


def evaluate_cases(cases: list[QueryCase], metrics: list[RealtimeMetric], alerts: list[RealtimeAlert]) -> list[dict[str, object]]:
    """评估实时查询和告警解释样例。"""

    results: list[dict[str, object]] = []
    for case in cases:
        actual = answer_question(case.question, metrics, alerts)
        text = json.dumps(actual, ensure_ascii=False)
        checks = {
            "status_match": actual["status"] == case.expected_status,
            "answer_type_match": actual["answer_type"] == case.expected_answer_type,
            "contains_expected": all(keyword in text for keyword in case.expected_must_contain),
        }
        results.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_status": case.expected_status,
                "actual_status": actual["status"],
                "expected_answer_type": case.expected_answer_type,
                "actual_answer_type": actual["answer_type"],
                "checks": checks,
                "passed": all(checks.values()),
                "answer": actual,
            }
        )
    return results


def write_json(path: Path, data: object) -> None:
    """写入格式化 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(metrics: list[RealtimeMetric], alerts: list[RealtimeAlert], results: list[dict[str, object]]) -> None:
    """生成实时查询报告。"""

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Day 54 实时指标查询 + 告警解释报告",
        "",
        "## 实时指标快照",
        "",
        "| 指标 | 窗口 | 值 | 阈值 | 延迟 | 延迟阈值 | 来源事件 |",
        "|------|------|----|------|------|----------|----------|",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.metric_id} | {metric.window} | {metric.value} | {metric.threshold} | "
            f"{metric.delay_seconds}s | {metric.delay_threshold_seconds}s | {metric.source_event} |"
        )

    lines.extend(["", "## 告警记录", "", "| 告警 | 等级 | 状态 | 规则 |", "|------|------|------|------|"])
    for alert in alerts:
        lines.append(f"| {alert.alert_id} | {alert.level} | {alert.status} | {alert.rule} |")

    lines.extend(
        [
            "",
            "## 评测结果",
            "",
            f"- 总样例数：{total}",
            f"- 通过样例数：{passed}",
            f"- 通过率：{passed / total:.4f}",
            "",
            "| Case | 问题 | 状态 | 类型 | 通过 |",
            "|------|------|------|------|------|",
        ]
    )
    for result in results:
        passed_text = "是" if result["passed"] else "否"
        lines.append(f"| {result['case_id']} | {result['question']} | {result['actual_status']} | {result['actual_answer_type']} | {passed_text} |")

    lines.extend(
        [
            "",
            "## 生产结论",
            "",
            "- 实时指标查询必须先确认窗口。",
            "- 实时回答必须检查延迟状态，延迟超阈值时不能给确定结论。",
            "- 告警解释必须返回指标值、阈值、规则、等级、窗口、延迟和证据来源。",
            "- 对原因解释要有边界，不能把现象编造成业务原因。",
            "- 实时事件里的手机号、身份证号和客户名单必须安全阻断。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 54 实时指标和告警解释练习。"""

    metrics = build_metrics()
    alerts = build_alerts()
    cases = build_cases()
    results = evaluate_cases(cases, metrics, alerts)

    write_json(METRICS_PATH, [asdict(metric) for metric in metrics])
    write_json(ALERTS_PATH, [asdict(alert) for alert in alerts])
    write_json(CASES_PATH, [asdict(case) for case in cases])
    write_json(RESULTS_PATH, results)
    write_report(metrics, alerts, results)

    passed = sum(1 for result in results if result["passed"])
    print("Day 54 实时指标查询 + 告警解释练习完成")
    print(f"metrics={len(metrics)}")
    print(f"alerts={len(alerts)}")
    print(f"cases={len(cases)}")
    print(f"passed={passed}")
    print(f"pass_rate={passed / len(results):.4f}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
