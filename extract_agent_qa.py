#!/usr/bin/env python3
"""从 微信文章_AI_Agent面试题.md 提取 8 道显式面试题，追加到学习题库"""

import re

SOURCE_FILE = "credit_risk_control_system/Learning_Review_Plan/补充/微信文章_AI_Agent面试题.md"
OUTPUT_FILE = "docs/learning_review_questions.md"

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    text = f.read()

# 定义 8 道题的切分边界（问题标题 → 下一个问题的开始）
questions_def = [
    ("LLM 和 Agent 有什么区别？", "Agent 和 Workflow 有什么区别？"),
    ("Agent 和 Workflow 有什么区别？", "Agent 有什么工作模式？"),
    ("Agent 有什么工作模式？", "Function Call 是什么？"),
    ("Function Call 是什么？", "MCP 是什么协议？"),
    ("MCP 是什么协议？", "Skills 是什么？"),
    ("Skills 是什么？", "Function Call、MCP、Skills 有什么区别？"),
    ("Function Call、MCP、Skills 有什么区别？", "什么是 A2A 协议？"),
    ("什么是 A2A 协议？", "总结"),
]

extracted = []
for title, next_title in questions_def:
    pattern = re.escape(title) + r'(.*?)' + re.escape(next_title)
    match = re.search(pattern, text, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        extracted.append((title, answer))
        print(f"  ✅ {title} ({len(answer)} 字符)")
    else:
        print(f"  ❌ 未找到: {title}")

print(f"\n提取 {len(extracted)} 题，追加到题库...")

# 追加到题库
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    existing = f.read()

# 计算已有题目数
existing_count = len(re.findall(r'^### L\d+', existing, re.MULTILINE))
next_id = existing_count + 1

with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
    for title, answer in extracted:
        qid = f"L{next_id:03d}"
        f.write(f"### {qid}\n")
        f.write(f"**分类：** Agent面试题\n")
        f.write(f"**题目：** {title}\n")
        f.write(f"**参考答案：** {answer}\n")
        f.write(f"\n---\n\n")
        next_id += 1

print(f"✅ 追加完成！题库现有 {next_id - 1} 题")
