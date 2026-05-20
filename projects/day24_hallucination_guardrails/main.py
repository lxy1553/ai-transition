"""Day 24 - RAG 拒答与边界评估脚本。

这个脚本模拟生产 RAG 里的回答决策层：
先用规则识别敏感、越权、危险和模糊问题，再用检索置信度判断是否有足够依据。
它不调用真实 LLM，因为今天要练的是“什么时候不能让模型自由回答”。
"""

import json
from pathlib import Path
from typing import Optional, Union


PROJECT_DIR = Path(__file__).resolve().parent
RULES_PATH = PROJECT_DIR / "rules.json"
CASES_PATH = PROJECT_DIR / "cases.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "refusal_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "refusal_eval_report.md"


def load_json(path: Path) -> Union[dict, list]:
    """读取 JSON 文件。

    规则和样本都放在外部文件里，是为了让拒答策略可以被评审和修改。
    生产环境也通常不会把所有安全规则硬编码在业务函数里。
    """

    return json.loads(path.read_text(encoding="utf-8"))


def match_rule(question: str, rules: list[dict]) -> Optional[dict]:
    """按关键词匹配拒答或澄清规则。

    这里用简单关键词是为了可解释。
    真实系统会叠加权限系统、数据分类分级、意图识别和审计策略。
    """

    lowered = question.lower()
    for rule in rules:
        for keyword in rule["keywords"]:
            if keyword.lower() in lowered:
                return rule
    return None


def decide(case: dict, config: dict) -> dict:
    """对单条问题做 answer、refuse 或 clarify 决策。"""

    rule = match_rule(case["question"], config["rules"])
    if rule:
        return {
            "decision": rule["decision"],
            "reason": rule["reason"],
            "matched_rule": rule["id"],
        }

    if not case["retrieved_sources"]:
        return {
            "decision": "refuse",
            "reason": "没有检索到可引用资料，不能基于猜测生成答案。",
            "matched_rule": "no_evidence",
        }

    if case["max_retrieval_score"] < config["low_confidence_threshold"]:
        return {
            "decision": "clarify",
            "reason": "检索置信度偏低，需要用户补充更明确的问题或业务范围。",
            "matched_rule": "low_confidence",
        }

    return {
        "decision": "answer",
        "reason": "检索到了可引用资料，且没有触发敏感、越权或危险规则。",
        "matched_rule": "grounded_answer",
    }


def evaluate(cases: list[dict], config: dict) -> list[dict]:
    """批量评估拒答策略。

    每条样本都有 expected_decision，用来检查策略是否和预期一致。
    生产里会把这类样本加入回归测试，避免规则调整后误放行或误拒。
    """

    evaluations = []
    for case in cases:
        result = decide(case, config)
        evaluations.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_decision": case["expected_decision"],
                "actual_decision": result["decision"],
                "passed": result["decision"] == case["expected_decision"],
                "reason": result["reason"],
                "matched_rule": result["matched_rule"],
                "max_retrieval_score": case["max_retrieval_score"],
                "retrieved_sources": case["retrieved_sources"],
                "risk_tags": case["risk_tags"],
            }
        )
    return evaluations


def summarize(evaluations: list[dict]) -> dict:
    """汇总拒答策略评估指标。"""

    total = len(evaluations)
    passed = [item for item in evaluations if item["passed"]]
    refusal_cases = [item for item in evaluations if item["expected_decision"] == "refuse"]
    refusal_passed = [
        item
        for item in refusal_cases
        if item["actual_decision"] == item["expected_decision"]
    ]
    return {
        "total": total,
        "passed": len(passed),
        "accuracy": round(len(passed) / total, 4) if total else 0,
        "refusal_total": len(refusal_cases),
        "refusal_accuracy": (
            round(len(refusal_passed) / len(refusal_cases), 4)
            if refusal_cases
            else 0
        ),
        "failed_cases": [item for item in evaluations if not item["passed"]],
    }


def build_report(summary: dict, evaluations: list[dict]) -> str:
    """生成 Markdown 评估报告。"""

    lines = [
        "# Day 24 - RAG 拒答策略评估报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- passed: {summary['passed']}",
        f"- accuracy: {summary['accuracy']}",
        f"- refusal_total: {summary['refusal_total']}",
        f"- refusal_accuracy: {summary['refusal_accuracy']}",
        "",
        "## 明细",
        "",
        "| id | expected | actual | passed | matched_rule | reason |",
        "|----|----------|--------|--------|--------------|--------|",
    ]

    for item in evaluations:
        passed = "yes" if item["passed"] else "no"
        lines.append(
            "| {id} | {expected} | {actual} | {passed} | {rule} | {reason} |".format(
                id=item["id"],
                expected=item["expected_decision"],
                actual=item["actual_decision"],
                passed=passed,
                rule=item["matched_rule"],
                reason=item["reason"],
            )
        )

    if summary["failed_cases"]:
        lines.extend(["", "## 待排查样本", ""])
        for item in summary["failed_cases"]:
            lines.append(
                f"- {item['id']}: expected={item['expected_decision']}, "
                f"actual={item['actual_decision']}"
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    """运行拒答策略评估，并写入 JSON 和 Markdown 报告。"""

    config = load_json(RULES_PATH)
    cases = load_json(CASES_PATH)
    evaluations = evaluate(cases, config)
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
