#!/usr/bin/env python3
"""
将所有题库按来源→分类→单题md文件，重组到 interview/ 目录
"""

import re
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("/Users/lxy/Documents/ai_transition/docs")
INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")

# 4 个题库来源
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
    """清理文件名"""
    name = re.sub(r'[\\/*?:"<>|#&]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:80]


def parse_generic(block: str, source: str):
    """解析 mianshiya/xiaolinnote/learning 格式的 block"""
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

    return {
        "id": qid,
        "source": source,
        "category": category,
        "title": title,
        "answer": answer,
    }


def parse_core(block: str):
    """解析 interview_core 格式的 block（HTML 锚点）"""
    id_match = re.search(r'<a id="(q\d+)">', block)
    if not id_match:
        return None
    qid = id_match.group(1).upper()

    title_match = re.search(r'##\s+Q\d+\s*[：:]\s*(.+)', block)
    if not title_match:
        return None
    title = title_match.group(1).strip()

    # 从标题推断分类
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

    return {
        "id": qid,
        "source": "interview_core",
        "category": category,
        "title": title,
        "answer": answer,
    }


def main():
    # 清空 interview 目录（保留旧文件）
    if INTERVIEW_DIR.exists():
        # 删除之前爬取的子目录，保留README
        for item in INTERVIEW_DIR.iterdir():
            if item.is_dir() and item.name not in [".git"]:
                shutil.rmtree(item)
        for item in INTERVIEW_DIR.iterdir():
            if item.is_file() and item.name.endswith(".md") and item.name != "README.md":
                item.unlink()
        for item in INTERVIEW_DIR.iterdir():
            if item.name.endswith(".json"):
                item.unlink()

    INTERVIEW_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    index = []

    for source_key, cfg in SOURCES.items():
        source_label = cfg["label"]
        filepath = cfg["file"]

        if not filepath.exists():
            print(f"⚠️ 跳过 {source_label}: 文件不存在 {filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # 按题目分割
        blocks = re.split(cfg["split_pattern"], text)
        # 第一块可能是文件头（介绍文字），跳过
        blocks = [b for b in blocks if re.search(cfg["id_pattern"], b)]

        source_dir = INTERVIEW_DIR / source_key
        source_dir.mkdir(exist_ok=True)

        source_count = 0
        for block in blocks:
            if source_key == "interview_core":
                q = parse_core(block)
            else:
                q = parse_generic(block, source_key)

            if not q or not q["title"] or len(q["answer"]) < 50:
                continue

            # 分类子目录
            cat_dir = source_dir / sanitize(q["category"])
            cat_dir.mkdir(exist_ok=True)

            # 文件名：ID_标题.md
            filename = f"{q['id']}_{sanitize(q['title'])}.md"
            filepath = cat_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"---\n")
                f.write(f"id: {q['id']}\n")
                f.write(f"source: {q['source']}\n")
                f.write(f"category: {q['category']}\n")
                f.write(f"title: {q['title']}\n")
                f.write(f"generated: {datetime.now().isoformat()}\n")
                f.write(f"---\n\n")
                f.write(f"# {q['title']}\n\n")
                f.write(f"> 来源: {source_label} | 分类: {q['category']}\n\n")
                f.write(q['answer'])

            source_count += 1
            index.append({
                "id": q["id"],
                "source": source_key,
                "category": q["category"],
                "title": q["title"],
            })

        total += source_count
        print(f"  ✅ {source_label}: {source_count} 题 → interview/{source_key}/")

    # 写索引
    index_path = INTERVIEW_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 写 README
    readme_path = INTERVIEW_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# AI 面试题库\n\n")
        f.write(f"> 生成时间: {datetime.now().isoformat()}\n")
        f.write(f"> 总题数: {total}\n\n")
        f.write("---\n\n")
        for source_key, cfg in SOURCES.items():
            src_index = [i for i in index if i["source"] == source_key]
            if not src_index:
                continue
            f.write(f"## {cfg['label']}（{len(src_index)} 题）\n\n")
            cats = {}
            for item in src_index:
                cats.setdefault(item["category"], []).append(item)
            for cat, items in sorted(cats.items()):
                f.write(f"### {cat}（{len(items)} 题）\n\n")
                for item in items:
                    f.write(f"- [{item['title']}]({source_key}/{sanitize(cat)}/{item['id']}_{sanitize(item['title'])}.md)\n")
                f.write("\n")

    print(f"\n✅ 完成！共 {total} 题，输出到 {INTERVIEW_DIR}")
    print(f"   索引: {index_path}")
    print(f"   目录: {readme_path}")


if __name__ == "__main__":
    main()
