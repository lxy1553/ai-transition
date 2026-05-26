"""Day 26 - RAG 性能与成本优化实验。

这个脚本不用真实 LLM，也不用联网。
它用固定样本模拟 RAG 请求，把 baseline 和优化策略的 token、成本、缓存命中情况做对比。
这样做的目的，是先把“成本来自哪里”讲清楚，再考虑接入真实模型计费。
"""

import hashlib
import json
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "cost_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "cost_optimization_report.md"

INPUT_COST_PER_1K = 0.002
OUTPUT_COST_PER_1K = 0.006
BASE_OUTPUT_TOKENS = 180
MIN_RELEVANCE = 0.62
MAX_CONTEXT_TOKENS = 520


REQUESTS = [
    {
        "id": "req_001",
        "user_role": "analyst",
        "question": "RAG 为什么需要引用来源？",
        "retrieved_chunks": [
            {
                "chunk_id": "c001",
                "source": "notes/day18_rag_retrieval_citations.md",
                "score": 0.91,
                "text": "RAG 回答需要返回 citations，方便用户知道答案来自哪份资料，也方便排查错误。",
            },
            {
                "chunk_id": "c002",
                "source": "notes/day18_rag_retrieval_citations.md",
                "score": 0.88,
                "text": "引用来源要包含 source_path、chunk_id 和 position，方便追溯检索链路。",
            },
            {
                "chunk_id": "c003",
                "source": "notes/day05_fastapi.md",
                "score": 0.39,
                "text": "FastAPI 可以用来创建 health 接口和业务 API。",
            },
        ],
    },
    {
        "id": "req_002",
        "user_role": "analyst",
        "question": "RAG 为什么需要引用来源？",
        "retrieved_chunks": [
            {
                "chunk_id": "c001",
                "source": "notes/day18_rag_retrieval_citations.md",
                "score": 0.91,
                "text": "RAG 回答需要返回 citations，方便用户知道答案来自哪份资料，也方便排查错误。",
            },
            {
                "chunk_id": "c004",
                "source": "notes/day18_rag_retrieval_citations.md",
                "score": 0.83,
                "text": "如果答案没有引用来源，用户很难判断回答是基于资料还是模型猜测。",
            },
        ],
    },
    {
        "id": "req_003",
        "user_role": "engineer",
        "question": "怎么降低 RAG 的 token 成本？",
        "retrieved_chunks": [
            {
                "chunk_id": "c101",
                "source": "notes/day19_rag_retrieval_optimization.md",
                "score": 0.89,
                "text": "可以通过 top-k 调整、query rewrite、去重和 rerank 改善召回质量。",
            },
            {
                "chunk_id": "c102",
                "source": "notes/day26_rag_performance_cost.md",
                "score": 0.94,
                "text": "成本优化要控制进入 prompt 的 chunk 数量，记录 input token、output token 和缓存命中率。",
            },
            {
                "chunk_id": "c103",
                "source": "notes/day26_rag_performance_cost.md",
                "score": 0.92,
                "text": "重复问题可以缓存召回结果或答案，但缓存 key 要包含权限、知识库版本和 prompt 版本。",
            },
            {
                "chunk_id": "c104",
                "source": "notes/day01_environment_setup.md",
                "score": 0.35,
                "text": "Day 1 的重点是搭建环境和确定岗位方向。",
            },
        ],
    },
    {
        "id": "req_004",
        "user_role": "engineer",
        "question": "怎么降低 RAG 的 token 成本？",
        "retrieved_chunks": [
            {
                "chunk_id": "c102",
                "source": "notes/day26_rag_performance_cost.md",
                "score": 0.94,
                "text": "成本优化要控制进入 prompt 的 chunk 数量，记录 input token、output token 和缓存命中率。",
            },
            {
                "chunk_id": "c103",
                "source": "notes/day26_rag_performance_cost.md",
                "score": 0.92,
                "text": "重复问题可以缓存召回结果或答案，但缓存 key 要包含权限、知识库版本和 prompt 版本。",
            },
        ],
    },
    {
        "id": "req_005",
        "user_role": "analyst",
        "question": "RAG 权限过滤为什么不能只靠 prompt？",
        "retrieved_chunks": [
            {
                "chunk_id": "c201",
                "source": "notes/day25_security_controls.md",
                "score": 0.95,
                "text": "prompt 只能约束模型行为，不能替代权限系统和数据治理。",
            },
            {
                "chunk_id": "c202",
                "source": "notes/day25_security_controls.md",
                "score": 0.9,
                "text": "如果敏感 chunk 已经进入上下文，模型可能直接引用、总结或推断出敏感内容。",
            },
        ],
    },
]


