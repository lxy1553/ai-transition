"""Day 43 - Agent 工作流定义生成器。

这个脚本不连接真实模型和数据库，而是先把 Agent 每一步的职责、工具、失败回退和审计点写成结构化定义。
生产里做 Agent 最怕流程边界不清，先生成可检查的流程定义，后续才能稳定扩展多工具调用和端到端评测。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
WORKFLOW_JSON_PATH = OUTPUT_DIR / "agent_workflow.json"
WORKFLOW_MERMAID_PATH = OUTPUT_DIR / "agent_workflow.mmd"
REPORT_PATH = OUTPUT_DIR / "agent_workflow_report.md"


@dataclass(frozen=True)
class WorkflowStep:
    """描述 Agent 工作流中的一个受控步骤。

    每一步都写清输入、输出、工具和失败回退，是为了避免模型自由调用工具后无法解释。
    在金融信贷场景里，错误调用工具可能带来敏感数据泄露、错误 SQL 执行和审计缺失。
    """

    step_id: str
    name: str
    purpose: str
    input_from: list[str]
    output: str
    tools: list[str]
    risk_controls: list[str]
    fallback: str
    audit_fields: list[str]


def build_workflow() -> list[WorkflowStep]:
    """构建 Day 43 的最小 Agent 工作流。

    这里先用固定步骤，而不是动态规划工具调用，是为了让学习版项目可解释、可复盘。
    后续接 LLM 时，也应该让模型在这套边界内工作，而不是绕过权限和校验直接执行。
    """

    return [
        WorkflowStep(
            step_id="intent",
            name="意图识别",
            purpose="判断用户是在问指标、查明细、问规则解释，还是提出敏感导出请求。",
            input_from=["user_question"],
            output="intent_result",
            tools=["rule_classifier", "llm_classifier"],
            risk_controls=["识别敏感字段", "识别不支持问题", "保留原始问题"],
            fallback="无法识别时返回 clarification_required，不进入 SQL 生成。",
            audit_fields=["question", "intent", "confidence"],
        ),
        WorkflowStep(
            step_id="context_retrieval",
            name="Schema 与知识检索",
            purpose="查找可用表、字段、指标口径和业务规则，为后续 SQL 或回答提供依据。",
            input_from=["intent_result"],
            output="retrieved_context",
            tools=["schema_catalog", "rag_retriever"],
            risk_controls=["按用户权限过滤 schema", "只返回可引用知识片段"],
            fallback="检索不到关键上下文时拒答或要求补充条件。",
            audit_fields=["matched_tables", "matched_docs", "permission_scope"],
        ),
        WorkflowStep(
            step_id="question_parse",
            name="问题结构化解析",
            purpose="把自然语言拆成指标、维度、时间范围、过滤条件和查询类型。",
            input_from=["intent_result", "retrieved_context"],
            output="parsed_question",
            tools=["question_parser"],
            risk_controls=["强制时间范围", "标记缺失指标", "标记敏感维度"],
            fallback="缺少关键条件时返回 clarification_required。",
            audit_fields=["metrics", "dimensions", "time_range", "risk_flags"],
        ),
        WorkflowStep(
            step_id="candidate_generation",
            name="候选 SQL 或回答计划生成",
            purpose="根据结构化问题生成候选 SQL，或者生成基于引用资料的回答计划。",
            input_from=["parsed_question", "retrieved_context"],
            output="candidate_action",
            tools=["sql_generator", "answer_planner"],
            risk_controls=["只生成 select 查询", "禁止拼接用户原始条件", "保留生成理由"],
            fallback="生成结果缺少表字段依据时拒答。",
            audit_fields=["candidate_sql", "answer_plan", "generation_reason"],
        ),
        WorkflowStep(
            step_id="validation",
            name="安全、权限、成本校验",
            purpose="在执行前检查 SQL、字段、权限、扫描范围和成本风险。",
            input_from=["candidate_action"],
            output="validation_result",
            tools=["sql_validator", "permission_checker", "cost_guard"],
            risk_controls=["敏感字段黑名单", "只读限制", "limit 约束", "分区过滤"],
            fallback="校验失败时返回 safely_blocked，并说明阻断原因。",
            audit_fields=["validation_status", "blocked_reasons", "estimated_cost"],
        ),
        WorkflowStep(
            step_id="execution",
            name="执行工具",
            purpose="只在校验通过后调用查询、检索或业务工具。",
            input_from=["validation_result"],
            output="tool_result",
            tools=["query_executor", "rag_reader"],
            risk_controls=["超时控制", "行数限制", "只读账号", "异常分类"],
            fallback="执行失败时进入失败分类，不允许编造结果。",
            audit_fields=["tool_name", "execution_status", "row_count", "error_type"],
        ),
        WorkflowStep(
            step_id="interpretation",
            name="结果解释与引用",
            purpose="把工具返回的结构化结果解释成业务能读懂的回答，并附带限制说明。",
            input_from=["tool_result", "retrieved_context"],
            output="business_answer",
            tools=["result_interpreter", "citation_builder"],
            risk_controls=["不得超出结果推断", "保留引用来源", "提示数据口径限制"],
            fallback="结果为空或口径不明时输出保守解释和追问建议。",
            audit_fields=["answer_summary", "citations", "limitations"],
        ),
        WorkflowStep(
            step_id="audit",
            name="审计记录",
            purpose="把问题、步骤、工具、SQL、校验、执行和最终回答串成可回放记录。",
            input_from=["business_answer", "validation_result", "tool_result"],
            output="audit_record",
            tools=["audit_storage"],
            risk_controls=["记录 request_id", "敏感字段脱敏", "审计写入失败告警"],
            fallback="审计写入失败时返回系统错误，不静默吞掉。",
            audit_fields=["request_id", "user_id", "steps", "final_status"],
        ),
    ]


def validate_workflow(steps: list[WorkflowStep]) -> list[str]:
    """检查工作流定义是否具备生产最低边界。

    这不是业务功能测试，而是结构检查：每一步必须有失败回退和审计字段。
    如果这些字段缺失，后续真实接模型时就很容易出现无法排查的黑盒行为。
    """

    errors: list[str] = []
    seen_ids: set[str] = set()
    for step in steps:
        if step.step_id in seen_ids:
            errors.append(f"duplicate step_id: {step.step_id}")
        seen_ids.add(step.step_id)
        if not step.fallback:
            errors.append(f"{step.step_id} missing fallback")
        if not step.audit_fields:
            errors.append(f"{step.step_id} missing audit_fields")
        if not step.risk_controls:
            errors.append(f"{step.step_id} missing risk_controls")
    return errors


def build_mermaid(steps: list[WorkflowStep]) -> str:
    """把结构化步骤转成 Mermaid 流程图。

    Mermaid 图适合放进 README 和学习笔记，面试讲项目时也能快速说明 Agent 不是黑盒，
    而是一条有校验、有回退、有审计的受控链路。
    """

    lines = ["flowchart TD"]
    previous_node = "U[用户问题]"
    lines.append(f"    {previous_node}")
    for step in steps:
        node_id = step.step_id.upper()
        lines.append(f"    {previous_node.split('[')[0]} --> {node_id}[{step.name}]")
        previous_node = f"{node_id}[{step.name}]"
        if step.step_id in {"validation", "execution"}:
            fallback_node = f"{node_id}_F[失败回退: {step.fallback}]"
            lines.append(f"    {node_id} -.异常或阻断.-> {fallback_node}")
    lines.append(f"    {previous_node.split('[')[0]} --> O[返回业务答案]")
    return "\n".join(lines) + "\n"


def build_report(steps: list[WorkflowStep], validation_errors: list[str]) -> str:
    """生成一份便于阅读的工作流报告。"""

    status = "通过" if not validation_errors else "失败"
    lines = [
        "# Day 43 Agent 工作流报告",
        "",
        f"- 步骤数：{len(steps)}",
        f"- 结构检查：{status}",
        "",
        "## 步骤清单",
        "",
        "| 步骤 | 作用 | 工具 | 失败回退 |",
        "|------|------|------|----------|",
    ]
    for step in steps:
        lines.append(
            f"| {step.name} | {step.purpose} | {', '.join(step.tools)} | {step.fallback} |"
        )
    if validation_errors:
        lines.extend(["", "## 检查问题", ""])
        lines.extend(f"- {error}" for error in validation_errors)
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 43 的本地练习产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    steps = build_workflow()
    validation_errors = validate_workflow(steps)

    WORKFLOW_JSON_PATH.write_text(
        json.dumps([asdict(step) for step in steps], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    WORKFLOW_MERMAID_PATH.write_text(build_mermaid(steps), encoding="utf-8")
    REPORT_PATH.write_text(build_report(steps, validation_errors), encoding="utf-8")

    print(f"workflow_steps={len(steps)}")
    print(f"validation_errors={len(validation_errors)}")
    print(f"json={WORKFLOW_JSON_PATH}")
    print(f"mermaid={WORKFLOW_MERMAID_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
