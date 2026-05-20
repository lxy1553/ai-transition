"""Day 20 - RAG API 回归测试脚本。

这个脚本不启动 HTTP 服务，而是直接调用 API 背后的核心函数跑 5 个固定问题。
用途是快速检查：是否有答案、是否有 citations、是否有 request_id。
后续改 top-k、query rewrite、权限过滤时，可以先跑这个脚本确认主链路没坏。
"""

import json
import time
from pathlib import Path

from main import AskRequest, ROOT_DIR, build_response


OUTPUT_PATH = Path(__file__).resolve().parent / "output/regression_results.json"

QUESTIONS = [
    "RAG 知识入库怎么设计？",
    "RAG 为什么要返回引用来源？",
    "SQL 解释助手能检查哪些风险？",
    "query rewrite 解决什么问题？",
    "RAG 召回质量差怎么排查？",
]


def run_case(index: int, question: str) -> dict:
    """运行单条回归问题。

    每条问题都走和 `/rag/ask` 一样的响应组装逻辑。
    这样不用启动服务，也能检查 API 返回结构是否稳定。
    """

    request = AskRequest(question=question, top_k=3, user_id="local_regression")
    response = build_response(
        request=request,
        request_id=f"reg_{index:03d}",
        started_at=time.time(),
    )
    # 兼容 Pydantic 1 和 2：不同版本导出模型字典的方法不一样。
    # 这样回归脚本不会因为依赖版本变化而报警或失败。
    payload = response.model_dump() if hasattr(response, "model_dump") else response.dict()
    payload["has_answer"] = bool(payload["answer"])
    payload["has_citations"] = bool(payload["citations"])
    payload["has_request_id"] = bool(payload["request_id"])
    return payload


def main() -> None:
    """运行 5 个 Day 20 回归问题，并保存结果。"""

    results = [run_case(index=index, question=question) for index, question in enumerate(QUESTIONS, start=1)]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Day 20 RAG API Regression ===")
    for item in results:
        print(
            f"{item['request_id']} | citations={len(item['citations'])} "
            f"confidence={item['confidence']:.3f} | {item['question']}"
        )
    print(f"output: {OUTPUT_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
