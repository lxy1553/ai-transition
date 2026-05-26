"""Day 27 - RAG 演示稳定性检查。

这个脚本直接复用 Day 20 RAG API 的核心函数，不需要启动 uvicorn。
目标是演示前快速检查：索引是否就绪、成功样例是否稳定、边界错误是否有清楚结果。
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

from pydantic import ValidationError


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
DAY20_DIR = ROOT_DIR / "projects/day20_rag_api"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "demo_stability_results.json"
REPORT_PATH = OUTPUT_DIR / "demo_stability_report.md"

# Day 20 的 regression.py 也是通过当前目录导入 main。
# 这里把 Day 20 目录加入 sys.path，确保本脚本可以直接复用同一套 API 组装逻辑。
sys.path.insert(0, str(DAY20_DIR))

from main import AskRequest, DB_PATH, build_response, health  # noqa: E402


SUCCESS_CASES = [
    "RAG 知识入库怎么设计？",
    "RAG 为什么要返回引用来源？",
    "SQL 解释助手能检查哪些风险？",
]


def model_to_dict(model) -> dict:
    """兼容 Pydantic 1 和 2 的模型导出。"""

    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def passed_case(name: str, detail: str, payload: Optional[dict] = None) -> dict:
    """生成通过结果，保持报告结构统一。"""

    return {
        "name": name,
        "passed": True,
        "detail": detail,
        "payload": payload or {},
    }


def failed_case(name: str, detail: str, payload: Optional[dict] = None) -> dict:
    """生成失败结果，避免异常直接中断整个检查。"""

    return {
        "name": name,
        "passed": False,
        "detail": detail,
        "payload": payload or {},
    }


def check_index_ready() -> dict:
    """检查 Day 17 索引是否存在。"""

    payload = health()
    if payload["index_ready"] and DB_PATH.exists():
        return passed_case("index_ready", "Day 17 索引已存在，RAG API 具备检索前置条件。", payload)
    return failed_case("index_ready", "Day 17 索引不存在，请先运行入库脚本。", payload)


def check_success_cases() -> list[dict]:
    """检查固定成功问题是否返回稳定字段。"""

    results = []
    for index, question in enumerate(SUCCESS_CASES, start=1):
        request = AskRequest(question=question, top_k=3, user_id="demo_user")
        response = build_response(
            request=request,
            request_id=f"demo_success_{index:03d}",
            started_at=time.time(),
        )
        payload = model_to_dict(response)
        has_required_fields = all(
            [
                payload["answer"],
                payload["request_id"],
                isinstance(payload["citations"], list),
                payload["confidence"] >= 0,
                payload["latency_ms"] >= 0,
            ]
        )
        has_citations = len(payload["citations"]) > 0
        if has_required_fields and has_citations:
            results.append(
                passed_case(
                    f"success_case_{index}",
                    "成功样例返回 answer、citations、request_id、confidence 和 latency。",
                    {
                        "question": question,
                        "citations": len(payload["citations"]),
                        "confidence": payload["confidence"],
                        "latency_ms": payload["latency_ms"],
                    },
                )
            )
        else:
            results.append(
                failed_case(
                    f"success_case_{index}",
                    "成功样例缺少关键字段或 citations 为空。",
                    payload,
                )
            )
    return results


def check_no_answer_case() -> dict:
    """检查无相关资料时是否明确返回 cannot_answer_reason。"""

    request = AskRequest(question="蓝色香蕉发票制度是什么？", top_k=3, user_id="demo_user")
    response = build_response(
        request=request,
        request_id="demo_no_answer_001",
        started_at=time.time(),
    )
    payload = model_to_dict(response)
    if payload["cannot_answer_reason"] == "no_relevant_chunks" and not payload["citations"]:
        return passed_case("no_answer_case", "无相关资料时能明确返回 no_relevant_chunks。", payload)
    return failed_case("no_answer_case", "无相关资料时没有按预期进入拒答边界。", payload)


def check_validation_case(name: str, kwargs: dict, expected_text: str) -> dict:
    """检查 Pydantic 参数校验是否能拦住非法请求。"""

    try:
        AskRequest(**kwargs)
    except ValidationError as exc:
        return passed_case(
            name,
            expected_text,
            {"error_count": len(exc.errors()), "first_error": exc.errors()[0]},
        )
    return failed_case(name, "非法请求没有被参数校验拦住。", kwargs)


def summarize(results: list[dict]) -> dict:
    """汇总稳定性检查结果。"""

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0,
    }


def build_report(summary: dict, results: list[dict]) -> str:
    """生成 Markdown 演示稳定性报告。"""

    lines = [
        "# Day 27 - RAG 演示稳定性检查报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- passed: {summary['passed']}",
        f"- failed: {summary['failed']}",
        f"- pass_rate: {summary['pass_rate']}",
        "",
        "## 明细",
        "",
        "| check | passed | detail |",
        "|-------|--------|--------|",
    ]
    for item in results:
        passed = "yes" if item["passed"] else "no"
        lines.append(f"| {item['name']} | {passed} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## 演示建议",
            "",
            "- 先跑本检查脚本，再启动 HTTP API 做正式演示。",
            "- 成功样例优先选能稳定返回 citations 的问题。",
            "- 主动准备 no-answer 或 bad case，用 request_id、citations 和 retrieved_chunks 讲排查思路。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行演示稳定性检查，并写入 JSON 和 Markdown 报告。"""

    results = [
        check_index_ready(),
        *check_success_cases(),
        check_no_answer_case(),
        check_validation_case(
            name="empty_question_validation",
            kwargs={"question": "", "top_k": 3},
            expected_text="空问题会被请求模型校验拦截。",
        ),
        check_validation_case(
            name="top_k_validation",
            kwargs={"question": "RAG 为什么要返回引用来源？", "top_k": 99},
            expected_text="top_k 越界会被请求模型校验拦截。",
        ),
    ]
    summary = summarize(results)
    payload = {"summary": summary, "results": results}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report(summary, results), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
