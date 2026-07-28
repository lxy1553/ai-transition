#!/usr/bin/env python3
"""
将所有题库按来源→分类，每个分类一个 md 文件，存入 interview/ 目录
"""

import re
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("/Users/lxy/Documents/ai_transition/docs")
INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")

SOURCES = {
    "mianshiya": {
        "file": DOCS_DIR / "mianshiya_llm_interview_questions.md",
        "split_pattern": r'\n(?=### (?:Q\d+|附-\d+))',
        "id_pattern": r'###\s+([QXL]\d+|附-\d+)',
        "label": "面试鸭题库",
    },
    "interview_core": {
        "file": DOCS_DIR / "interview_core_questions.md",
        "split_pattern": r'(?=<a id="q\d+">)',
        "id_pattern": r'<a id="(q\d+)">',
        "label": "核心题库",
    },
    "xiaolinnote": {
        "file": DOCS_DIR / "xiaolinnote_questions.md",
        "split_pattern": r'\n(?=### X\d+)',
        "id_pattern": r'###\s+([QXL]\d+)',
        "label": "小林面试笔记",
    },
    "learning": {
        "file": DOCS_DIR / "learning_review_questions.md",
        "split_pattern": r'\n(?=### L\d+)',
        "id_pattern": r'###\s+([QXL]\d+)',
        "label": "学习复习计划",
    },
}


