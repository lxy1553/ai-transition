"""Day 11 - Tool Use 流程 Demo。

这个脚本模拟“模型选择工具、工具执行确定性逻辑、再组织最终回答”的流程。
用途是理解 AI 应用里 LLM 不应该直接做所有事情，安全和确定性的部分要交给工具层。
"""

from dataclasses import dataclass
import re
from typing import Any


SAMPLE_SQL = """
select city, count(distinct user_id) as active_users
from user_events
where dt between '2026-05-01' and '2026-05-07'
  and event_name = 'app_open'
group by city
"""


@dataclass
class ToolCall:
    """模型决定调用哪个工具，以及传什么参数。

    真实 function calling 返回的也是类似结构：工具名 + 参数。
    这样程序才能知道下一步应该执行哪个确定性函数。
    """

    name: str
    arguments: dict[str, str]


def check_sql_risk(sql: str, dialect: str = "hive") -> dict[str, Any]:
    """用确定性规则检查 SQL 风险。

    SQL 安全不能完全依赖模型判断。像 select *、缺少 where、缺少 dt 分区这类风险，
    用规则检查更稳定，也更容易测试和解释。
    """
    lowered = sql.lower()
    normalized = " ".join(lowered.split())
    risks: list[str] = []
    suggestions: list[str] = []
    missing_context: list[str] = []

    # select * 会读取所有字段，可能带来性能浪费，也可能把敏感字段暴露出去。
    if "select *" in normalized:
        risks.append("使用 select * 会读取不必要字段。")
        suggestions.append("只选择业务需要的字段。")

    # 没有 where 的查询在大表上可能扫全表，是数仓里非常常见的性能风险。
    if not re.search(r"\bwhere\b", normalized):
        risks.append("缺少 where 条件，可能触发全表扫描。")
        suggestions.append("补充时间范围、分区或业务过滤条件。")

    # dt 经常是数仓分区字段，缺少它通常意味着扫描范围无法收敛。
    if "dt" not in lowered:
        risks.append("未发现 dt 分区条件。")
        suggestions.append("确认是否需要按 dt 分区过滤。")

    if "group by" in normalized:
        risks.append("group by 可能带来聚合开销。")
        suggestions.append("确认分组字段基数，必要时先过滤再聚合。")

    # 指标名出现时，需要业务口径作为上下文，否则 SQL 语法对也可能业务错。
    if "active_users" in lowered:
        missing_context.append("active_users 活跃用户业务口径")

    risk_level = "low"
    if len(risks) >= 2 or missing_context:
        risk_level = "medium"
    if "select *" in normalized and not re.search(r"\bwhere\b", normalized):
        risk_level = "high"

    return {
        "dialect": dialect,
        "risk_level": risk_level,
        "can_publish": risk_level == "low" and not missing_context,
        "risks": risks or ["未发现明显 SQL 风险。"],
        "missing_context": missing_context,
        "suggestions": suggestions or ["建议结合表结构、数据量和执行计划继续确认。"],
    }


def choose_tool(user_input: str) -> ToolCall:
    """根据用户输入选择工具。

    当前 Demo 只有一个 SQL 风险工具，所以直接返回它。
    真实 Agent 里会根据问题类型选择检索、SQL 校验、数据库查询等不同工具。
    """
    return ToolCall(
        name="check_sql_risk",
        arguments={
            "sql": user_input,
            "dialect": "hive",
        },
    )


def build_final_answer(tool_result: dict[str, Any]) -> str:
    """把工具结果整理成人能读懂的回答。

    工具层返回结构化结果，适合程序判断。
    最终回答要把风险、缺少上下文和建议解释清楚，方便用户理解和执行。
    """
    lines = [
        f"风险等级：{tool_result['risk_level']}",
        f"是否允许上线：{'是' if tool_result['can_publish'] else '否'}",
        "风险：",
    ]

    for risk in tool_result["risks"]:
        lines.append(f"- {risk}")

    if tool_result["missing_context"]:
        lines.append("缺少上下文：")
        for item in tool_result["missing_context"]:
            lines.append(f"- {item}")

    lines.append("建议：")
    for suggestion in tool_result["suggestions"]:
        lines.append(f"- {suggestion}")

    return "\n".join(lines)


def main() -> None:
    """运行一次完整 Tool Use 流程。

    顺序是：用户输入 -> 选择工具 -> 执行工具 -> 基于工具结果生成最终回答。
    """
    print("=== User Input ===")
    print(SAMPLE_SQL.strip())
    print()

    tool_call = choose_tool(SAMPLE_SQL)
    print("=== Tool Call ===")
    print(f"name: {tool_call.name}")
    print(f"arguments: {tool_call.arguments}")
    print()

    if tool_call.name != "check_sql_risk":
        raise ValueError(f"Unsupported tool: {tool_call.name}")

    tool_result = check_sql_risk(**tool_call.arguments)
    print("=== Tool Result ===")
    print(tool_result)
    print()

    print("=== Final Answer ===")
    print(build_final_answer(tool_result))


if __name__ == "__main__":
    main()
