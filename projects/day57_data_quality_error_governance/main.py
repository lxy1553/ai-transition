"""
Day 57 - 数据质量 + 错误治理：主线脚本

功能：
  1. 加载数据质量规则清单（quality_rules.json）
  2. 加载质量 bad case 回归样例（quality_bad_cases.json）
  3. 模拟 Agent 对不同质量状态的回答策略
  4. 输出 JSON 和 Markdown 两份治理报告
  5. 为 Day 58 审计存储准备结构化字段设计

设计前提：
  - 不调用真实 LLM，而是用规则匹配模拟质量状态判断和回答策略
  - 所有质量检查结果都是结构化的，便于后续路由和审计
  - bad case 覆盖了 Day 56 评测中的空分区、延迟、口径冲突等场景
"""

import json
import os
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(PROJECT_DIR, "quality_rules.json")
BAD_CASES_PATH = os.path.join(PROJECT_DIR, "quality_bad_cases.json")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
JSON_OUTPUT = os.path.join(OUTPUT_DIR, "quality_governance_results.json")
MD_OUTPUT = os.path.join(OUTPUT_DIR, "quality_governance_report.md")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 审计字段设计（为 Day 58 服务化 + 审计存储准备）
# ---------------------------------------------------------------------------
AUDIT_FIELDS_DESIGN = {
    "request_level": {
        "request_id": "str — 请求唯一标识，用于全链路追踪",
        "trace_id": "str — 分布式追踪 ID，串联 Agent → 工具 → 数据源",
        "timestamp": "str (ISO 8601) — 请求时间",
        "user_question": "str — 用户原始问题",
        "agent_intent": "str — Agent 识别的意图类型",
    },
    "quality_check_level": {
        "quality_status": "enum: quality_ok | quality_warning | quality_blocked",
        "triggered_rules": "list[str] — 触发的质量规则 ID 列表",
        "quality_detail": "dict — 每条触发规则的详细检查结果",
        "data_freshness": "str — 数据新鲜度描述（如 'dt=2026-06-10, ETL completed'）",
        "completeness_score": "float 0.0-1.0 — 数据完整度评分",
        "duplication_rate": "float — 重复率（如有）",
    },
    "decision_level": {
        "action": "enum: normal_answer | degraded_answer | blocked_answer",
        "confidence": "float 0.0-1.0 — Agent 回答可信度",
        "degradation_reason": "str — 降级原因（quality_warning 时必填）",
        "block_reason": "str — 阻断原因（quality_blocked 时必填）",
        "suggestions": "list[str] — 给用户的排查建议",
    },
    "regression_level": {
        "bad_case_id": "str — 关联的 bad case ID",
        "regression_check_passed": "bool — 本次回答是否通过该 bad case 断言",
        "linked_day56_scenario": "str — 关联的 Day 56 评测场景",
    },
}

# ---------------------------------------------------------------------------
# 质量模拟：给每条规则生成一个模拟检查结果
# ---------------------------------------------------------------------------
def simulate_quality_checks(rules: list[dict]) -> list[dict]:
    """
    模拟对每条规则的检查。
    生产环境中这里会去查分区状态、去重计数、空值比例、ETL 任务状态等。
    这里用预设的模拟结果来演示质量状态路由逻辑。
    """
    # 模拟不同规则触发不同状态：
    # DQ-009（空分区）→ blocked, DQ-006（幂等失败）→ blocked
    # DQ-001,002,003,004,005,007,008,010 → warning
    quality_blocked_rules = {"DQ-006", "DQ-009"}
    simulation_results = []
    for rule in rules:
        rule_id = rule["rule_id"]
        if rule_id in quality_blocked_rules:
            actual_status = "quality_blocked"
        else:
            actual_status = "quality_warning"
        simulation_results.append({
            "rule_id": rule_id,
            "rule_name": rule["rule_name"],
            "category": rule["category"],
            "risk_level": rule["risk_level"],
            "warehouse_type": rule["warehouse_type"],
            "quality_status": actual_status,
            "triggered": True,  # 模拟全部触发，展示完整质量路由
            "detail": f"模拟触发：{rule['trigger_condition'][:60]}...",
            "recommended_action": rule["action"],
        })
    return simulation_results