def sanitize(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|#&]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:80]


def parse_generic(block: str, source: str):
    id_match = re.search(r'###\s+([QXL]\d+|附-\d+)', block)
    if not id_match:
        return None
    qid = id_match.group(1)
    cat_match = re.search(r'\*\*分类：\*\*\s*(.+)', block)
    category = cat_match.group(1).strip() if cat_match else "未分类"
    title_match = re.search(r'\*\*题目：\*\*\s*(.+)', block)
    if not title_match:
        return None
    title = title_match.group(1).strip()
    ans_start = block.find("**参考答案：**")
    if ans_start == -1:
        return None
    answer = block[ans_start + len("**参考答案：**"):].strip()
    answer = re.sub(r'\n---\s*$', '', answer).strip()
    return {"id": qid, "source": source, "category": category, "title": title, "answer": answer}


def parse_core(block: str):
    id_match = re.search(r'<a id="(q\d+)">', block)
    if not id_match:
        return None
    qid = id_match.group(1).upper()
    title_match = re.search(r'##\s+Q\d+\s*[：:]\s*(.+)', block)
    if not title_match:
        return None
    title = title_match.group(1).strip()
    t = title.lower()
    if any(w in t for w in ['rag', '检索', '召回', 'chunk', 'embed', '向量']):
        category = "RAG检索增强"
    elif any(w in t for w in ['nl2sql', 'sql', '查询', '表', '字段']):
        category = "NL2SQL"
    elif any(w in t for w in ['agent', '工具', '编排', '工作流', 'tool']):
        category = "Agent"
    elif any(w in t for w in ['仓库', 'ods', 'dwd', 'dws', 'ads', '离线', '实时', '分区']):
        category = "数据仓库"
    elif any(w in t for w in ['微调', 'peft', 'lora', 'fine']):
        category = "微调与PEFT"
    elif any(w in t for w in ['prompt', '提示', '结构化']):
        category = "Prompt工程"
    elif any(w in t for w in ['权限', '安全', '敏感', '脱敏', '阻断']):
        category = "安全与合规"
    elif any(w in t for w in ['服务', 'api', 'docker', '部署', '配置']):
        category = "工程化"
    elif any(w in t for w in ['血缘', '指标', '告警', '监控']):
        category = "数据治理"
    elif any(w in t for w in ['信贷', '风控', '授信', '放款', '还款', '逾期']):
        category = "金融信贷"
    else:
        category = "综合"
    ans_start = block.find("### 回答")
    if ans_start == -1:
        return None
    answer = block[ans_start + len("### 回答"):].strip()
    answer = re.sub(r'\n---\s*$', '', answer).strip()
    return {"id": qid, "source": "interview_core", "category": category, "title": title, "answer": answer}


def main():
    # 清空旧文件
    if INTERVIEW_DIR.exists():
        for item in list(INTERVIEW_DIR.iterdir()):
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    INTERVIEW_DIR.mkdir(parents=True, exist_ok=True)

    all_categories = {}  # {source_key: {category: [questions]}}
    total = 0

    for source_key, cfg in SOURCES.items():
        source_label = cfg["label"]
        filepath = cfg["file"]

        if not filepath.exists():
            print(f"⚠️ 跳过 {source_label}: 文件不存在")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        blocks = re.split(cfg["split_pattern"], text)
        blocks = [b for b in blocks if re.search(cfg["id_pattern"], b)]

        cats = {}
        for block in blocks:
            q = parse_core(block) if source_key == "interview_core" else parse_generic(block, source_key)
            if not q or not q["title"] or len(q["answer"]) < 50:
                continue
            cats.setdefault(q["category"], []).append(q)

        all_categories[source_key] = cats
        total += sum(len(v) for v in cats.values())
        print(f"  ✅ {source_label}: {sum(len(v) for v in cats.values())} 题, {len(cats)} 个分类")

    # 写入文件：每个来源一个子目录，每个分类一个 md 文件
    print(f"\n📝 写入文件...")

    for source_key, cats in all_categories.items():
        source_label = SOURCES[source_key]["label"]
        src_dir = INTERVIEW_DIR / source_key
        src_dir.mkdir(exist_ok=True)

        for cat_name, questions in sorted(cats.items()):
            filename = f"{sanitize(cat_name)}.md"
            filepath = src_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                # 文件头
                f.write(f"---\n")
                f.write(f"source: {source_key}\n")
                f.write(f"source_label: {source_label}\n")
                f.write(f"category: {cat_name}\n")
                f.write(f"count: {len(questions)}\n")
                f.write(f"generated: {datetime.now().isoformat()}\n")
                f.write(f"---\n\n")
                f.write(f"# {source_label} · {cat_name}\n\n")
                f.write(f"> 共 {len(questions)} 题\n\n")
                f.write(f"---\n\n")

                for i, q in enumerate(questions, 1):
                    f.write(f"## {i}. {q['title']}\n\n")
                    f.write(f"> ID: `{q['id']}`\n\n")
                    f.write(q['answer'])
                    f.write(f"\n\n---\n\n")

            print(f"  📄 {source_key}/{filename} ({len(questions)} 题)")

    # 写总索引
    index = []
    for source_key, cats in all_categories.items():
        for cat_name, questions in cats.items():
            index.append({
                "source": source_key,
                "source_label": SOURCES[source_key]["label"],
                "category": cat_name,
                "count": len(questions),
                "file": f"{source_key}/{sanitize(cat_name)}.md",
            })

    index_path = INTERVIEW_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 写 README
    readme_path = INTERVIEW_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# AI 面试题库\n\n")
        f.write(f"> 生成时间: {datetime.now().isoformat()}\n")
        f.write(f"> 总题数: {total} 题\n")
        f.write(f"> 总分类: {len(index)} 个\n\n")
        f.write("---\n\n")
        for source_key, cfg in SOURCES.items():
            cats = all_categories.get(source_key, {})
            if not cats:
                continue
            src_total = sum(len(v) for v in cats.values())
            f.write(f"## {cfg['label']}（{src_total} 题 / {len(cats)} 个分类）\n\n")
            for cat_name, questions in sorted(cats.items()):
                f.write(f"- [{cat_name}（{len(questions)} 题）]({source_key}/{sanitize(cat_name)}.md)\n")
            f.write("\n")

    file_count = sum(1 for _ in INTERVIEW_DIR.rglob("*.md") if _.name != "README.md")
    print(f"\n✅ 完成！共 {total} 题 → {file_count} 个 md 文件 → {INTERVIEW_DIR}")


if __name__ == "__main__":
    main()
