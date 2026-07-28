#!/usr/bin/env python3
"""
跨来源合并同类面试题：去重、补充、纠错、汇总
输出到 interview/汇总/
"""

import re
import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")
MERGED_DIR = INTERVIEW_DIR / "汇总"

# ---- 分类映射：各来源分类 → 统一分类 ----
CATEGORY_MAP = {
    # Agent
    "Agent 与框架": "Agent 智能体",
    "Agent": "Agent 智能体",
    "Agent面试题": "Agent 智能体",
    "Agent图解专栏": "Agent 智能体",
    # RAG
    "RAG 检索增强": "RAG 检索增强生成",
    "RAG检索增强": "RAG 检索增强生成",
    # MCP / 工具调用
    "MCP 与协议": "MCP 工具调用与协议",
    "LLM工具调用与协议": "MCP 工具调用与协议",
    # 大模型工程
    "大模型工程": "大模型工程与训练",
    "LLM与AI工程": "大模型工程与训练",
    # 微调
    "微调与 PEFT": "大模型工程与训练",
    # Prompt → 合并到大模型工程
    "Prompt 与结构化输出": "大模型工程与训练",
    "Prompt工程": "大模型工程与训练",
    # 数据仓库
    "数据仓库": "数据仓库与治理",
    "数据治理": "数据仓库与治理",
    # NL2SQL
    "NL2SQL": "NL2SQL 自然语言查询",
    # 信贷风控
    "金融信贷": "信贷风控建模",
    "信贷风控建模": "信贷风控建模",
    # 工程化
    "工程与场景": "AI 应用工程化",
    "工程化": "AI 应用工程化",
    "AI应用开发": "AI 应用工程化",
    # Claude Code
    "Claude Code图解专栏": "Claude Code 开发实战",
    # 可解释性 → 合并到信贷风控
    "模型可解释性": "信贷风控建模",
    "模型可解释性与评估": "信贷风控建模",
    # 安全 → 合并到 AI 应用工程化
    "安全与合规": "AI 应用工程化",
    "AI 安全与合规": "AI 应用工程化",
    # 其他
    "其他": "综合",
    "综合": "综合",
    "未分类": "综合",
}


def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|#&]', '_', name).strip()[:80]