# ---------------------------------------------------------------------------
# 质量状态汇总与路由决策
# ---------------------------------------------------------------------------
def aggregate_quality_status(check_results: list[dict]) -> dict:
    """汇总所有质量检查结果，输出统一的质量状态和路由决策"""
    blocked_rules = [r for r in check_results if r["quality_status"] == "quality_blocked"]
    warning_rules = [r for r in check_results if r["quality_status"] == "quality_warning"]
    ok_rules = [r for r in check_results if r["quality_status"] == "quality_ok"]

    if blocked_rules:
        overall_status = "quality_blocked"
        overall_action = "blocked_answer"
        overall_reason = f"存在 {len(blocked_rules)} 条阻断级质量问题：{', '.join(r['rule_id'] for r in blocked_rules)}"
    elif warning_rules:
        overall_status = "quality_warning"
        overall_action = "degraded_answer"
        overall_reason = f"存在 {len(warning_rules)} 条警告级质量问题，需要降级说明"
    else:
        overall_status = "quality_ok"
        overall_action = "normal_answer"
        overall_reason = "所有质量检查通过，数据可信"

    return {
        "overall_status": overall_status,
        "overall_action": overall_action,
        "overall_reason": overall_reason,
        "blocked_count": len(blocked_rules),
        "warning_count": len(warning_rules),
        "ok_count": len(ok_rules),
        "blocked_rules": [r["rule_id"] for r in blocked_rules],
        "warning_rules": [r["rule_id"] for r in warning_rules],
        "confidence": max(0.3, 1.0 - len(warning_rules) * 0.06 - len(blocked_rules) * 0.3),
    }


# ---------------------------------------------------------------------------
# Bad Case 回归验证
# ---------------------------------------------------------------------------
def run_bad_case_regression(bad_cases: list[dict], check_results: list[dict]) -> list[dict]:
    """
    对每个 bad case 执行回归验证：
    - 找到关联的质量规则
    - 检查规则的质量状态是否匹配 bad case 的预期状态
    - 检查必要的断言是否可满足（这里做结构化校验，不做 NLP）
    """
    regression_results = []
    for bc in bad_cases:
        linked_rule_id = bc["linked_rule_id"]
        # 找到对应的检查结果
        matched_check = next(
            (r for r in check_results if r["rule_id"] == linked_rule_id), None
        )
        if matched_check is None:
            regression_results.append({
                "case_id": bc["case_id"],
                "title": bc["title"],
                "linked_rule_id": linked_rule_id,
                "expected_status": bc["expected_quality_status"],
                "actual_status": "unknown",
                "status_match": False,
                "regression_passed": False,
                "note": "未找到对应的质量检查结果",
            })
            continue

        status_match = matched_check["quality_status"] == bc["expected_quality_status"]
        # 断言检查：结构化验证（生产环境可扩展为 NLP 检查）
        assertions = bc.get("regression_assertions", [])
        assertions_count = len(assertions)
        # 模拟：状态匹配则断言可检查，实际验证需要 Agent 输出文本
        regression_passed = status_match

        regression_results.append({
            "case_id": bc["case_id"],
            "title": bc["title"],
            "linked_rule_id": linked_rule_id,
            "linked_day56_scenario": bc.get("linked_day56_scenario", ""),
            "expected_status": bc["expected_quality_status"],
            "actual_status": matched_check["quality_status"],
            "status_match": status_match,
            "regression_passed": regression_passed,
            "assertions_to_check": assertions,
            "assertions_count": assertions_count,
            "note": "状态匹配，所有断言可结构化校验" if status_match else f"状态不匹配：期望 {bc['expected_quality_status']}，实际 {matched_check['quality_status']}",
        })

    return regression_results


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------
def generate_json_report(
    check_results: list[dict],
    aggregation: dict,
    regression_results: list[dict],
    audit_design: dict,
) -> dict:
    """生成 JSON 格式的完整治理报告"""
    tz_bj = timezone(timedelta(hours=8))
    now = datetime.now(tz_bj).isoformat()
    return {
        "report_meta": {
            "project": "Day 57 - 数据质量 + 错误治理",
            "generated_at": now,
            "description": "金融信贷离线/实时仓库数据质量治理报告：包含质量规则检查、路由决策、bad case 回归和审计字段设计",
        },
        "quality_check_summary": aggregation,
        "quality_check_details": check_results,
        "bad_case_regression": {
            "total": len(regression_results),
            "passed": sum(1 for r in regression_results if r["regression_passed"]),
            "failed": sum(1 for r in regression_results if not r["regression_passed"]),
            "details": regression_results,
        },
        "audit_field_design": audit_design,
        "next_steps": {
            "day58": "将 quality_status、triggered_rules、confidence 等字段写入审计存储，支持 request_id + trace_id 回放",
            "day59": "在统一仓库 Agent 入口中集成质量检查节点，根据 quality_status 路由到正常/降级/阻断分支",
            "day60": "在演示中展示：正常回答 → 降级说明 → 阻断排查 三种质量状态下的 Agent 行为差异",
        },
    }