def normalize_question(question: str) -> str:
    """把问题规范化，避免空格和大小写导致缓存 miss。"""

    return re.sub(r"\s+", "", question).lower()


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数。

    真实生产要用模型对应 tokenizer。
    这里为了本地练习，只用一个稳定的近似算法：中文字符按 1 个 token，英文单词按 1 个 token。
    """

    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    english_words = re.findall(r"[A-Za-z0-9_]+", text)
    punctuation = re.findall(r"[，。；：,.!?]", text)
    return len(chinese_chars) + len(english_words) + max(1, len(punctuation) // 2)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """按固定单价估算成本，便于比较优化前后差异。"""

    input_cost = input_tokens / 1000 * INPUT_COST_PER_1K
    output_cost = output_tokens / 1000 * OUTPUT_COST_PER_1K
    return round(input_cost + output_cost, 6)


def chunk_fingerprint(chunk: dict) -> str:
    """为 chunk 生成去重指纹。

    生产里通常用 chunk_id、source、内容 hash 和版本号组合。
    本实验用 source + 文本 hash，模拟同一资料被重复召回时只保留一次。
    """

    raw = f"{chunk['source']}::{chunk['text']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def baseline_context(chunks: list[dict]) -> list[dict]:
    """baseline 策略：召回多少基本就塞多少，不过滤低相关资料。"""

    return chunks


def optimized_context(chunks: list[dict]) -> list[dict]:
    """优化策略：过滤低分、按内容去重，并遵守 token budget。"""

    selected = []
    seen = set()
    used_tokens = 0
    for chunk in sorted(chunks, key=lambda item: item["score"], reverse=True):
        if chunk["score"] < MIN_RELEVANCE:
            continue

        fingerprint = chunk_fingerprint(chunk)
        if fingerprint in seen:
            continue

        chunk_tokens = estimate_tokens(chunk["text"])
        if used_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
            continue

        selected.append(chunk)
        seen.add(fingerprint)
        used_tokens += chunk_tokens

    return selected


def evaluate_request(request: dict, strategy: str, cache: dict) -> dict:
    """评估单次请求的 token、成本和缓存状态。"""

    cache_key = f"{request['user_role']}::{normalize_question(request['question'])}::kb_v1::prompt_v1"
    if strategy == "optimized" and cache_key in cache:
        cached = cache[cache_key]
        return {
            "request_id": request["id"],
            "strategy": strategy,
            "cache_hit": True,
            "context_chunks": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0,
            "reused_from": cached["request_id"],
        }

    context_chunks = (
        optimized_context(request["retrieved_chunks"])
        if strategy == "optimized"
        else baseline_context(request["retrieved_chunks"])
    )
    context_text = "\n".join(chunk["text"] for chunk in context_chunks)
    input_tokens = estimate_tokens(request["question"]) + estimate_tokens(context_text)
    output_tokens = BASE_OUTPUT_TOKENS
    estimated_cost = estimate_cost(input_tokens, output_tokens)

    result = {
        "request_id": request["id"],
        "strategy": strategy,
        "cache_hit": False,
        "context_chunks": len(context_chunks),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": estimated_cost,
        "sources": [chunk["source"] for chunk in context_chunks],
    }

    if strategy == "optimized":
        cache[cache_key] = result

    return result


def evaluate_strategy(strategy: str) -> list[dict]:
    """批量评估某个策略。"""

    cache = {}
    return [evaluate_request(request, strategy, cache) for request in REQUESTS]


def summarize(results: list[dict]) -> dict:
    """汇总 token、成本和缓存命中指标。"""

    total_requests = len(results)
    total_cost = sum(item["estimated_cost"] for item in results)
    total_input_tokens = sum(item["input_tokens"] for item in results)
    total_output_tokens = sum(item["output_tokens"] for item in results)
    cache_hits = sum(1 for item in results if item["cache_hit"])
    return {
        "total_requests": total_requests,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "total_estimated_cost": round(total_cost, 6),
        "avg_context_chunks": round(
            sum(item["context_chunks"] for item in results) / total_requests,
            2,
        ),
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / total_requests, 4),
    }


def compare(baseline: dict, optimized: dict) -> dict:
    """比较 baseline 和优化策略的节省效果。"""

    saved_tokens = baseline["total_tokens"] - optimized["total_tokens"]
    saved_cost = baseline["total_estimated_cost"] - optimized["total_estimated_cost"]
    return {
        "saved_tokens": saved_tokens,
        "saved_cost": round(saved_cost, 6),
        "token_reduction_rate": round(saved_tokens / baseline["total_tokens"], 4),
        "cost_reduction_rate": round(saved_cost / baseline["total_estimated_cost"], 4),
    }


def build_report(payload: dict) -> str:
    """生成 Markdown 成本优化报告。"""

    baseline = payload["summary"]["baseline"]
    optimized = payload["summary"]["optimized"]
    comparison = payload["summary"]["comparison"]

    lines = [
        "# Day 26 - RAG 成本优化实验报告",
        "",
        "## 总览",
        "",
        "| strategy | total_tokens | estimated_cost | avg_context_chunks | cache_hit_rate |",
        "|----------|--------------|----------------|--------------------|----------------|",
        (
            f"| baseline | {baseline['total_tokens']} | {baseline['total_estimated_cost']} | "
            f"{baseline['avg_context_chunks']} | {baseline['cache_hit_rate']} |"
        ),
        (
            f"| optimized | {optimized['total_tokens']} | {optimized['total_estimated_cost']} | "
            f"{optimized['avg_context_chunks']} | {optimized['cache_hit_rate']} |"
        ),
        "",
        "## 节省效果",
        "",
        f"- saved_tokens: {comparison['saved_tokens']}",
        f"- saved_cost: {comparison['saved_cost']}",
        f"- token_reduction_rate: {comparison['token_reduction_rate']}",
        f"- cost_reduction_rate: {comparison['cost_reduction_rate']}",
        "",
        "## 明细",
        "",
        "| request_id | strategy | cache_hit | context_chunks | input_tokens | output_tokens | cost |",
        "|------------|----------|-----------|----------------|--------------|---------------|------|",
    ]

    for item in payload["results"]:
        lines.append(
            "| {request_id} | {strategy} | {cache_hit} | {context_chunks} | "
            "{input_tokens} | {output_tokens} | {estimated_cost} |".format(**item)
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "优化策略通过低分过滤、上下文去重、token budget 和缓存减少了模型输入。",
            "生产环境还需要接入真实 tokenizer、真实模型价格、延迟统计、权限维度和知识库版本失效机制。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行成本优化实验，并写入 JSON 和 Markdown 报告。"""

    baseline_results = evaluate_strategy("baseline")
    optimized_results = evaluate_strategy("optimized")
    baseline_summary = summarize(baseline_results)
    optimized_summary = summarize(optimized_results)
    payload = {
        "pricing": {
            "input_cost_per_1k": INPUT_COST_PER_1K,
            "output_cost_per_1k": OUTPUT_COST_PER_1K,
            "note": "这是本地实验用的固定估算单价，不代表真实模型价格。",
        },
        "summary": {
            "baseline": baseline_summary,
            "optimized": optimized_summary,
            "comparison": compare(baseline_summary, optimized_summary),
        },
        "results": baseline_results + optimized_results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report(payload), encoding="utf-8")

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
