"""
评测脚本 —— 跑一遍评测集，算准确率，暴露 bad case

小白理解：这是给系统"考试"。提前准备好 10 道题 + 标准答案，
让系统做一遍，看它答对几道、答错几道、哪道错了、为什么错。

为什么评测是 RAG/NL2SQL 项目的"灵魂"？
  没有评测，你说"我的系统效果很好"，谁信？全是自我感觉。
  有了评测，你能拿出硬数字："意图识别准确率 90%，指标解析准确率 85%"。
  面试官最想听的就是这个数字 + "我怎么做评测的"。

评测三件事（面试必讲）：
  1. 评测集怎么建的（覆盖哪些场景）
  2. 准确率怎么算的（意图识别、指标解析分别算）
  3. bad case 怎么归因的（哪一步错了 → 怎么改）

运行方式（在 credit_risk_control_system 目录下）：
    python3 scripts/eval_qa.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai_assistant.llm_client import create_llm
from src.ai_assistant.schema_catalog import SchemaCatalog
from src.ai_assistant.pipeline import QAPipeline


def load_cases() -> list[dict]:
    """加载评测集。"""
    cases_path = Path(__file__).resolve().parent.parent / "config" / "eval_cases.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def evaluate(pipeline, cases: list[dict]) -> dict:
    """
    跑评测，返回评测报告。

    评两个核心指标 + 按维度分组：
      1. 意图识别准确率：系统分对意图了吗
      2. 指标解析准确率：系统抽对指标了吗
      3. 按 dimension 分组统计（看出哪个维度是短板）
    """
    intent_correct = 0
    indicator_correct = 0
    indicator_total = 0
    bad_cases = []
    # 按维度统计
    dim_stats = {}   # {dimension: {intent_correct, intent_total, indicator_correct, indicator_total}}

    for case in cases:
        dim = case.get("dimension", "未分类")
        if dim not in dim_stats:
            dim_stats[dim] = {"intent_correct": 0, "intent_total": 0,
                              "indicator_correct": 0, "indicator_total": 0}
        dim_stats[dim]["intent_total"] += 1

        # 调内部方法拿意图（评测需要直接看中间结果）
        intent_result = pipeline.intent_classifier.classify(case["query"])
        actual_intent = intent_result.intent

        # ── 评意图识别 ──
        if actual_intent == case["expected_intent"]:
            intent_correct += 1
            dim_stats[dim]["intent_correct"] += 1
        else:
            bad_cases.append({
                "id": case["id"], "query": case["query"],
                "dimension": dim, "eval_dim": "意图识别",
                "expected": case["expected_intent"], "actual": actual_intent,
            })

        # ── 评指标解析（仅标注了 expected_indicator 的"指标查询"类）──
        if case["expected_indicator"] is not None:
            indicator_total += 1
            dim_stats[dim]["indicator_total"] += 1
            rewritten = pipeline.query_rewriter.rewrite(case["query"])
            actual_indicator = rewritten.indicators[0] if rewritten.indicators else None
            if actual_indicator == case["expected_indicator"]:
                indicator_correct += 1
                dim_stats[dim]["indicator_correct"] += 1
            else:
                bad_cases.append({
                    "id": case["id"], "query": case["query"],
                    "dimension": dim, "eval_dim": "指标解析",
                    "expected": case["expected_indicator"], "actual": actual_indicator,
                })

    intent_acc = intent_correct / len(cases) if cases else 0
    indicator_acc = indicator_correct / indicator_total if indicator_total else 0

    return {
        "intent_accuracy": intent_acc,
        "intent_correct": intent_correct,
        "intent_total": len(cases),
        "indicator_accuracy": indicator_acc,
        "indicator_correct": indicator_correct,
        "indicator_total": indicator_total,
        "dim_stats": dim_stats,
        "bad_cases": bad_cases,
    }


def main():
    print("=" * 60)
    print("AI 数据问答系统 评测")
    print("=" * 60)

    # 组装系统（用 Mock LLM，保证评测可复现、不花钱）
    catalog = SchemaCatalog()
    llm = create_llm(catalog=catalog)   # 把 catalog 传给 Mock，让它能识别同义词
    pipeline = QAPipeline(llm=llm, catalog=catalog)

    # 加载评测集
    cases = load_cases()
    print(f"\n📚 评测集共 {len(cases)} 道题\n")

    # 跑评测
    report = evaluate(pipeline, cases)

    # ── 打印评测报告 ──
    print("=" * 60)
    print("📊 评测报告")
    print("=" * 60)
    print(f"\n意图识别准确率：{report['intent_correct']}/{report['intent_total']} "
          f"= {report['intent_accuracy']:.0%}")
    print(f"指标解析准确率：{report['indicator_correct']}/{report['indicator_total']} "
          f"= {report['indicator_accuracy']:.0%}")

    # ── 按维度分组统计 ──
    print("\n" + "-" * 60)
    print("按维度分组（看出短板在哪）：")
    print("-" * 60)
    print(f"{'维度':<12} {'意图':>10} {'指标解析':>12}")
    for dim, stats in sorted(report["dim_stats"].items()):
        i_acc = stats["intent_correct"] / stats["intent_total"] if stats["intent_total"] else 0
        ind_acc = (stats["indicator_correct"] / stats["indicator_total"]
                   if stats["indicator_total"] else 0)
        print(f"{dim:<12} {stats['intent_correct']}/{stats['intent_total']} "
              f"({i_acc:.0%})  {stats['indicator_correct']}/{stats['indicator_total']} "
              f"({ind_acc:.0%})")

    # ── 打印 bad case ──
    if report["bad_cases"]:
        print(f"\n🔴 Bad Cases（{len(report['bad_cases'])} 个）：")
        for bc in report["bad_cases"]:
            print(f"\n  [{bc['id']}] {bc['query']}")
            print(f"    维度：{bc['dimension']} / {bc['eval_dim']}")
            print(f"    预期：{bc['expected']}")
            print(f"    实际：{bc['actual']}")
    else:
        print("\n✅ 没有 bad case，全部通过")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
