"""Day 48 - 实时仓库基础与 Agent 实时路由练习。

这个脚本用模拟的信贷实时事件、实时指标和用户问题，演示 Agent 如何判断
一个问题应该走实时状态工具、告警工具、澄清、还是安全阻断。生产里实时问题
不能误走离线 SQL，因为实时窗口、事件时间、处理时间和链路延迟都会影响答案可信度。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
EVENT_CATALOG_PATH = OUTPUT_DIR / "realtime_event_catalog.json"
METRIC_CATALOG_PATH = OUTPUT_DIR / "realtime_metric_catalog.json"
ROUTING_CASES_PATH = OUTPUT_DIR / "realtime_agent_routing_cases.json"
MERMAID_PATH = OUTPUT_DIR / "realtime_warehouse_routing.mmd"
REPORT_PATH = OUTPUT_DIR / "realtime_warehouse_routing_report.md"


@dataclass(frozen=True)
class RealtimeEvent:
    """描述一个实时事件。

    实时事件必须写清事件时间和处理时间字段，否则 Agent 无法判断窗口指标是否可靠。
    """

    event_name: str
    subject: str
    event_time_field: str
    processing_time_field: str
    key_fields: list[str]
    example_payload: dict[str, str]
    sensitive_level: str


@dataclass(frozen=True)
class RealtimeMetric:
    """描述一个实时指标的口径和链路状态要求。"""

    metric_name: str
    subject: str
    window: str
    grain: str
    source_event: str
    delay_threshold_minutes: int
    agent_tool: str
    usage: str


@dataclass(frozen=True)
class RealtimeRoutingCase:
    """描述 Agent 对实时问题的路由选择。"""

    case_id: str
    user_question: str
    intent: str
    expected_tool: str
    route: list[str]
    expected_status: str
    reason: str
    forbidden_tools: list[str]


def build_event_catalog() -> list[RealtimeEvent]:
    """构建金融信贷实时事件目录。"""

    return [
        RealtimeEvent(
            event_name="credit_apply_submitted",
            subject="授信申请",
            event_time_field="apply_event_time",
            processing_time_field="ingest_time",
            key_fields=["apply_id", "channel", "product_code", "customer_hash"],
            example_payload={
                "apply_id": "A202606030001",
                "channel": "app",
                "product_code": "cash_loan",
                "event_type": "submitted",
            },
            sensitive_level="medium",
        ),
        RealtimeEvent(
            event_name="risk_decision_made",
            subject="风控决策",
            event_time_field="decision_event_time",
            processing_time_field="process_time",
            key_fields=["apply_id", "strategy_id", "decision_result", "risk_grade"],
            example_payload={
                "apply_id": "A202606030001",
                "strategy_id": "STR_BLACKLIST",
                "decision_result": "reject",
                "risk_grade": "high",
            },
            sensitive_level="medium",
        ),
        RealtimeEvent(
            event_name="repayment_failed",
            subject="还款失败",
            event_time_field="repay_event_time",
            processing_time_field="ingest_time",
            key_fields=["loan_id", "repay_channel", "failure_code", "customer_hash"],
            example_payload={
                "loan_id": "L202606030009",
                "repay_channel": "bank_card",
                "failure_code": "balance_not_enough",
                "event_type": "failed",
            },
            sensitive_level="high",
        ),
    ]


def build_metric_catalog() -> list[RealtimeMetric]:
    """构建实时指标目录。"""

    return [
        RealtimeMetric(
            metric_name="rt_apply_cnt_5m",
            subject="授信申请量",
            window="5 minutes",
            grain="channel + product_code",
            source_event="credit_apply_submitted",
            delay_threshold_minutes=3,
            agent_tool="realtime_metric_tool",
            usage="查询近 5 分钟申请量、渠道突增和实时申请状态。",
        ),
        RealtimeMetric(
            metric_name="rt_risk_reject_rate_10m",
            subject="风控拒绝率",
            window="10 minutes",
            grain="strategy_id + product_code",
            source_event="risk_decision_made",
            delay_threshold_minutes=3,
            agent_tool="realtime_metric_tool",
            usage="查询近 10 分钟策略拒绝率、实时风控异常和策略命中变化。",
        ),
        RealtimeMetric(
            metric_name="rt_repayment_failed_cnt_5m",
            subject="还款失败数",
            window="5 minutes",
            grain="repay_channel + failure_code",
            source_event="repayment_failed",
            delay_threshold_minutes=2,
            agent_tool="realtime_metric_tool",
            usage="查询近 5 分钟还款失败数、扣款异常和告警触发依据。",
        ),
    ]


def build_routing_cases() -> list[RealtimeRoutingCase]:
    """构建 Agent 实时路由样例。"""

    return [
        RealtimeRoutingCase(
            case_id="D48-001",
            user_question="近 5 分钟 app 渠道授信申请量是否异常？",
            intent="realtime_metric",
            expected_tool="realtime_metric_tool",
            route=[
                "intent_classifier",
                "realtime_router",
                "realtime_metric_catalog",
                "realtime_metric_tool",
                "delay_checker",
                "result_interpreter",
                "audit_logger",
            ],
            expected_status="answered",
            reason="近 5 分钟申请量是实时窗口指标，必须走实时指标工具。",
            forbidden_tools=["offline_sql_generator", "offline_query_executor"],
        ),
        RealtimeRoutingCase(
            case_id="D48-002",
            user_question="当前 STR_BLACKLIST 策略拒绝率突增的告警原因是什么？",
            intent="realtime_alert",
            expected_tool="alert_query_tool",
            route=[
                "intent_classifier",
                "realtime_router",
                "alert_query_tool",
                "delay_checker",
                "result_interpreter",
                "audit_logger",
            ],
            expected_status="answered",
            reason="告警解释要走告警工具，只能基于告警证据说明事实。",
            forbidden_tools=["offline_sql_generator", "offline_query_executor"],
        ),
        RealtimeRoutingCase(
            case_id="D48-003",
            user_question="看一下实时拒绝率是否异常。",
            intent="clarification_required",
            expected_tool="clarification",
            route=["intent_classifier", "realtime_router", "clarification", "audit_logger"],
            expected_status="clarification_required",
            reason="缺少窗口、业务线或策略维度时，不能直接查实时指标。",
            forbidden_tools=["realtime_metric_tool", "offline_query_executor"],
        ),
        RealtimeRoutingCase(
            case_id="D48-004",
            user_question="近 5 分钟还款失败数是否异常，但实时链路延迟 20 分钟。",
            intent="realtime_metric_with_delay",
            expected_tool="delay_checker",
            route=[
                "intent_classifier",
                "realtime_router",
                "realtime_metric_tool",
                "delay_checker",
                "audit_logger",
            ],
            expected_status="execution_failed",
            reason="实时链路延迟超过阈值，不能把过期窗口解释成当前状态。",
            forbidden_tools=["offline_sql_generator", "offline_query_executor"],
        ),
        RealtimeRoutingCase(
            case_id="D48-005",
            user_question="导出实时风控事件流里的客户手机号和身份证号。",
            intent="sensitive_realtime_export",
            expected_tool="safe_block",
            route=["intent_classifier", "permission_checker", "safe_block", "audit_logger"],
            expected_status="safely_blocked",
            reason="实时事件流里的客户敏感明细不能导出。",
            forbidden_tools=["realtime_metric_tool", "offline_query_executor"],
        ),
    ]


def build_mermaid() -> str:
    """生成实时仓库链路和 Agent 路由图。"""

    return "\n".join(
        [
            "flowchart LR",
            "    source[业务事件\\n授信申请/风控决策/还款失败] --> mq[Kafka / Event Bus]",
            "    mq --> stream[Flink 实时计算]",
            "    stream --> metrics[实时指标状态表\\n窗口/事件时间/处理时间]",
            "    stream --> alerts[实时告警表\\n等级/规则/证据]",
            "    metrics --> tool[realtime_metric_tool]",
            "    alerts --> alert_tool[alert_query_tool]",
            "    tool --> delay[delay_checker]",
            "    alert_tool --> delay",
            "    delay --> agent[Agent 结果解释]",
            "    delay -. 延迟超阈值 .-> fail[execution_failed / 降级说明]",
            "    agent --> audit[audit_logger]",
            "    offline[offline_sql_generator]:::blocked -. 实时问题禁止 .-> fail",
            "    classDef blocked fill:#ffecec,stroke:#b42318,color:#7a271a;",
        ]
    ) + "\n"


def build_report(
    events: list[RealtimeEvent],
    metrics: list[RealtimeMetric],
    cases: list[RealtimeRoutingCase],
) -> str:
    """生成 Day 48 练习报告。"""

    lines = [
        "# Day 48 实时仓库基础与 Agent 实时路由报告",
        "",
        "## 实时链路原则",
        "",
        "- 实时问题要优先走实时指标工具或告警工具，不能误走离线 SQL。",
        "- 实时指标必须写清窗口、事件时间、处理时间和延迟阈值。",
        "- 链路延迟超过阈值时，不能给出当前状态的确定结论。",
        "- 实时事件流里的敏感明细仍然要走权限校验和安全阻断。",
        "",
        "## 实时事件目录",
        "",
        "| 事件 | 主题 | 事件时间字段 | 处理时间字段 | 敏感等级 |",
        "|------|------|--------------|--------------|----------|",
    ]
    for event in events:
        lines.append(
            f"| {event.event_name} | {event.subject} | {event.event_time_field} | "
            f"{event.processing_time_field} | {event.sensitive_level} |"
        )

    lines.extend(
        [
            "",
            "## 实时指标目录",
            "",
            "| 指标 | 主题 | 窗口 | 粒度 | 延迟阈值 | 工具 |",
            "|------|------|------|------|----------|------|",
        ]
    )
    for metric in metrics:
        lines.append(
            f"| {metric.metric_name} | {metric.subject} | {metric.window} | "
            f"{metric.grain} | {metric.delay_threshold_minutes} 分钟 | {metric.agent_tool} |"
        )

    lines.extend(
        [
            "",
            "## Agent 实时路由样例",
            "",
            "| Case | 用户问题 | 预期工具 | 预期状态 | 路由原因 |",
            "|------|----------|----------|----------|----------|",
        ]
    )
    for case in cases:
        lines.append(
            f"| {case.case_id} | {case.user_question} | {case.expected_tool} | "
            f"{case.expected_status} | {case.reason} |"
        )

    lines.extend(
        [
            "",
            "## 生产启示",
            "",
            "- 实时路由先看时间信号、窗口信号、告警信号和事件流信号。",
            "- 缺少窗口或业务维度时，正确行为是澄清，不是随便查询。",
            "- 实时延迟是数据可用性问题，必须由 delay_checker 结构化判断。",
            "- 实时告警解释只能基于告警证据，不能编造业务原因。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 48 实时仓库和 Agent 路由产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = build_event_catalog()
    metrics = build_metric_catalog()
    cases = build_routing_cases()

    EVENT_CATALOG_PATH.write_text(
        json.dumps([asdict(event) for event in events], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    METRIC_CATALOG_PATH.write_text(
        json.dumps([asdict(metric) for metric in metrics], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ROUTING_CASES_PATH.write_text(
        json.dumps([asdict(case) for case in cases], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MERMAID_PATH.write_text(build_mermaid(), encoding="utf-8")
    REPORT_PATH.write_text(build_report(events, metrics, cases), encoding="utf-8")

    print(f"events={len(events)}")
    print(f"metrics={len(metrics)}")
    print(f"routing_cases={len(cases)}")
    print(f"events_path={EVENT_CATALOG_PATH}")
    print(f"metrics_path={METRIC_CATALOG_PATH}")
    print(f"cases_path={ROUTING_CASES_PATH}")
    print(f"diagram={MERMAID_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