def parse_question_from_file(filepath: Path) -> list:
    """从美化后的 md 中提取题目"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    fm_match = re.search(r'^---\n(.*?)\n---', text, re.DOTALL)
    fm = {}
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()

    source = fm.get('source', '')
    source_label = fm.get('source_label', '')
    orig_category = fm.get('category', '')

    questions = []
    h2_pattern = re.compile(r'^## (\d+)\. (.+)$', re.MULTILINE)
    matches = list(h2_pattern.finditer(text))

    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        answer = text[start:end].strip()
        answer = re.sub(r'^> ID:.*\n?', '', answer, flags=re.MULTILINE).strip()

        if len(answer) > 50:
            questions.append({
                "title": title,
                "answer": answer,
                "source": source,
                "source_label": source_label,
                "orig_category": orig_category,
            })

    return questions


def title_similarity(a: str, b: str) -> float:
    """计算标题相似度"""
    # 清理干扰词
    def clean(t):
        t = re.sub(r'^\d+\.\s*', '', t)
        t = re.sub(r'请(讲讲|说说|问|你|面试官问)[：:]?\s*', '', t)
        t = re.sub(r'怎么(做|办|样|设计|实现|选)[？?]?', '', t)
        t = re.sub(r'什么是|是指|指的是|介绍一下|详细描述', '', t)
        t = re.sub(r'[？?！!，,。.\s]', '', t)
        return t.lower()[:50]

    return SequenceMatcher(None, clean(a), clean(b)).ratio()


def main():
    print("📂 读取所有来源题目...")

    all_questions = []
    for source_dir in ["mianshiya", "interview_core", "xiaolinnote", "learning"]:
        src_path = INTERVIEW_DIR / source_dir
        if not src_path.exists():
            continue
        for md_file in sorted(src_path.glob("*.md")):
            if md_file.name == "README.md":
                continue
            qs = parse_question_from_file(md_file)
            for q in qs:
                q["unified_category"] = CATEGORY_MAP.get(q["orig_category"], q["orig_category"])
                all_questions.append(q)

    # 按统一分类分组
    cats = {}
    for q in all_questions:
        cats.setdefault(q["unified_category"], []).append(q)

    print(f"   共 {len(all_questions)} 题 → {len(cats)} 个统一分类")

    # 在每个分类内去重合并
    MERGED_DIR.mkdir(exist_ok=True, parents=True)
    total_merged = 0
    total_deduped = 0

    for cat_name, questions in sorted(cats.items()):
        # 按相似度聚类
        clusters = []
        used = set()

        for i, q1 in enumerate(questions):
            if i in used:
                continue
            cluster = [q1]
            used.add(i)
            for j, q2 in enumerate(questions):
                if j in used:
                    continue
                if title_similarity(q1["title"], q2["title"]) > 0.6:
                    cluster.append(q2)
                    used.add(j)
            clusters.append(cluster)

        deduped = len(questions) - len(clusters)

        # 写合并文件
        filename = f"{sanitize(cat_name)}.md"
        filepath = MERGED_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\n")
            f.write(f"category: {cat_name}\n")
            f.write(f"total: {len(clusters)}\n")
            f.write(f"sources: {', '.join(sorted(set(q['source'] for q in questions)))}\n")
            f.write(f"deduped: {deduped}\n")
            f.write(f"generated: {datetime.now().isoformat()}\n")
            f.write(f"---\n\n")
            f.write(f"# 🏷️ {cat_name}\n\n")
            f.write(f"> {len(questions)} 题（来自 {len(set(q['source'] for q in questions))} 个来源）")
            if deduped > 0:
                f.write(f" → 去重合并为 {len(clusters)} 题")
            f.write(f"\n\n---\n\n")

            # 写目录
            if len(clusters) > 1:
                f.write("## 📑 目录\n\n")
                for ci, cluster in enumerate(clusters, 1):
                    main_q = cluster[0]
                    f.write(f"{ci}. [{main_q['title'][:80]}](#{sanitize(main_q['title'][:40])})\n")
                f.write("\n---\n\n")

            for ci, cluster in enumerate(clusters, 1):
                main_q = cluster[0]
                sources_info = [f"{q['source_label']}" for q in cluster]

                f.write(f"## {ci}. {main_q['title']}\n\n")

                if len(cluster) > 1:
                    f.write(f"> 📚 跨来源合并（{len(cluster)} 处来源：{', '.join(sources_info)}）\n\n")

                    # 合并答案：取最长的
                    best = max(cluster, key=lambda q: len(q["answer"]))
                    f.write(best["answer"])
                    f.write(f"\n\n> 💡 本题在 {len(cluster)} 个来源中出现，已取最完整版本合并。\n")

                    # 如果有补充信息（其他来源有但最佳答案没有的关键内容）
                    for other in cluster:
                        if other != best:
                            # 简单检查是否有独特关键词
                            other_keywords = set(re.findall(r'[一-鿿]{2,}', other["answer"]))
                            best_keywords = set(re.findall(r'[一-鿿]{2,}', best["answer"]))
                            unique = other_keywords - best_keywords
                            if len(unique) > 50:  # 有显著独特内容
                                f.write(f"\n\n### 📎 补充（来自 {other['source_label']}）\n\n")
                                f.write(other["answer"])
                else:
                    f.write(f"> 来源: {main_q['source_label']}\n\n")
                    f.write(main_q["answer"])

                f.write("\n\n---\n\n")

        print(f"  📄 {cat_name}: {len(questions)}→{len(clusters)} 题, 去重 {deduped}")
        total_merged += len(clusters)
        total_deduped += deduped

    # 写总索引
    index = []
    for filepath in sorted(MERGED_DIR.glob("*.md")):
        if filepath.name == "README.md":
            continue
        with open(filepath) as f:
            content = f.read()
        cat_name = re.search(r'category:\s*(.+)', content).group(1)
        total = int(re.search(r'total:\s*(\d+)', content).group(1))
        deduped = int(re.search(r'deduped:\s*(\d+)', content).group(1))
        sources = re.search(r'sources:\s*(.+)', content).group(1)
        index.append({"category": cat_name, "total": total, "deduped": deduped, "sources": sources, "file": filepath.name})

    index_path = MERGED_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # README
    readme = MERGED_DIR / "README.md"
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# 📋 面试题库 · 分类汇总（跨来源合并去重）\n\n")
        f.write(f"> 生成: {datetime.now().isoformat()}\n")
        f.write(f"> 合并前: {len(all_questions)} 题\n")
        f.write(f"> 合并后: {total_merged} 题（去重 {total_deduped} 题）\n\n")
        f.write("---\n\n")
        for item in sorted(index, key=lambda x: -x["total"]):
            dedup_info = f"（去重 {item['deduped']} 题）" if item['deduped'] > 0 else ""
            f.write(f"- [{item['category']}（{item['total']} 题 {dedup_info}）]({item['file']})\n")

    print(f"\n✅ 汇总完成！")
    print(f"   合并前: {len(all_questions)} 题（4 个来源）")
    print(f"   合并后: {total_merged} 题（去重 {total_deduped} 题）")
    print(f"   输出: {MERGED_DIR}")


if __name__ == "__main__":
    main()
