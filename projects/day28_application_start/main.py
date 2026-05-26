"""Day 28 - 试投准备检查脚本。

这个脚本把简历、项目、面试题库和投递记录拆成可检查项。
它不负责真实投递，而是先判断“能不能开始小批量试投”。
生产化思路和 RAG 项目一样：先有清单、证据和状态，再做下一步动作。
"""

import json
from collections import Counter
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CHECKLIST_PATH = PROJECT_DIR / "checklist.json"
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "application_readiness_results.json"
REPORT_PATH = OUTPUT_DIR / "application_readiness_report.md"


def load_checklist() -> list[dict]:
    """读取试投准备清单。"""

    return json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))


def summarize(items: list[dict]) -> dict:
    """汇总 ready 和 todo 数量。"""

    counts = Counter(item["status"] for item in items)
    total = len(items)
    ready = counts.get("ready", 0)
    return {
        "total": total,
        "ready": ready,
        "todo": counts.get("todo", 0),
        "ready_rate": round(ready / total, 4) if total else 0,
        "can_start_small_batch": ready >= 5,
    }


def build_report(summary: dict, items: list[dict]) -> str:
    """生成 Markdown 试投准备报告。"""

    decision = "可以开始小批量试投" if summary["can_start_small_batch"] else "先补齐关键材料"
    lines = [
        "# Day 28 - 试投准备检查报告",
        "",
        "## 总览",
        "",
        f"- total: {summary['total']}",
        f"- ready: {summary['ready']}",
        f"- todo: {summary['todo']}",
        f"- ready_rate: {summary['ready_rate']}",
        f"- decision: {decision}",
        "",
        "## 明细",
        "",
        "| id | category | status | item | evidence |",
        "|----|----------|--------|------|----------|",
    ]

    for item in items:
        lines.append(
            "| {id} | {category} | {status} | {name} | {evidence} |".format(
                id=item["id"],
                category=item["category"],
                status=item["status"],
                name=item["item"],
                evidence=item["evidence"],
            )
        )

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 补齐真实简历中的公司、项目指标、职责和联系方式。",
            "- 确认项目仓库或压缩包可以安全发送。",
            "- 从最新岗位里筛出 5-10 个高匹配岗位做首轮试投。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """运行试投准备检查，并写入 JSON 和 Markdown 报告。"""

    items = load_checklist()
    summary = summarize(items)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps({"summary": summary, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(summary, items), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
