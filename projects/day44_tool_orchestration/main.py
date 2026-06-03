"""Day 44 - 多工具调用策略生成器。

这个脚本不连接真实模型、数据库或知识库，而是把 Agent 的工具注册表、工具路线、
失败回退和循环保护写成结构化产物。生产里接真实工具前，先把这些边界定义清楚，
可以减少越权调用、无意义循环和工具失败后编造答案的风险。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
PLAN_PATH = OUTPUT_DIR / "tool_orchestration_plan.json"
MERMAID_PATH = OUTPUT_DIR / "tool_orchestration.mmd"
REPORT_PATH = OUTPUT_DIR / "tool_orchestration_report.md"
MAX_STEPS = 6


@dataclass(frozen=True)
class ToolDefinition:
    """描述一个 Agent 可调用工具。

    风险等级和前置条件是生产里必须显式写出来的字段。
    例如查询执行工具必须要求 SQL 校验通过，不能让模型跳过校验直接查库。
    """

    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    risk_level: str
    preconditions: list[str]
    fallback: str


@dataclass(frozen=True)
class Scenario:
    """描述一个用户问题场景和期望工具路线。"""

    scenario_id: str
    question: str
    intent: str
    risk_flags: list[str]


@dataclass(frozen=True)
class ToolCallPlan:
    """描述某个场景下的工具调用计划。"""

    scenario_id: str
    intent: str
    tool_route: list[str]
    final_status: str
    fallback_reason: str
    validation_errors: list[str]


def build_tool_registry() -> dict[str, ToolDefinition]:
    """构建工具注册表。

    注册表是编排层的基础：只有被注册、被授权、满足前置条件的工具才能进入调用路线。
    """

    tools = [
        ToolDefinition(
            name="intent_classifier",
            purpose="识别用户是在问指标、规则解释、明细查询还是敏感导出。",
            inputs=["question"],
            outputs=["intent", "risk_flags"],
            risk_level="low",
            preconditions=[],
            fallback="无法识别时要求用户补充问题。",
        ),
        ToolDefinition(
            name="schema_lookup",
            purpose="查找用户有权限访问的表、字段、指标口径和权限标签。",
            inputs=["intent", "user_role"],
            outputs=["schema_context"],
            risk_level="medium",
            preconditions=["intent_is_metric_query"],
            fallback="找不到 schema 时要求补充业务域或指标口径。",
        ),
        ToolDefinition(
            name="rag_retriever",
            purpose="检索政策、口径、规则和说明文档，并返回引用来源。",
            inputs=["question", "permission_scope"],
            outputs=["retrieved_context", "citations"],
            risk_level="medium",
            preconditions=["intent_is_rule_question"],
            fallback="无可靠引用时返回资料不足。",
        ),
        ToolDefinition(
            name="sql_generator",
            purpose="基于 schema_context 生成候选只读 SQL。",
            inputs=["question", "schema_context"],
            outputs=["candidate_sql"],
            risk_level="medium",
            preconditions=["schema_lookup_done"],
            fallback="字段或指标依据不足时不生成 SQL。",
        ),
        ToolDefinition(
            name="sql_validator",
            purpose="检查只读、敏感字段、时间范围、limit、权限和成本风险。",
            inputs=["candidate_sql", "permission_scope"],
            outputs=["validation_result"],
            risk_level="high",
            preconditions=["candidate_sql_generated"],
            fallback="校验失败时返回 safely_blocked。",
        ),
        ToolDefinition(
            name="query_executor",
            purpose="只执行校验通过的 SQL，并限制超时和返回行数。",
            inputs=["validated_sql"],
            outputs=["query_result"],
            risk_level="high",
            preconditions=["sql_validation_passed"],
            fallback="执行失败时返回 execution_failed，不允许编造结果。",
        ),
        ToolDefinition(
            name="result_interpreter",
            purpose="把查询结果或检索资料解释成业务语言，并说明口径和限制。",
            inputs=["query_result", "retrieved_context"],
            outputs=["business_answer"],
            risk_level="medium",
            preconditions=["has_query_result_or_citations"],
            fallback="资料不足或结果为空时输出保守解释。",
        ),
        ToolDefinition(
            name="safe_block",
            purpose="对敏感导出、越权字段、高成本查询或危险请求做安全阻断。",
            inputs=["risk_flags"],
            outputs=["safe_response"],
            risk_level="low",
            preconditions=["risk_detected"],
            fallback="无法判断风险时转人工复核。",
        ),
        ToolDefinition(
            name="clarification",
            purpose="当时间范围、指标、产品、地区等关键条件缺失时，要求用户补充。",
            inputs=["missing_fields"],
            outputs=["clarification_question"],
            risk_level="low",
            preconditions=["missing_required_condition"],
            fallback="用户不补充时终止本轮。",
        ),
        ToolDefinition(
            name="audit_logger",
            purpose="记录 request_id、工具路线、失败原因、最终状态和必要脱敏信息。",
            inputs=["tool_route", "final_status"],
            outputs=["audit_record"],
            risk_level="low",
            preconditions=[],
            fallback="审计失败时返回系统错误并告警。",
        ),
    ]
    return {tool.name: tool for tool in tools}


def build_scenarios() -> list[Scenario]:
    """构建覆盖成功、拒答、补充条件和规则解释的样例。"""

    return [
        Scenario(
            scenario_id="metric_success",
            question="本周授信通过率比上周变化多少？",
            intent="metric_query",
            risk_flags=[],
        ),
        Scenario(
            scenario_id="rule_answer",
            question="近 90 天有 M2 逾期记录还能自动审批吗？",
            intent="rule_question",
            risk_flags=[],
        ),
        Scenario(
            scenario_id="sensitive_export",
            question="导出今天被拒客户的手机号和身份证号。",
            intent="detail_export",
            risk_flags=["sensitive_field", "bulk_export"],
        ),
        Scenario(
            scenario_id="missing_time_range",
            question="查一下放款金额最高的渠道。",
            intent="metric_query",
            risk_flags=["missing_time_range"],
        ),
        Scenario(
            scenario_id="unsafe_sql",
            question="删除测试客户的授信申请记录。",
            intent="dangerous_operation",
            risk_flags=["write_operation"],
        ),
    ]


def plan_route(scenario: Scenario) -> ToolCallPlan:
    """根据意图和风险标记生成工具路线。

    这里用确定性规则演示编排层的职责。真实系统可以让 LLM 辅助识别意图，
    但执行类工具的前置条件和安全阻断仍然应该由代码控制。
    """

    route = ["intent_classifier"]
    final_status = "answered"
    fallback_reason = ""

    if "write_operation" in scenario.risk_flags:
        route.extend(["safe_block", "audit_logger"])
        final_status = "safely_blocked"
        fallback_reason = "命中写操作风险，Agent 只能走只读查询或拒答。"
    elif "sensitive_field" in scenario.risk_flags:
        route.extend(["safe_block", "audit_logger"])
        final_status = "safely_blocked"
        fallback_reason = "命中敏感字段或批量导出风险。"
    elif "missing_time_range" in scenario.risk_flags:
        route.extend(["schema_lookup", "clarification", "audit_logger"])
        final_status = "clarification_required"
        fallback_reason = "指标查询缺少时间范围，不能继续生成 SQL。"
    elif scenario.intent == "metric_query":
        route.extend(
            [
                "schema_lookup",
                "sql_generator",
                "sql_validator",
                "query_executor",
                "result_interpreter",
                "audit_logger",
            ]
        )
    elif scenario.intent == "rule_question":
        route.extend(["rag_retriever", "result_interpreter", "audit_logger"])
    else:
        route.extend(["clarification", "audit_logger"])
        final_status = "unsupported"
        fallback_reason = "无法匹配受支持的工具路线。"

    validation_errors = validate_route(route)
    if validation_errors and final_status == "answered":
        final_status = "route_invalid"
        fallback_reason = "工具路线结构检查失败。"

    return ToolCallPlan(
        scenario_id=scenario.scenario_id,
        intent=scenario.intent,
        tool_route=route,
        final_status=final_status,
        fallback_reason=fallback_reason,
        validation_errors=validation_errors,
    )


def validate_route(route: list[str]) -> list[str]:
    """检查工具路线是否满足最低生产边界。"""

    errors: list[str] = []
    if len(route) > MAX_STEPS + 1:
        errors.append(f"tool route exceeds max steps: {len(route)} > {MAX_STEPS + 1}")
    repeated_tools = [tool for tool in route if route.count(tool) > 1]
    if repeated_tools:
        errors.append(f"repeated tools detected: {sorted(set(repeated_tools))}")
    if "query_executor" in route and "sql_validator" not in route:
        errors.append("query_executor requires sql_validator before execution")
    if "query_executor" in route and route.index("query_executor") < route.index("sql_validator"):
        errors.append("query_executor appears before sql_validator")
    if "sql_generator" in route and "schema_lookup" not in route:
        errors.append("sql_generator requires schema_lookup")
    if "result_interpreter" in route and not (
        "query_executor" in route or "rag_retriever" in route
    ):
        errors.append("result_interpreter requires query_executor or rag_retriever")
    if route[-1] != "audit_logger":
        errors.append("route must end with audit_logger")
    return errors


def build_mermaid(plans: list[ToolCallPlan]) -> str:
    """生成工具编排 Mermaid 图。"""

    lines = ["flowchart TD"]
    for plan in plans:
        previous = f"{plan.scenario_id}_START[{plan.scenario_id}]"
        lines.append(f"    {previous}")
        for tool in plan.tool_route:
            node = f"{plan.scenario_id}_{tool}[{tool}]"
            lines.append(f"    {previous.split('[')[0]} --> {node}")
            previous = node
        status_node = f"{plan.scenario_id}_STATUS[{plan.final_status}]"
        lines.append(f"    {previous.split('[')[0]} --> {status_node}")
    return "\n".join(lines) + "\n"


def build_report(
    tools: dict[str, ToolDefinition], scenarios: list[Scenario], plans: list[ToolCallPlan]
) -> str:
    """生成 Markdown 报告。"""

    total_errors = sum(len(plan.validation_errors) for plan in plans)
    lines = [
        "# Day 44 工具编排报告",
        "",
        f"- 工具数量：{len(tools)}",
        f"- 场景数量：{len(scenarios)}",
        f"- 路线检查问题：{total_errors}",
        "",
        "## 工具注册表",
        "",
        "| 工具 | 用途 | 风险等级 | 前置条件 |",
        "|------|------|----------|----------|",
    ]
    for tool in tools.values():
        preconditions = ", ".join(tool.preconditions) if tool.preconditions else "无"
        lines.append(f"| {tool.name} | {tool.purpose} | {tool.risk_level} | {preconditions} |")

    lines.extend(
        [
            "",
            "## 场景路线",
            "",
            "| 场景 | 问题 | 工具路线 | 最终状态 | 回退原因 |",
            "|------|------|----------|----------|----------|",
        ]
    )
    scenario_by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    for plan in plans:
        scenario = scenario_by_id[plan.scenario_id]
        fallback_reason = plan.fallback_reason or "无"
        lines.append(
            f"| {plan.scenario_id} | {scenario.question} | {' -> '.join(plan.tool_route)} | "
            f"{plan.final_status} | {fallback_reason} |"
        )

    if total_errors:
        lines.extend(["", "## 检查问题", ""])
        for plan in plans:
            for error in plan.validation_errors:
                lines.append(f"- {plan.scenario_id}: {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 44 的本地练习产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tools = build_tool_registry()
    scenarios = build_scenarios()
    plans = [plan_route(scenario) for scenario in scenarios]

    payload = {
        "max_steps": MAX_STEPS,
        "tools": [asdict(tool) for tool in tools.values()],
        "scenarios": [asdict(scenario) for scenario in scenarios],
        "plans": [asdict(plan) for plan in plans],
    }
    PLAN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    MERMAID_PATH.write_text(build_mermaid(plans), encoding="utf-8")
    REPORT_PATH.write_text(build_report(tools, scenarios, plans), encoding="utf-8")

    print(f"tools={len(tools)}")
    print(f"scenarios={len(scenarios)}")
    print(f"validation_errors={sum(len(plan.validation_errors) for plan in plans)}")
    print(f"plan={PLAN_PATH}")
    print(f"mermaid={MERMAID_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