def generate_markdown_report(json_report: dict) -> str:
    """生成 Markdown 格式的治理报告"""
    meta = json_report["report_meta"]
    summary = json_report["quality_check_summary"]
    details = json_report["quality_check_details"]
    regression = json_report["bad_case_regression"]
    audit = json_report["audit_field_design"]

    lines = []
    lines.append(f"# Day 57 - 数据质量 + 错误治理报告")
    lines.append(f"")
    lines.append(f"**生成时间：** {meta['generated_at']}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 一、质量检查汇总")
    lines.append(f"")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 整体质量状态 | **{summary['overall_status']}** |")
    lines.append(f"| 路由决策 | **{summary['overall_action']}** |")
    lines.append(f"| 阻断规则数 | {summary['blocked_count']} |")
    lines.append(f"| 警告规则数 | {summary['warning_count']} |")
    lines.append(f"| 正常规则数 | {summary['ok_count']} |")
    lines.append(f"| Agent 可信度 | {summary['confidence']:.2f} |")
    lines.append(f"| 决策原因 | {summary['overall_reason']} |")
    lines.append(f"")
    if summary["blocked_rules"]:
        lines.append(f"**阻断规则：** {', '.join(summary['blocked_rules'])}")
        lines.append(f"")
    if summary["warning_rules"]:
        lines.append(f"**警告规则：** {', '.join(summary['warning_rules'])}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 二、质量规则检查明细")
    lines.append(f"")
    lines.append(f"| 规则 ID | 规则名称 | 分类 | 风险等级 | 仓库类型 | 质量状态 |")
    lines.append(f"|---------|----------|------|----------|----------|----------|")
    for d in details:
        status_emoji = "🔴" if d["quality_status"] == "quality_blocked" else "🟡"
        lines.append(
            f"| {d['rule_id']} | {d['rule_name']} | {d['category']} | {d['risk_level']} | {d['warehouse_type']} | {status_emoji} {d['quality_status']} |"
        )
    lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 三、错误分类与修复建议")
    lines.append(f"")
    lines.append(f"### 需阻断（quality_blocked）")
    lines.append(f"")
    blocked = [d for d in details if d["quality_status"] == "quality_blocked"]
    for d in blocked:
        lines.append(f"- **{d['rule_id']} {d['rule_name']}**（{d['category']}）")
        lines.append(f"  - 风险等级：{d['risk_level']}")
        lines.append(f"  - 触发条件：{d['detail']}")
        lines.append(f"  - 处理动作：{d['recommended_action']}")
        lines.append(f"")
    lines.append(f"")
    lines.append(f"### 需降级（quality_warning）")
    lines.append(f"")
    warning = [d for d in details if d["quality_status"] == "quality_warning"]
    for d in warning:
        lines.append(f"- **{d['rule_id']} {d['rule_name']}**（{d['category']}）")
        lines.append(f"  - 风险等级：{d['risk_level']}")
        lines.append(f"  - 触发条件：{d['detail']}")
        lines.append(f"  - 处理动作：{d['recommended_action']}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 四、Bad Case 回归验证")
    lines.append(f"")
    lines.append(f"| Bad Case | 关联规则 | 关联 Day 56 场景 | 预期状态 | 实际状态 | 回归结果 |")
    lines.append(f"|----------|----------|-----------------|----------|----------|----------|")
    for r in regression["details"]:
        passed_emoji = "✅" if r["regression_passed"] else "❌"
        lines.append(
            f"| {r['case_id']} {r['title']} | {r['linked_rule_id']} | {r.get('linked_day56_scenario', '')} | {r['expected_status']} | {r['actual_status']} | {passed_emoji} |"
        )
    lines.append(f"")
    lines.append(f"**回归汇总：** {regression['passed']}/{regression['total']} 通过")

    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 五、审计字段设计（Day 58 准备）")
    lines.append(f"")
    for level_name, fields in audit.items():
        level_label = level_name.replace("_level", "").replace("_", " ").title()
        lines.append(f"### {level_label} 字段")
        lines.append(f"")
        lines.append(f"| 字段名 | 说明 |")
        lines.append(f"|--------|------|")
        for field_name, field_desc in fields.items():
            lines.append(f"| `{field_name}` | {field_desc} |")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 六、后续步骤")
    lines.append(f"")
    for day, step in json_report["next_steps"].items():
        lines.append(f"- **{day}**：{step}")
    lines.append(f"")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    """Day 57 数据质量治理主流程"""
    print("=" * 60)
    print("Day 57 - 数据质量 + 错误治理")
    print("=" * 60)
    print()

    # 1. 加载规则清单
    print("[1/5] 加载数据质量规则清单...")
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules_data = json.load(f)
    rules = rules_data["rules"]
    print(f"      已加载 {len(rules)} 条质量规则")
    print(f"      覆盖分类：{', '.join(rules_data['error_category_summary'].keys())}")
    print()

    # 2. 加载 bad case
    print("[2/5] 加载质量 Bad Case 回归样例...")
    with open(BAD_CASES_PATH, "r", encoding="utf-8") as f:
        bad_cases_data = json.load(f)
    bad_cases = bad_cases_data["bad_cases"]
    print(f"      已加载 {len(bad_cases)} 条 bad case")
    print(f"      关联 Day 56 场景：{', '.join(bad_cases_data['meta']['linked_day56_scenarios'])}")
    print()

    # 3. 模拟质量检查
    print("[3/5] 执行质量检查...")
    check_results = simulate_quality_checks(rules)
    aggregation = aggregate_quality_status(check_results)
    print(f"      整体状态：{aggregation['overall_status']}")
    print(f"      路由决策：{aggregation['overall_action']}")
    print(f"      阻断 {aggregation['blocked_count']} 条 / 警告 {aggregation['warning_count']} 条")
    print(f"      Agent 可信度：{aggregation['confidence']:.2f}")
    print()

    # 4. Bad case 回归
    print("[4/5] 执行 Bad Case 回归验证...")
    regression_results = run_bad_case_regression(bad_cases, check_results)
    passed = sum(1 for r in regression_results if r["regression_passed"])
    print(f"      回归结果：{passed}/{len(regression_results)} 通过")
    for r in regression_results:
        emoji = "✅" if r["regression_passed"] else "❌"
        print(f"      {emoji} {r['case_id']}: {r['title']} — {r['note']}")
    print()

    # 5. 生成报告
    print("[5/5] 生成治理报告...")
    json_report = generate_json_report(
        check_results, aggregation, regression_results, AUDIT_FIELDS_DESIGN
    )
    md_report = generate_markdown_report(json_report)

    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f"      JSON 报告 → {JSON_OUTPUT}")

    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"      Markdown 报告 → {MD_OUTPUT}")
    print()

    print("=" * 60)
    print("Day 57 治理报告已生成")
    print(f"  整体质量状态：{aggregation['overall_status']}")
    print(f"  路由决策：{aggregation['overall_action']}")
    print(f"  Bad case 回归：{passed}/{len(regression_results)} 通过")
    print(f"  审计字段设计：4 层 {sum(len(v) for v in AUDIT_FIELDS_DESIGN.values())} 个字段")
    print("=" * 60)


if __name__ == "__main__":
    main()
