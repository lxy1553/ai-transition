"""Day 51 - Schema Catalog 与工具注册表练习。

这个脚本用规则方式模拟生产 Agent 的工具选择过程。
Schema Catalog 负责说明“有哪些表、字段、粒度、权限和查询约束”，工具注册表负责说明
“有哪些工具、输入参数、前置条件、风险等级和失败处理”。模型可以参与理解用户问题，
但是否允许调用工具必须由这些确定性元数据共同约束。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
SCHEMA_CATALOG_PATH = OUTPUT_DIR / "schema_catalog.json"
TOOL_REGISTRY_PATH = OUTPUT_DIR / "tool_registry.json"
ROUTING_CASES_PATH = OUTPUT_DIR / "routing_cases.json"
EVAL_RESULTS_PATH = OUTPUT_DIR / "routing_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "schema_catalog_tool_registry_report.md"


@dataclass(frozen=True)
class CatalogEntity:
    """描述 Agent 可理解的一张离线表、一个实时指标或一个血缘入口。

    Catalog 不是简单字段列表。生产里还要写清层级、粒度、分区、时间字段和权限标签。
    否则 Agent 可能选错 ODS 明细表、漏掉分区条件，或者访问手机号、身份证号这类敏感字段。
    """

    entity_id: str
    entity_type: str
    layer: str
    domain: str
    name: str
    description: str
    grain: str
    time_field: str
    partition_field: str
    fields: list[dict[str, str]]
    sensitive_fields: list[str]
    permission_level: str
    query_constraints: list[str]
    owner: str


@dataclass(frozen=True)
class ToolDefinition:
    """描述 Agent 可调用工具的注册信息。"""

    tool_id: str
    tool_name: str
    intent: str
    description: str
    allowed_entity_types: list[str]
    required_inputs: list[str]
    preconditions: list[str]
    risk_level: str
    fallback: str
    audit_required: bool


@dataclass(frozen=True)
class RoutingCase:
    """一条用户问题到工具路线的评测样例。"""

    case_id: str
    question: str
    expected_tool_id: str
    expected_entity_id: str
    expected_status: str
    expected_reason_contains: list[str]


def build_schema_catalog() -> list[CatalogEntity]:
    """构建信贷离线表、实时指标和血缘入口的 Catalog。"""

    return [
        CatalogEntity(
            entity_id="ads_credit_daily_metrics",
            entity_type="offline_table",
            layer="ADS",
            domain="授信申请",
            name="ads_credit_daily_metrics",
            description="信贷经营日报指标表，服务经营看板和总览查询。",
            grain="biz_date + channel + product_code",
            time_field="biz_date",
            partition_field="biz_date",
            fields=[
                {"name": "biz_date", "type": "date", "desc": "业务日期"},
                {"name": "channel", "type": "string", "desc": "渠道"},
                {"name": "product_code", "type": "string", "desc": "产品编码"},
                {"name": "apply_cnt", "type": "int", "desc": "授信申请量"},
                {"name": "approved_cnt", "type": "int", "desc": "授信通过量"},
                {"name": "approval_rate", "type": "decimal", "desc": "授信通过率"},
                {"name": "loan_amount", "type": "decimal", "desc": "放款金额"},
            ],
            sensitive_fields=[],
            permission_level="internal",
            query_constraints=["必须带 biz_date 条件", "优先用于日报总览", "不包含客户明细"],
            owner="credit_data_team",
        ),
        CatalogEntity(
            entity_id="dws_credit_apply_channel_1d",
            entity_type="offline_table",
            layer="DWS",
            domain="授信申请",
            name="dws_credit_apply_channel_1d",
            description="按渠道和产品汇总的授信申请主题宽表，适合趋势和维度分析。",
            grain="dt + channel + product_code + risk_grade",
            time_field="dt",
            partition_field="dt",
            fields=[
                {"name": "dt", "type": "date", "desc": "分区日期"},
                {"name": "channel", "type": "string", "desc": "渠道"},
                {"name": "product_code", "type": "string", "desc": "产品编码"},
                {"name": "risk_grade", "type": "string", "desc": "风险等级"},
                {"name": "apply_cnt", "type": "int", "desc": "申请量"},
                {"name": "approved_cnt", "type": "int", "desc": "审批通过量"},
                {"name": "rejected_cnt", "type": "int", "desc": "审批拒绝量"},
            ],
            sensitive_fields=[],
            permission_level="internal",
            query_constraints=["必须带 dt 条件", "适合渠道、产品、风险等级维度分析"],
            owner="credit_data_team",
        ),
        CatalogEntity(
            entity_id="dwd_credit_apply_detail_di",
            entity_type="offline_table",
            layer="DWD",
            domain="授信申请",
            name="dwd_credit_apply_detail_di",
            description="授信申请明细事实表，只用于授权排查和明细核对。",
            grain="apply_id",
            time_field="apply_time",
            partition_field="dt",
            fields=[
                {"name": "apply_id", "type": "string", "desc": "申请单 ID"},
                {"name": "customer_id", "type": "string", "desc": "客户 ID"},
                {"name": "phone", "type": "string", "desc": "手机号"},
                {"name": "id_card", "type": "string", "desc": "身份证号"},
                {"name": "apply_time", "type": "timestamp", "desc": "申请时间"},
                {"name": "approve_status", "type": "string", "desc": "审批状态"},
            ],
            sensitive_fields=["phone", "id_card", "customer_id"],
            permission_level="restricted",
            query_constraints=["普通 Agent 不可直接查询", "必须有明细授权和审计原因", "禁止批量导出敏感字段"],
            owner="credit_data_team",
        ),
        CatalogEntity(
            entity_id="rt_risk_reject_rate_10m",
            entity_type="realtime_metric",
            layer="REALTIME",
            domain="风控决策",
            name="rt_risk_reject_rate_10m",
            description="实时 10 分钟滚动窗口风控拒绝率。",
            grain="window_start + strategy_id + product_code",
            time_field="event_time",
            partition_field="window_start",
            fields=[
                {"name": "window_start", "type": "timestamp", "desc": "窗口开始时间"},
                {"name": "strategy_id", "type": "string", "desc": "策略 ID"},
                {"name": "product_code", "type": "string", "desc": "产品编码"},
                {"name": "reject_event_cnt", "type": "int", "desc": "拒绝事件数"},
                {"name": "risk_decision_event_cnt", "type": "int", "desc": "风控决策事件数"},
                {"name": "reject_rate", "type": "decimal", "desc": "拒绝率"},
                {"name": "delay_seconds", "type": "int", "desc": "链路延迟秒数"},
            ],
            sensitive_fields=[],
            permission_level="internal",
            query_constraints=["必须带窗口", "必须检查 delay_seconds", "延迟超过阈值时不能给确定结论"],
            owner="risk_realtime_team",
        ),
        CatalogEntity(
            entity_id="lineage_credit_approval_rate",
            entity_type="lineage_entry",
            layer="METADATA",
            domain="授信申请",
            name="lineage_credit_approval_rate",
            description="授信通过率从 ODS 到 ADS 的血缘入口。",
            grain="metric_id",
            time_field="version_time",
            partition_field="none",
            fields=[
                {"name": "metric_id", "type": "string", "desc": "指标 ID"},
                {"name": "upstream_tables", "type": "array", "desc": "上游表"},
                {"name": "jobs", "type": "array", "desc": "加工任务"},
                {"name": "downstream_reports", "type": "array", "desc": "下游报表"},
            ],
            sensitive_fields=[],
            permission_level="internal",
            query_constraints=["用于回答来源和影响范围", "不返回客户明细"],
            owner="metadata_team",
        ),
    ]


def build_tool_registry() -> list[ToolDefinition]:
    """构建 Agent 工具注册表。"""

    return [
        ToolDefinition(
            tool_id="metric_definition_rag",
            tool_name="指标口径 RAG 工具",
            intent="metric_definition",
            description="回答指标定义、分子分母、时间口径、窗口和使用限制。",
            allowed_entity_types=["metric_definition"],
            required_inputs=["metric_name"],
            preconditions=["问题是口径解释，不是查当前数值", "必须返回 citation"],
            risk_level="medium",
            fallback="无可靠口径资料时返回资料不足",
            audit_required=True,
        ),
        ToolDefinition(
            tool_id="offline_nl2sql_query",
            tool_name="离线 NL2SQL 查询工具",
            intent="offline_metric_query",
            description="查询离线 ADS/DWS 指标表，回答历史指标、趋势和维度分析。",
            allowed_entity_types=["offline_table"],
            required_inputs=["metric", "date_range", "dimensions"],
            preconditions=["优先选择 ADS/DWS", "必须有分区条件", "不得选择 restricted 敏感明细字段"],
            risk_level="high",
            fallback="缺时间范围时先澄清，命中敏感字段时阻断",
            audit_required=True,
        ),
        ToolDefinition(
            tool_id="realtime_metric_query",
            tool_name="实时指标查询工具",
            intent="realtime_status_query",
            description="查询实时窗口指标、延迟状态和异常状态。",
            allowed_entity_types=["realtime_metric"],
            required_inputs=["metric", "window", "dimension_filter"],
            preconditions=["必须有窗口", "必须检查延迟", "延迟超阈值时返回不可判断或降级"],
            risk_level="high",
            fallback="缺窗口时澄清，链路延迟时说明不可用原因",
            audit_required=True,
        ),
        ToolDefinition(
            tool_id="lineage_lookup",
            tool_name="血缘追溯工具",
            intent="lineage_query",
            description="查询指标、表或报表的上游来源、加工任务和下游影响范围。",
            allowed_entity_types=["lineage_entry"],
            required_inputs=["metric_or_table_name"],
            preconditions=["问题关注来源、影响范围或加工链路", "不返回敏感明细"],
            risk_level="medium",
            fallback="无血缘资料时返回资料不足",
            audit_required=True,
        ),
        ToolDefinition(
            tool_id="safe_block",
            tool_name="安全阻断工具",
            intent="sensitive_export",
            description="阻断手机号、身份证号、银行卡号、客户名单等敏感明细导出请求。",
            allowed_entity_types=["offline_table", "realtime_metric", "lineage_entry"],
            required_inputs=["question", "matched_sensitive_terms"],
            preconditions=["命中敏感导出或越权访问", "必须写审计"],
            risk_level="critical",
            fallback="提示需要授权流程，不执行查询",
            audit_required=True,
        ),
    ]


def build_routing_cases() -> list[RoutingCase]:
    """构建工具路由评测样例。"""

    return [
        RoutingCase(
            case_id="D51-001",
            question="近 7 天各渠道授信通过率是多少？",
            expected_tool_id="offline_nl2sql_query",
            expected_entity_id="dws_credit_apply_channel_1d",
            expected_status="routed",
            expected_reason_contains=["离线指标", "DWS", "dt"],
        ),
        RoutingCase(
            case_id="D51-002",
            question="看一下当前实时风控拒绝率是不是异常，按近 10 分钟。",
            expected_tool_id="realtime_metric_query",
            expected_entity_id="rt_risk_reject_rate_10m",
            expected_status="routed",
            expected_reason_contains=["实时指标", "窗口", "延迟"],
        ),
        RoutingCase(
            case_id="D51-003",
            question="授信通过率这个指标来自哪些上游表，会影响哪些报表？",
            expected_tool_id="lineage_lookup",
            expected_entity_id="lineage_credit_approval_rate",
            expected_status="routed",
            expected_reason_contains=["血缘", "上游", "下游"],
        ),
        RoutingCase(
            case_id="D51-004",
            question="导出昨天所有授信申请客户的手机号和身份证号。",
            expected_tool_id="safe_block",
            expected_entity_id="dwd_credit_apply_detail_di",
            expected_status="blocked",
            expected_reason_contains=["敏感字段", "阻断", "restricted"],
        ),
        RoutingCase(
            case_id="D51-005",
            question="查一下授信申请明细表里最近一个月所有客户记录。",
            expected_tool_id="safe_block",
            expected_entity_id="dwd_credit_apply_detail_di",
            expected_status="blocked",
            expected_reason_contains=["明细", "授权", "审计"],
        ),
    ]


def route_question(
    question: str,
    catalog: list[CatalogEntity],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """根据问题、Catalog 和工具注册表选择工具。

    这里故意使用简单规则，是为了突出确定性约束。生产里可以让模型先给候选意图，
    但最终仍要用 Catalog 和 Tool Registry 校验前置条件、权限和风险等级。
    """

    sensitive_terms = ["手机号", "身份证", "客户记录", "客户名单", "导出"]
    if any(term in question for term in sensitive_terms):
        entity = find_entity(catalog, "dwd_credit_apply_detail_di")
        return build_route_result("safe_block", entity, tools, "命中敏感字段或明细导出，DWD 明细表为 restricted，缺少明细授权时必须阻断并写审计。", "blocked")

    if "实时" in question or "当前" in question or "近 10 分钟" in question:
        entity = find_entity(catalog, "rt_risk_reject_rate_10m")
        return build_route_result("realtime_metric_query", entity, tools, "实时指标问题，必须带窗口并检查延迟状态。", "routed")

    if "来自" in question or "上游" in question or "下游" in question or "血缘" in question:
        entity = find_entity(catalog, "lineage_credit_approval_rate")
        return build_route_result("lineage_lookup", entity, tools, "血缘追溯问题，需要返回上游、加工任务和下游影响范围。", "routed")

    if "各渠道" in question or "趋势" in question:
        entity = find_entity(catalog, "dws_credit_apply_channel_1d")
        return build_route_result("offline_nl2sql_query", entity, tools, "离线指标维度分析，优先选择 DWS，并要求 dt 分区条件。", "routed")

    entity = find_entity(catalog, "ads_credit_daily_metrics")
    return build_route_result("offline_nl2sql_query", entity, tools, "离线日报总览问题，优先选择 ADS，并要求 biz_date 分区条件。", "routed")


def find_entity(catalog: list[CatalogEntity], entity_id: str) -> CatalogEntity:
    """按 ID 查找 Catalog 实体。"""

    for entity in catalog:
        if entity.entity_id == entity_id:
            return entity
    raise ValueError(f"entity not found: {entity_id}")


def find_tool(tools: list[ToolDefinition], tool_id: str) -> ToolDefinition:
    """按 ID 查找工具定义。"""

    for tool in tools:
        if tool.tool_id == tool_id:
            return tool
    raise ValueError(f"tool not found: {tool_id}")


def build_route_result(
    tool_id: str,
    entity: CatalogEntity,
    tools: list[ToolDefinition],
    reason: str,
    status: str,
) -> dict[str, object]:
    """生成统一的路由结果，便于后续评测和审计。"""

    tool = find_tool(tools, tool_id)
    return {
        "status": status,
        "tool_id": tool.tool_id,
        "tool_name": tool.tool_name,
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type,
        "permission_level": entity.permission_level,
        "risk_level": tool.risk_level,
        "audit_required": tool.audit_required,
        "preconditions": tool.preconditions,
        "reason": reason,
    }


def evaluate_routes(
    cases: list[RoutingCase],
    catalog: list[CatalogEntity],
    tools: list[ToolDefinition],
) -> list[dict[str, object]]:
    """评估工具路由是否符合预期。"""

    results: list[dict[str, object]] = []
    for case in cases:
        actual = route_question(case.question, catalog, tools)
        checks = {
            "tool_match": actual["tool_id"] == case.expected_tool_id,
            "entity_match": actual["entity_id"] == case.expected_entity_id,
            "status_match": actual["status"] == case.expected_status,
            "reason_match": all(keyword in str(actual["reason"]) for keyword in case.expected_reason_contains),
        }
        passed = all(checks.values())
        results.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_tool_id": case.expected_tool_id,
                "actual_tool_id": actual["tool_id"],
                "expected_entity_id": case.expected_entity_id,
                "actual_entity_id": actual["entity_id"],
                "expected_status": case.expected_status,
                "actual_status": actual["status"],
                "checks": checks,
                "passed": passed,
                "route_result": actual,
            }
        )
    return results


def write_json(path: Path, data: object) -> None:
    """写入格式化 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(
    catalog: list[CatalogEntity],
    tools: list[ToolDefinition],
    results: list[dict[str, object]],
) -> None:
    """生成 Markdown 报告。"""

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Day 51 Schema Catalog + 工具注册表报告",
        "",
        "## Catalog 概览",
        "",
        "| 实体 | 类型 | 层级 | 主题域 | 粒度 | 权限 |",
        "|------|------|------|--------|------|------|",
    ]
    for entity in catalog:
        lines.append(
            f"| {entity.entity_id} | {entity.entity_type} | {entity.layer} | {entity.domain} | {entity.grain} | {entity.permission_level} |"
        )

    lines.extend(
        [
            "",
            "## 工具注册表",
            "",
            "| 工具 | 意图 | 风险等级 | 审计 | 失败处理 |",
            "|------|------|----------|------|----------|",
        ]
    )
    for tool in tools:
        audit_text = "是" if tool.audit_required else "否"
        lines.append(f"| {tool.tool_id} | {tool.intent} | {tool.risk_level} | {audit_text} | {tool.fallback} |")

    lines.extend(
        [
            "",
            "## 路由评测",
            "",
            f"- 总样例数：{total}",
            f"- 通过样例数：{passed}",
            f"- 通过率：{passed / total:.4f}",
            "",
            "| Case | 问题 | 工具 | 实体 | 状态 | 通过 |",
            "|------|------|------|------|------|------|",
        ]
    )
    for result in results:
        passed_text = "是" if result["passed"] else "否"
        lines.append(
            f"| {result['case_id']} | {result['question']} | {result['actual_tool_id']} | "
            f"{result['actual_entity_id']} | {result['actual_status']} | {passed_text} |"
        )

    lines.extend(
        [
            "",
            "## 生产结论",
            "",
            "- Schema Catalog 要约束表、字段、粒度、分区、时间字段和权限边界。",
            "- 工具注册表要约束工具用途、输入参数、前置条件、风险等级和失败处理。",
            "- Agent 可以给出候选路线，但最终是否调用工具必须经过确定性校验。",
            "- 金融信贷场景里，敏感明细、实时延迟、漏分区和错误表选择都必须在工具调用前拦住。",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 51 Catalog 和工具注册表练习。"""

    catalog = build_schema_catalog()
    tools = build_tool_registry()
    cases = build_routing_cases()
    results = evaluate_routes(cases, catalog, tools)

    write_json(SCHEMA_CATALOG_PATH, [asdict(item) for item in catalog])
    write_json(TOOL_REGISTRY_PATH, [asdict(item) for item in tools])
    write_json(ROUTING_CASES_PATH, [asdict(item) for item in cases])
    write_json(EVAL_RESULTS_PATH, results)
    write_report(catalog, tools, results)

    passed = sum(1 for result in results if result["passed"])
    print("Day 51 Schema Catalog + 工具注册表练习完成")
    print(f"catalog_entities={len(catalog)}")
    print(f"tools={len(tools)}")
    print(f"routing_cases={len(cases)}")
    print(f"passed={passed}")
    print(f"pass_rate={passed / len(results):.4f}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
