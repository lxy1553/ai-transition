#!/usr/bin/env python3
"""
从 interview/ 目录下的分类 md 文件重新生成网站题库源文件到 docs/
保持网站解析器兼容的格式（### ID 块）
"""

import re
import json
from pathlib import Path
from datetime import datetime

INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")
DOCS_DIR = Path("/Users/lxy/Documents/ai_transition/docs")

# 来源映射
SOURCE_MAP = {
    "mianshiya": "面试鸭题库",
    "interview_core": "核心题库",
    "xiaolinnote": "小林面试笔记",
    "learning": "学习复习计划",
}

OUTPUT_FILES = {
    "mianshiya": DOCS_DIR / "mianshiya_llm_interview_questions.md",
    "interview_core": DOCS_DIR / "interview_core_questions.md",
    "xiaolinnote": DOCS_DIR / "xiaolinnote_questions.md",
    "learning": DOCS_DIR / "learning_review_questions.md",
}


def parse_category_file(filepath: Path) -> list:
    """从美化后的分类 md 中提取题目列表"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # 读取 frontmatter
    fm_match = re.search(r'^---\n(.*?)\n---', text, re.DOTALL)
    fm = {}
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()

    source = fm.get('source', '')
    category = fm.get('category', '')

    # 按 ## 数字. 标题 分割题目
    questions = []
    # 找到所有 H2 题目标题的位置
    h2_pattern = re.compile(r'^## (\d+)\. (.+)$', re.MULTILINE)
    matches = list(h2_pattern.finditer(text))

    for i, m in enumerate(matches):
        num = m.group(1)
        title = m.group(2).strip()

        # 答案从当前 H2 之后开始，到下一个 H2 或文件末尾
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        answer_block = text[start:end].strip()

        # 去掉 ID 行
        answer_block = re.sub(r'^> ID:.*\n?', '', answer_block, flags=re.MULTILINE)
        answer_block = re.sub(r'^\n+', '', answer_block)

        # 清理答案
        answer_block = answer_block.strip()

        if len(answer_block) > 50:
            questions.append({
                "id": num,
                "title": title,
                "answer": answer_block,
                "category": category,
                "source": source,
            })

    return questions


def write_source_file(filepath: Path, source_key: str, all_questions: list):
    """写入合并的题库文件，格式兼容网站解析器"""
    source_label = SOURCE_MAP[source_key]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {source_label}\n\n")
        f.write(f"> 共 {len(all_questions)} 题 | 更新: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"> 数据来源: interview/{source_key}/ 目录\n\n")
        f.write("---\n\n")

        for i, q in enumerate(all_questions):
            # ID 保持原有格式：mianshiya用Q, core用q, xiaolinnote用X, learning用L
            if source_key == "interview_core":
                qid = f"q{i+1:03d}"
                # interview_core 使用原始 HTML 锚点格式
                f.write(f'<a id="{qid}"></a>\n\n')
                f.write(f"## {qid.upper()}：{q['title']}\n\n")
                f.write(f"**分类：** {q['category']}\n\n")
                f.write(f"### 回答\n\n{q['answer']}\n\n")
                f.write("---\n\n")
            else:
                prefix = {"mianshiya": "Q", "xiaolinnote": "X", "learning": "L"}[source_key]
                qid = f"{prefix}{i+1:03d}"
                f.write(f"### {qid}\n")
                f.write(f"**分类：** {q['category']}\n")
                f.write(f"**题目：** {q['title']}\n")
                f.write(f"**参考答案：** {q['answer']}\n")
                f.write("\n---\n\n")

    return len(all_questions)


def main():
    print("📂 扫描 interview/ 目录...")

    # 收集所有题目
    source_questions = {k: [] for k in SOURCE_MAP}

    for source_key in SOURCE_MAP:
        src_dir = INTERVIEW_DIR / source_key
        if not src_dir.exists():
            print(f"  ⚠️ {source_key}/ 不存在，跳过")
            continue

        for md_file in sorted(src_dir.glob("*.md")):
            if md_file.name == "README.md":
                continue
            questions = parse_category_file(md_file)
            if questions:
                source_questions[source_key].extend(questions)
                print(f"  📄 {source_key}/{md_file.name}: {len(questions)} 题")

    # 写入合并文件
    print("\n📝 生成网站题库文件...")
    total = 0
    for source_key, questions in source_questions.items():
        if not questions:
            continue
        filepath = OUTPUT_FILES[source_key]
        count = write_source_file(filepath, source_key, questions)
        total += count
        size_kb = filepath.stat().st_size / 1024
        print(f"  ✅ {SOURCE_MAP[source_key]}: {count} 题 → {filepath.name} ({size_kb:.0f} KB)")

    print(f"\n✅ 完成！共 {total} 题，4 个题库文件已更新")
    print(f"   面试网站刷新后即可加载最新内容")


if __name__ == "__main__":
    main()
