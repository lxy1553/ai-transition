"""Day 55 - 日报 + 实时告警 Agent 练习。

这个脚本把 Day 50-54 的能力串起来：指标口径、Schema/Catalog 约束、血缘意识、
离线日报查询和实时告警解释。生产里的 Agent 不是只调用一个工具，而是要把多工具结果
组合成一个可审计、可追溯、边界清楚的业务摘要。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
DAILY_METRICS_PATH = OUTPUT_DIR / "daily_metrics.json"
ALERTS_PATH = OUTPUT_DIR / "realtime_alerts.json"
AUDIT_LOG_PATH = OUTPUT_DIR / "agent_audit_log.jsonl"
RESULT_PATH = OUTPUT_DIR / "daily_alert_agent_result.json"
REPORT_PATH = OUTPUT_DIR / "daily_alert_agent_report.md"


@dataclass(frozen=True)
class DailyMetric:
    """离线日报指标。"""

    biz_date: str
    metric_id: str
    metric_name: str
    value: float
    unit: str
    wow_change: float
    source_table: str
    partition_field: str
    evidence_id: str


@dataclass(frozen=True)
class RealtimeAlert:
    """近 1 小时实时告警。"""

    alert_id: str
    alert_name: str
    level: str
    status: str
    metric_id: str
    window: str
    metric_value: float
    threshold: float
    delay_seconds: int
    delay_threshold_seconds: int
    triggered_at: str
    evidence: list[str]


@dataclass(frozen=True)
class MetricDefinition:
    """日报摘要中引用的指标口径。"""

    metric_id: str
    definition: str
    numerator: str
    denominator: str
    time_scope: str
    citation: str


def build_daily_metrics() -> list[DailyMetric]:
    """构建昨日离线日报指标。"""

    return [
        DailyMetric("2026-06-04", "credit_apply_cnt_1d", "授信申请量", 18600, "count", 0.08, "ads_credit_daily_metrics", "biz_date", "ads::credit_daily::20260604::apply_cnt"),
        DailyMetric("2026-06-04", "credit_approval_rate_1d", "授信通过率", 0.638, "ratio", -0.032, "ads_credit_daily_metrics", "biz_date", "ads::credit_daily::20260604::approval_rate"),
        DailyMetric("2026-06-04", "loan_amount_1d", "放款金额", 52800000, "amount", 0.041, "ads_credit_daily_metrics", "biz_date", "ads::credit_daily::20260604::loan_amount"),
        DailyMetric("2026-06-04", "m1_overdue_rate_1d", "M1 逾期率", 0.027, "ratio", 0.004, "ads_postloan_daily_metrics", "biz_date", "ads::postloan_daily::20260604::m1_overdue_rate"),
    ]


def build_realtime_alerts() -> list[RealtimeAlert]:
    """构建近 1 小时实时告警。"""

    return [
        RealtimeAlert(
            alert_id="alert_risk_reject_rate_spike_202606051030",
            alert_name="风控拒绝率突增告警",
            level="P1",
            status="triggered",
            metric_id="rt_risk_reject_rate_10m",
            window="10m",
            metric_value=0.42,
            threshold=0.35,
            delay_seconds=80,
            delay_threshold_seconds=180,
            triggered_at="2026-06-05 10:30:00",
            evidence=["metric_snapshot::rt_risk_reject_rate_10m::202606051030", "rule::risk_reject_rate_spike_v3"],
        ),
        RealtimeAlert(
            alert_id="alert_repayment_failed_delay_202606051015",
            alert_name="还款失败实时链路延迟告警",
            level="P2",
            status="degraded",
            metric_id="rt_repayment_failed_cnt_5m",
            window="5m",
            metric_value=86,
            threshold=50,
            delay_seconds=720,
            delay_threshold_seconds=120,
            triggered_at="2026-06-05 10:15:00",
            evidence=["metric_snapshot::rt_repayment_failed_cnt_5m::202606051015", "rule::realtime_delay_guard_v2"],
        ),
    ]


def build_metric_definitions() -> dict[str, MetricDefinition]:
    """构建摘要会引用的指标口径。"""

    definitions = [
        MetricDefinition(
            metric_id="credit_approval_rate_1d",
            definition="授信通过率表示审批通过申请数占授信申请总数的比例。",
            numerator="approved_cnt",
            denominator="apply_cnt",
            time_scope="离线 T+1 日分区，按 biz_date 统计。",
            citation="metric_dictionary::credit_approval_rate_1d",
        ),
        MetricDefinition(
            metric_id="m1_overdue_rate_1d",
            definition="M1 逾期率表示到期贷款中逾期天数大于等于 30 天的占比。",
            numerator="m1_overdue_cnt",
            denominator="due_loan_cnt",
            time_scope="离线 T+1 日分区，按贷后统计日统计。",
            citation="metric_dictionary::m1_overdue_rate_1d",
        ),
    ]
    return {definition.metric_id: definition for definition in definitions}


def write_audit(step: str, tool: str, status: str, detail: dict[str, object]) -> None:
    """写审计日志。"""

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "request_id": "day55-demo-request",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "step": step,
        "tool": tool,
        "status": status,
        "detail": detail,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def query_daily_metrics(metrics: list[DailyMetric]) -> list[DailyMetric]:
    """模拟离线日报查询工具。"""

    write_audit(
        "query_daily_metrics",
        "offline_daily_metric_tool",
        "success",
        {"source_tables": sorted({metric.source_table for metric in metrics}), "partition": "biz_date=2026-06-04"},
    )
    return metrics


def query_realtime_alerts(alerts: list[RealtimeAlert]) -> list[RealtimeAlert]:
    """模拟近 1 小时实时告警查询工具。"""

    write_audit(
        "query_realtime_alerts",
        "realtime_alert_tool",
        "success",
        {"window": "last_1h", "alert_count": len(alerts), "levels": sorted({alert.level for alert in alerts})},
    )
    return alerts


def lookup_metric_definitions(definitions: dict[str, MetricDefinition], metric_ids: list[str]) -> list[MetricDefinition]:
    """模拟指标口径查询工具。"""

    selected = [definitions[metric_id] for metric_id in metric_ids if metric_id in definitions]
    write_audit(
        "lookup_metric_definitions",
        "metric_definition_rag",
        "success",
        {"metric_ids": metric_ids, "citations": [definition.citation for definition in selected]},
    )
    return selected


def build_summary(metrics: list[DailyMetric], alerts: list[RealtimeAlert], definitions: list[MetricDefinition]) -> dict[str, object]:
    """合成日报 + 实时告警摘要。"""

    approval = find_metric(metrics, "credit_approval_rate_1d")
    m1 = find_metric(metrics, "m1_overdue_rate_1d")
    loan = find_metric(metrics, "loan_amount_1d")
    apply_cnt = find_metric(metrics, "credit_apply_cnt_1d")

    risk_points: list[str] = []
    if approval.wow_change < 0:
        risk_points.append(f"授信通过率较前一日下降 {abs(approval.wow_change):.1%}，需要关注渠道质量、策略版本和风控拒绝率。")
    if m1.wow_change > 0:
        risk_points.append(f"M1 逾期率较前一日上升 {m1.wow_change:.1%}，需要关注贷后风险和催收队列变化。")
    for alert in alerts:
        if alert.delay_seconds > alert.delay_threshold_seconds:
            risk_points.append(f"{alert.alert_name} 链路延迟 {alert.delay_seconds} 秒超过阈值 {alert.delay_threshold_seconds} 秒，当前窗口不可给确定结论。")
        elif alert.metric_value > alert.threshold:
            risk_points.append(f"{alert.alert_name} 触发 {alert.level} 告警，指标值 {alert.metric_value} 高于阈值 {alert.threshold}。")

    summary = {
        "title": "金融信贷日报 + 近 1 小时实时告警摘要",
        "offline_daily": {
            "biz_date": apply_cnt.biz_date,
            "apply_cnt": apply_cnt.value,
            "approval_rate": approval.value,
            "loan_amount": loan.value,
            "m1_overdue_rate": m1.value,
            "evidence": [metric.evidence_id for metric in metrics],
        },
        "realtime_alerts": [asdict(alert) for alert in alerts],
        "metric_definitions": [asdict(definition) for definition in definitions],
        "risk_points": risk_points,
        "bounded_explanation": (
            "本摘要只基于离线日报指标、实时告警快照和指标口径证据。"
            "对于通过率下降或拒绝率升高的业务根因，只能给出排查方向，不能直接编造原因。"
        ),
        "next_actions": [
            "复核授信通过率口径和 ADS 分区产出状态。",
            "排查风控拒绝率突增对应的策略版本、渠道流量和上游事件质量。",
            "还款失败链路延迟超阈值时，先检查实时任务和消息积压，再判断是否业务异常。",
        ],
    }
    write_audit(
        "build_summary",
        "daily_alert_agent",
        "success",
        {"risk_points": len(risk_points), "bounded": True, "audit_required": True},
    )
    return summary


def find_metric(metrics: list[DailyMetric], metric_id: str) -> DailyMetric:
    """按指标 ID 查找日报指标。"""

    for metric in metrics:
        if metric.metric_id == metric_id:
            return metric
    raise ValueError(f"metric not found: {metric_id}")


def write_json(path: Path, data: object) -> None:
    """写入 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(summary: dict[str, object], audits: list[dict[str, object]]) -> None:
    """生成 Markdown 报告。"""

    offline = summary["offline_daily"]
    alerts = summary["realtime_alerts"]
    lines = [
        "# Day 55 日报 + 实时告警 Agent 报告",
        "",
        "## 离线日报摘要",
        "",
        f"- 日期：{offline['biz_date']}",
        f"- 授信申请量：{offline['apply_cnt']}",
        f"- 授信通过率：{offline['approval_rate']}",
        f"- 放款金额：{offline['loan_amount']}",
        f"- M1 逾期率：{offline['m1_overdue_rate']}",
        "",
        "## 近 1 小时实时告警",
        "",
        "| 告警 | 等级 | 状态 | 窗口 | 指标值 | 阈值 | 延迟 |",
        "|------|------|------|------|--------|------|------|",
    ]
    for alert in alerts:
        lines.append(
            f"| {alert['alert_name']} | {alert['level']} | {alert['status']} | {alert['window']} | "
            f"{alert['metric_value']} | {alert['threshold']} | {alert['delay_seconds']}s |"
        )

    lines.extend(["", "## 风险提示", ""])
    for point in summary["risk_points"]:
        lines.append(f"- {point}")

    lines.extend(["", "## 解释边界", "", f"- {summary['bounded_explanation']}", "", "## 建议动作", ""])
    for action in summary["next_actions"]:
        lines.append(f"- {action}")

    lines.extend(["", "## 审计记录", "", "| Step | Tool | Status |", "|------|------|--------|"])
    for audit in audits:
        lines.append(f"| {audit['step']} | {audit['tool']} | {audit['status']} |")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def read_audits() -> list[dict[str, object]]:
    """读取审计日志。"""

    return [json.loads(line) for line in AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    """运行 Day 55 日报 + 告警 Agent。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if AUDIT_LOG_PATH.exists():
        AUDIT_LOG_PATH.unlink()

    metrics = build_daily_metrics()
    alerts = build_realtime_alerts()
    definitions = build_metric_definitions()

    daily_metrics = query_daily_metrics(metrics)
    realtime_alerts = query_realtime_alerts(alerts)
    metric_definitions = lookup_metric_definitions(definitions, ["credit_approval_rate_1d", "m1_overdue_rate_1d"])
    summary = build_summary(daily_metrics, realtime_alerts, metric_definitions)

    write_json(DAILY_METRICS_PATH, [asdict(metric) for metric in metrics])
    write_json(ALERTS_PATH, [asdict(alert) for alert in alerts])
    write_json(RESULT_PATH, summary)

    audits = read_audits()
    write_report(summary, audits)

    print("Day 55 日报 + 实时告警 Agent 练习完成")
    print(f"daily_metrics={len(metrics)}")
    print(f"realtime_alerts={len(alerts)}")
    print(f"audit_steps={len(audits)}")
    print(f"risk_points={len(summary['risk_points'])}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
