#!/usr/bin/env python3
"""
将 interview/ 下的 xiaolinnote 文章转换为面试题库格式
生成 xiaolinnote_questions.md 到 docs/
"""

import re
import os
from pathlib import Path

INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")
OUTPUT_FILE = Path("/Users/lxy/Documents/ai_transition/docs/xiaolinnote_questions.md")

# 文件路径 → 分类映射
PATH_CATEGORY_MAP = {
    "ai/agent": "Agent",
    "ai/rag": "RAG 检索增强",
    "ai/tools": "LLM工具调用与协议",
    "ai/llm": "大模型工程",
    "agent": "Agent图解专栏",
    "claudecode": "Claude Code图解专栏",
}


def extract_title_and_answer(filepath: str) -> tuple[str, str, str]:
    """从 Markdown 文件中提取标题和参考答案，返回 (id, title, answer, category)"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 frontmatter title
    fm_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
    title = fm_match.group(1).strip() if fm_match else ""

    # 去掉 frontmatter
    content = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL)

    # 提取第一个 H1 标题
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not title and h1_match:
        title = h1_match.group(1).strip()

    # 跳过非题目页面（导航页、介绍页、索引页）
    skip_titles = [
        "Agent 面试题介绍", "RAG 面试题介绍", "LLM工具调用面试题介绍",
        "大模型工程面试题介绍", "LangChain框架面试题介绍",
        "小林面试笔记", "大模型面试题", "图解 Agent", "图解 Claude Code",
        "01｜ Agent面试题", "02｜ RAG面试题", "03｜ LLM工具调用面试题",
        "03｜ 大模型工程面试题", "05｜ LangChain框架面试题",
        "Agent 概念与生态", "RAG 检索增强", "Agent 工程方法论",
        "Claude Code 基础入门", "Claude Code 实践技巧",
        "Claude Code 提示词工程", "Claude Code 源码解析", "Claude Code 行业观察",
        "赞赏支持", "关于网站",
    ]
    if title in skip_titles or title.startswith("0") and "｜" in title:
        return None, None, None, None

    # 确定分类
    category = "综合"
    for path_prefix, cat_name in PATH_CATEGORY_MAP.items():
        if path_prefix in filepath:
            category = cat_name
            break

    # 提取答案内容：去掉标题行和原文链接行，保留正文
    lines = content.split("\n")
    answer_lines = []
    started = False
    for line in lines:
        # 跳过开头的标题、链接、元数据
        if not started:
            if line.startswith("# ") or line.startswith("> 原文链接") or line.startswith("原创"):
                continue
            if line.strip().startswith("---") or line.strip() == "":
                continue
            started = True

        if started:
            answer_lines.append(line)

    answer = "\n".join(answer_lines).strip()

    # 清理答案中的图片链接（保留但不影响阅读）
    answer = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[图片: \1]', answer)

    # 如果答案太长（>50000字符），截断
    if len(answer) > 50000:
        answer = answer[:50000] + "\n\n... (内容过长，已截断，请查看原文)"

    if title is None or not title or not answer or len(answer) < 100:
        return None, None, None, None

    return title, answer, category, filepath


def main():
    # 收集所有文章文件
    md_files = []
    for root, dirs, files in os.walk(INTERVIEW_DIR):
        for f in files:
            if f.endswith(".md") and f not in ["README.md", "_index.json"]:
                path = os.path.join(root, f)
                # 排除已有的两个题库文件
                if f in ["mianshiya_llm_interview_questions.md",
                          "interview_core_questions.md"]:
                    continue
                md_files.append(path)

    md_files.sort()

    print(f"📂 发现 {len(md_files)} 个 MD 文件")

    questions = []
    q_id = 1

    for fpath in md_files:
        title, answer, category, _ = extract_title_and_answer(fpath)
        if title and answer:
            questions.append({
                "id": f"X{q_id:03d}",
                "title": title,
                "answer": answer,
                "category": category,
            })
            print(f"  ✅ X{q_id:03d} [{category}] {title[:60]}")
            q_id += 1
        else:
            rel_path = os.path.relpath(fpath, INTERVIEW_DIR)
            print(f"  ⏭ 跳过: {rel_path}")

    # 写入题库文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 小林面试笔记题库 (xiaolinnote.com)\n\n")
        f.write(f"> 共 {len(questions)} 题\n")
        f.write(f"> 来源: https://xiaolinnote.com\n\n")
        f.write("---\n\n")

        for q in questions:
            f.write(f"### {q['id']}\n")
            f.write(f"**分类：** {q['category']}\n")
            f.write(f"**题目：** {q['title']}\n")
            f.write(f"**参考答案：** {q['answer']}\n")
            f.write(f"\n---\n\n")

    print(f"\n✅ 生成题库: {OUTPUT_FILE}")
    print(f"   共 {len(questions)} 题")
    print(f"   文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
