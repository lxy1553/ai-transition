"""Day 52 - 数据血缘与 Agent 可追溯练习。

血缘工具回答的是“数据从哪里来、经过哪些任务、会影响哪些下游”，不是回答指标口径，
也不是直接查询指标值。生产里的 Agent 可以先识别血缘意图，但最终要由血缘图和权限规则
决定能返回哪些节点、证据和影响范围。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
LINEAGE_GRAPH_PATH = OUTPUT_DIR / "lineage_graph.json"
MERMAID_PATH = OUTPUT_DIR / "lineage_mermaid.md"
QA_CASES_PATH = OUTPUT_DIR / "lineage_qa_cases.json"
EVAL_RESULTS_PATH = OUTPUT_DIR / "lineage_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "data_lineage_agent_report.md"


@dataclass(frozen=True)
class LineageNode:
    """血缘图里的一个节点。

    节点可以是表、实时事件、加工任务、指标、告警或报表。把节点类型分清楚，
    Agent 才能说明“这是来源表”“这是加工任务”“这是下游报表”，而不是只返回一串表名。
    """

    node_id: str
    node_type: str
    domain: str
    name: str
    description: str
    owner: str
    permission_level: str


@dataclass(frozen=True)
class LineageEdge:
    """血缘图里的一条依赖边。"""

    source: str
    target: str
    relation: str
    evidence: str


@dataclass(frozen=True)
class LineageQaCase:
    """血缘问答评测样例。"""

    case_id: str
    question: str
    expected_status: str
    expected_answer_type: str
    expected_must_contain: list[str]


def build_lineage_nodes() -> list[LineageNode]:
    """构建离线指标、实时告警和报表相关的血缘节点。"""

    return [
        LineageNode(
            node_id="ods_credit_apply_order_di",
            node_type="offline_table",
            domain="授信申请",
            name="ODS 授信申请订单表",
            description="保留授信申请业务系统原始订单数据。",
            owner="credit_data_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="dwd_credit_apply_detail_di",
            node_type="offline_table",
            domain="授信申请",
            name="DWD 授信申请明细表",
            description="清洗后的授信申请明细事实表，含客户级字段。",
            owner="credit_data_team",
            permission_level="restricted",
        ),
        LineageNode(
            node_id="dws_credit_apply_channel_1d",
            node_type="offline_table",
            domain="授信申请",
            name="DWS 授信渠道日汇总表",
            description="按日期、渠道、产品和风险等级聚合申请量、通过量、拒绝量。",
            owner="credit_data_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="ads_credit_daily_metrics",
            node_type="offline_table",
            domain="授信申请",
            name="ADS 信贷经营日报指标表",
            description="面向经营看板和日报的授信、放款、逾期核心指标表。",
            owner="metric_platform_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="metric_credit_approval_rate",
            node_type="metric",
            domain="授信申请",
            name="授信通过率",
            description="审批通过申请数占授信申请总数的比例。",
            owner="metric_platform_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="report_credit_operation_daily",
            node_type="report",
            domain="授信申请",
            name="信贷经营日报",
            description="展示申请量、通过率、放款金额和逾期指标的日报报表。",
            owner="credit_bi_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="event_risk_decision_made",
            node_type="realtime_event",
            domain="风控决策",
            name="风控决策事件",
            description="风控引擎产生的实时决策事件，包含通过、拒绝和策略信息。",
            owner="risk_realtime_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="job_rt_risk_reject_rate_10m",
            node_type="realtime_job",
            domain="风控决策",
            name="实时风控拒绝率计算任务",
            description="按事件时间聚合 10 分钟滚动窗口拒绝率，并输出延迟状态。",
            owner="risk_realtime_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="rt_risk_reject_rate_10m",
            node_type="realtime_metric",
            domain="风控决策",
            name="实时风控拒绝率",
            description="近 10 分钟风控拒绝事件数占风控决策事件数比例。",
            owner="risk_realtime_team",
            permission_level="internal",
        ),
        LineageNode(
            node_id="alert_risk_reject_rate_spike",
            node_type="alert",
            domain="风控决策",
            name="风控拒绝率突增告警",
            description="拒绝率超过阈值且链路延迟正常时触发的实时告警。",
            owner="risk_ops_team",
            permission_level="internal",
        ),
    ]


def build_lineage_edges() -> list[LineageEdge]:
    """构建血缘依赖边。"""

    return [
        LineageEdge("ods_credit_apply_order_di", "dwd_credit_apply_detail_di", "clean_to_dwd", "job: credit_apply_detail_di_daily"),
        LineageEdge("dwd_credit_apply_detail_di", "dws_credit_apply_channel_1d", "aggregate_to_dws", "job: credit_apply_channel_1d_daily"),
        LineageEdge("dws_credit_apply_channel_1d", "ads_credit_daily_metrics", "publish_to_ads", "job: credit_daily_metrics_daily"),
        LineageEdge("ads_credit_daily_metrics", "metric_credit_approval_rate", "serve_metric", "metric_id: credit_approval_rate_1d"),
        LineageEdge("metric_credit_approval_rate", "report_credit_operation_daily", "serve_report", "report_id: credit_operation_daily"),
        LineageEdge("event_risk_decision_made", "job_rt_risk_reject_rate_10m", "consume_event", "stream: risk_decision_made"),
        LineageEdge("job_rt_risk_reject_rate_10m", "rt_risk_reject_rate_10m", "compute_realtime_metric", "window: 10m event_time"),
        LineageEdge("rt_risk_reject_rate_10m", "alert_risk_reject_rate_spike", "trigger_alert", "alert_rule: reject_rate > threshold and delay <= 180s"),
    ]


def build_qa_cases() -> list[LineageQaCase]:
    """构建血缘问答样例。"""

    return [
        LineageQaCase(
            case_id="D52-001",
            question="授信通过率来自哪些上游表？",
            expected_status="answered",
            expected_answer_type="upstream_trace",
            expected_must_contain=["ods_credit_apply_order_di", "dws_credit_apply_channel_1d", "ads_credit_daily_metrics"],
        ),
        LineageQaCase(
            case_id="D52-002",
            question="如果 dws_credit_apply_channel_1d 异常，会影响哪些下游？",
            expected_status="answered",
            expected_answer_type="downstream_impact",
            expected_must_contain=["ads_credit_daily_metrics", "metric_credit_approval_rate", "report_credit_operation_daily"],
        ),
        LineageQaCase(
            case_id="D52-003",
            question="实时风控拒绝率告警来自哪些事件和任务？",
            expected_status="answered",
            expected_answer_type="realtime_alert_trace",
            expected_must_contain=["event_risk_decision_made", "job_rt_risk_reject_rate_10m", "alert_risk_reject_rate_spike"],
        ),
        LineageQaCase(
            case_id="D52-004",
            question="昨天信贷经营日报通过率异常，应该先看哪些血缘节点？",
            expected_status="answered",
            expected_answer_type="debug_trace",
            expected_must_contain=["ads_credit_daily_metrics", "dws_credit_apply_channel_1d", "credit_daily_metrics_daily"],
        ),
        LineageQaCase(
            case_id="D52-005",
            question="帮我导出 DWD 授信申请明细里的手机号和身份证号。",
            expected_status="blocked",
            expected_answer_type="safe_block",
            expected_must_contain=["敏感明细", "阻断", "restricted"],
        ),
    ]


def upstream_nodes(target_id: str, edges: list[LineageEdge]) -> list[str]:
    """递归查找一个节点的所有上游节点。"""

    result: list[str] = []
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        for edge in edges:
            if edge.target == node_id and edge.source not in visited:
                visited.add(edge.source)
                result.append(edge.source)
                visit(edge.source)

    visit(target_id)
    return result


def downstream_nodes(source_id: str, edges: list[LineageEdge]) -> list[str]:
    """递归查找一个节点的所有下游节点。"""

    result: list[str] = []
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        for edge in edges:
            if edge.source == node_id and edge.target not in visited:
                visited.add(edge.target)
                result.append(edge.target)
                visit(edge.target)

    visit(source_id)
    return result


def answer_question(question: str, nodes: list[LineageNode], edges: list[LineageEdge]) -> dict[str, object]:
    """根据问题生成规则版血缘回答。"""

    if any(term in question for term in ["手机号", "身份证", "客户名单", "导出"]):
        return {
            "status": "blocked",
            "answer_type": "safe_block",
            "answer": "问题命中敏感明细导出，DWD 授信申请明细表为 restricted，必须阻断并写审计。",
            "nodes": ["dwd_credit_apply_detail_di"],
            "evidence": ["permission_level: restricted", "sensitive_terms: phone/id_card"],
        }

    if "实时风控拒绝率" in question or "告警" in question:
        path = ["event_risk_decision_made", "job_rt_risk_reject_rate_10m", "rt_risk_reject_rate_10m", "alert_risk_reject_rate_spike"]
        return {
            "status": "answered",
            "answer_type": "realtime_alert_trace",
            "answer": "实时风控拒绝率告警来自风控决策事件，经实时 10 分钟窗口任务计算指标，再触发拒绝率突增告警。",
            "nodes": path,
            "evidence": edge_evidence_for_path(path, edges),
        }

    if "影响" in question or "下游" in question:
        downstream = downstream_nodes("dws_credit_apply_channel_1d", edges)
        return {
            "status": "answered",
            "answer_type": "downstream_impact",
            "answer": "DWS 授信渠道日汇总表异常会影响 ADS 日报指标表、授信通过率指标和信贷经营日报。",
            "nodes": downstream,
            "evidence": edge_evidence_for_path(["dws_credit_apply_channel_1d", *downstream], edges),
        }

    if "异常" in question or "排查" in question:
        path = ["ads_credit_daily_metrics", "dws_credit_apply_channel_1d", "dwd_credit_apply_detail_di", "ods_credit_apply_order_di"]
        return {
            "status": "answered",
            "answer_type": "debug_trace",
            "answer": "日报通过率异常应先看 ADS 产出任务，再回查 DWS 汇总、DWD 明细和 ODS 原始申请数据。",
            "nodes": path,
            "evidence": ["job: credit_daily_metrics_daily", "job: credit_apply_channel_1d_daily", "job: credit_apply_detail_di_daily"],
        }

    upstream = upstream_nodes("metric_credit_approval_rate", edges)
    return {
        "status": "answered",
        "answer_type": "upstream_trace",
        "answer": "授信通过率来自 ADS 信贷经营日报指标表，上游依次包含 DWS 授信渠道日汇总表、DWD 授信申请明细表和 ODS 授信申请订单表。",
        "nodes": upstream,
        "evidence": edge_evidence_for_path([*reversed(upstream), "metric_credit_approval_rate"], edges),
    }


def edge_evidence_for_path(path: list[str], edges: list[LineageEdge]) -> list[str]:
    """抽取路径上相邻边的证据。"""

    evidence: list[str] = []
    for source, target in zip(path, path[1:]):
        for edge in edges:
            if edge.source == source and edge.target == target:
                evidence.append(edge.evidence)
    return evidence


def evaluate_cases(
    cases: list[LineageQaCase],
    nodes: list[LineageNode],
    edges: list[LineageEdge],
) -> list[dict[str, object]]:
    """评估血缘问答是否命中预期节点和状态。"""

    results: list[dict[str, object]] = []
    for case in cases:
        actual = answer_question(case.question, nodes, edges)
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


def write_mermaid(nodes: list[LineageNode], edges: list[LineageEdge]) -> None:
    """生成 Mermaid 血缘图，便于放进 README 或作品集。"""

    lines = ["```mermaid", "flowchart LR"]
    node_map = {node.node_id: node for node in nodes}
    for edge in edges:
        source = node_map[edge.source]
        target = node_map[edge.target]
        lines.append(f'  {edge.source}["{source.name}"] -->|{edge.relation}| {edge.target}["{target.name}"]')
    lines.append("```")
    MERMAID_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_report(nodes: list[LineageNode], edges: list[LineageEdge], results: list[dict[str, object]]) -> None:
    """生成血缘练习报告。"""

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Day 52 数据血缘 + Agent 可追溯报告",
        "",
        "## 血缘节点概览",
        "",
        "| 节点 | 类型 | 主题域 | 权限 | owner |",
        "|------|------|--------|------|-------|",
    ]
    for node in nodes:
        lines.append(f"| {node.node_id} | {node.node_type} | {node.domain} | {node.permission_level} | {node.owner} |")

    lines.extend(["", "## 血缘边概览", "", "| Source | Relation | Target | Evidence |", "|--------|----------|--------|----------|"])
    for edge in edges:
        lines.append(f"| {edge.source} | {edge.relation} | {edge.target} | {edge.evidence} |")

    lines.extend(
        [
            "",
            "## 问答评测",
            "",
            f"- 总样例数：{total}",
            f"- 通过样例数：{passed}",
            f"- 通过率：{passed / total:.4f}",
            "",
            "| Case | 问题 | 类型 | 状态 | 通过 |",
            "|------|------|------|------|------|",
        ]
    )
    for result in results:
        passed_text = "是" if result["passed"] else "否"
        lines.append(
            f"| {result['case_id']} | {result['question']} | {result['actual_answer_type']} | {result['actual_status']} | {passed_text} |"
        )

    lines.extend(
        [
            "",
            "## 生产结论",
            "",
            "- 数据血缘用于回答来源追溯、影响分析、加工链路和告警证据。",
            "- Agent 回答血缘问题时必须返回节点、路径、任务和证据，不能只给自然语言猜测。",
            "- 离线血缘关注 ODS/DWD/DWS/ADS、调度任务、指标和报表。",
            "- 实时血缘关注事件流、实时任务、窗口指标、延迟状态和告警规则。",
            "- 血缘工具不能绕过权限系统，命中敏感明细时必须阻断并审计。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 52 血缘练习。"""

    nodes = build_lineage_nodes()
    edges = build_lineage_edges()
    cases = build_qa_cases()
    results = evaluate_cases(cases, nodes, edges)

    write_json(LINEAGE_GRAPH_PATH, {"nodes": [asdict(node) for node in nodes], "edges": [asdict(edge) for edge in edges]})
    write_json(QA_CASES_PATH, [asdict(case) for case in cases])
    write_json(EVAL_RESULTS_PATH, results)
    write_mermaid(nodes, edges)
    write_report(nodes, edges, results)

    passed = sum(1 for result in results if result["passed"])
    print("Day 52 数据血缘 + Agent 可追溯练习完成")
    print(f"nodes={len(nodes)}")
    print(f"edges={len(edges)}")
    print(f"qa_cases={len(cases)}")
    print(f"passed={passed}")
    print(f"pass_rate={passed / len(results):.4f}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
