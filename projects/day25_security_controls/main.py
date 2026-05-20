"""Day 25 - RAG 权限与敏感信息控制检查脚本。

这个脚本模拟生产 RAG 的安全决策：
先判断用户是否有权限访问 chunk，再检查问题和内容是否包含敏感信息。
它的目标是让安全控制变成可测试的规则，而不是只靠 prompt 口头约束模型。
"""

import json
import re
from pathlib import Path
from typing import Optional


PROJECT_DIR = Path(__file__).resolve().parent
POLICY_PATH = PROJECT_DIR / "policy.json"
CASES_PATH = PROJECT_DIR / "cases.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "security_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "security_eval_report.md"


def load_json(path: Path):
    """读取策略或测试样本。"""

    return json.loads(path.read_text(encoding="utf-8"))


def has_role_access(user_role: str, allowed_roles: list[str]) -> bool:
    """判断用户角色是否在 chunk 允许访问的角色列表里。"""

    return user_role in allowed_roles


def match_blocked_keyword(question: str, blocked_keywords: list[str]) -> Optional[str]:
    """检查用户问题是否包含越权或高风险意图。"""

    for keyword in blocked_keywords:
        if keyword in question:
            return keyword
    return None


def find_sensitive_matches(text: str, patterns: list[dict]) -> list[dict]:
    """扫描文本中的手机号、邮箱、密钥等敏感信息。"""

    matches = []
    for item in patterns:
        if re.search(item["pattern"], text, flags=re.IGNORECASE):
            matches.append(
                {
                    "name": item["name"],
                    "reason": item["reason"],
                }
            )
    return matches


def decide(case: dict, policy: dict) -> dict:
    """对单条样本做 allow、deny 或 mask 决策。"""

    blocked_keyword = match_blocked_keyword(case["question"], policy["blocked_keywords"])
    if blocked_keyword:
        return {
            "decision": "deny",
            "reason": f"问题包含高风险意图：{blocked_keyword}",
            "sensitive_matches": [],
        }

    if not has_role_access(case["user_role"], case["chunk_allowed_roles"]):
        return {
            "decision": "deny",
            "reason": "用户角色无权访问该 chunk，不能进入模型上下文。",
            "sensitive_matches": [],
        }

    sensitive_matches = find_sensitive_matches(
        case["chunk_preview"],
        policy["sensitive_patterns"],
    )
    if sensitive_matches:
        return {
            "decision": "mask",
            "reason": "chunk 内容包含敏感信息，需要脱敏后才能返回或引用。",
            "sensitive_matches": sensitive_matches,
        }

    return {
        "decision": "allow",
        "reason": "用户有权限，且未命中敏感信息或高风险意图。",
        "sensitive_matches": [],
    }


def evaluate(cases: list[dict], policy: dict) -> list[dict]:
    """批量评估安全策略是否符合预期。"""

    evaluations = []
    for case in cases:
        result = decide(case, policy)
        evaluations.append(
            {
                "id": case["id"],
                "user_role": case["user_role"],
                "question": case["question"],
                "expected_decision": case["expected_decision"],
                "actual_decision": result["decision"],
                "passed": result["decision"] == case["expected_decision"],
                "reason": result["reason"],
                "sensitive_matches": result["sensitive_matches"],
                "chunk_security_level": case["chunk_security_level"],
                "chunk_allowed_roles": case["chunk_allowed_roles"],
            }
        )
    return evaluations


def summarize(evaluations: list[dict]) -> dict:
    """汇总安全检查指标。"""

    total = len(evaluations)
    passed = [item for item in evaluations if item["passed"]]
    deny_cases = [item for item in evaluations if item["expected_decision"] == "deny"]
    mask_cases = [item for item in evaluations if item["expected_decision"] == "mask"]
    return {
        "total": total,
        "passed": len(passed),
        "accuracy": round(len(passed) / total, 4) if total else 0,
        "deny_total": len(deny_cases),
        "mask_total": len(mask_cases),
        "failed_cases": [item for item in evaluations if not item["passed"]],
    }


def build_report(summary: dict, evaluations: list[dict]) -> str:
    """生成 Markdown 安全检查报告。"""

    lines = [
        "# Day 25 - RAG 权限与敏感信息安全检查报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- passed: {summary['passed']}",
        f"- accuracy: {summary['accuracy']}",
        f"- deny_total: {summary['deny_total']}",
        f"- mask_total: {summary['mask_total']}",
        "",
        "## 明细",
        "",
        "| id | role | expected | actual | passed | reason |",
        "|----|------|----------|--------|--------|--------|",
    ]

    for item in evaluations:
        passed = "yes" if item["passed"] else "no"
        lines.append(
            "| {id} | {role} | {expected} | {actual} | {passed} | {reason} |".format(
                id=item["id"],
                role=item["user_role"],
                expected=item["expected_decision"],
                actual=item["actual_decision"],
                passed=passed,
                reason=item["reason"],
            )
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    """运行安全策略检查，并写入报告。"""

    policy = load_json(POLICY_PATH)
    cases = load_json(CASES_PATH)
    evaluations = evaluate(cases, policy)
    summary = summarize(evaluations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps({"summary": summary, "evaluations": evaluations}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(summary, evaluations), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
