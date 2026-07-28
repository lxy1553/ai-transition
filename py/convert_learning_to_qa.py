#!/usr/bin/env python3
"""
将 Learning_Review_Plan 下的学习笔记提炼成面试题库格式
输出到 docs/learning_review_questions.md
"""

import re
import os
from pathlib import Path

LEARNING_DIR = Path("/Users/lxy/Documents/ai_transition/credit_risk_control_system/Learning_Review_Plan")
OUTPUT_FILE = Path("/Users/lxy/Documents/ai_transition/docs/learning_review_questions.md")

# 文件名关键词 → 分类
def get_category(filepath: str) -> str:
    path = filepath.lower()
    if "/ai/" in path:
        return "AI应用开发"
    if "/数仓/" in path or "数仓" in path:
        return "数据仓库"
    if "xgboost" in path or "模型训练" in path or "特征" in path or "规则引擎" in path or "评分卡" in path or "abc" in path or "黑白名单" in path or "ml" in path:
        return "信贷风控建模"
    if "rag" in path or "向量" in path or "llm" in path or "langchain" in path or "langgraph" in path or "fastapi" in path or "pytorch" in path or "微调" in path or "agent" in path:
        return "LLM与AI工程"
    if "shap" in path or "reason_code" in path:
        return "模型可解释性"
    if "数据来源" in path or "binlog" in path:
        return "数据工程"
    return "综合"


def extract_questions_from_file(filepath: str) -> list:
    """从一个 md 文件中提取面试题，返回 [{title, answer, category}]"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    questions = []
    rel_path = os.path.relpath(filepath, LEARNING_DIR)
    category = get_category(filepath)

    # 提取主标题
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    main_topic = h1_match.group(1).strip() if h1_match else rel_path

    # 清理 "Day XX：" 前缀
    main_topic = re.sub(r'^Day\s*\d+\s*[：:]\s*', '', main_topic)

    # 按 H2 分段
    sections = re.split(r'\n(?=## )', content)

    for section in sections:
        h2_match = re.search(r'^##\s+(.+)$', section, re.MULTILINE)
        if not h2_match:
            continue
        subtitle = h2_match.group(1).strip()

        # 跳过目录、目标等非问题性标题
        skip_patterns = [
            r'^(目标|目录|大纲|总结|参考|TODO|附录|思维导图)',
            r'(20min|30min|40min|60min|15min|10min)$',
        ]
        if any(re.search(p, subtitle) for p in skip_patterns):
            continue

        # 提取答案：去掉 H2 标题行后的内容
        answer = section.split("\n", 1)[1] if "\n" in section else section
        # 去掉开头的空行和元数据行
        answer = re.sub(r'^(\s*\n)+', '', answer)

        # 如果答案太短，跳过
        if len(answer.strip()) < 200:
            continue

        # 构造面试题标题
        # 把学习笔记的章节标题转化为面试问题
        title = convert_to_question(subtitle, main_topic, category)

        # 清理答案中的 markdown 标记，保留内容
        answer = clean_answer(answer)

        if len(answer) > 100:
            questions.append({
                "title": title,
                "answer": answer,
                "category": category,
            })

    return questions


def convert_to_question(subtitle: str, main_topic: str, category: str) -> str:
    """将学习笔记的章节标题转化为面试问题"""
    # 去掉时间标记 "(20min)" 等
    subtitle = re.sub(r'\s*\(\d+min\)\s*', '', subtitle).strip()

    # 去掉编号 "一、" "1.1" 等
    subtitle = re.sub(r'^[一二三四五六七八九十]+[、.]?\s*', '', subtitle)
    subtitle = re.sub(r'^\d+[\.\、]\d*\s*', '', subtitle)

    # 如果标题已经是问题形式，直接用
    if re.search(r'[？?]', subtitle) or re.search(r'(为什么|什么|怎么|如何|怎样|多少|哪)', subtitle):
        return subtitle

    # 根据内容类型生成问题
    patterns = [
        (r'(.*)是什么|什么是(.*)', r'请解释什么是\1\2'),
        (r'.*区别|.*对比|.*vs|.*选择', r'请说说' + subtitle),
        (r'.*原理|.*机制|.*过程|.*流程', r'请详细讲解' + subtitle),
        (r'.*策略|.*方案|.*设计|.*架构', r'请谈谈' + subtitle + '怎么设计？'),
        (r'.*实战|.*实现|.*代码|.*例子', r'请举例说明' + subtitle + '如何实现？'),
        (r'.*问题|.*挑战|.*难点|.*坑', r'面试官问：' + subtitle + '你会怎么回答？'),
        (r'.*方法|.*手段|.*技巧', r'请分享' + subtitle),
    ]

    for pattern, template in patterns:
        if re.search(pattern, subtitle):
            return template

    # 默认：结合主标题生成问题
    return f"请讲讲{main_topic}中的{subtitle}"


def clean_answer(text: str) -> str:
    """清理答案文本"""
    # 保留代码块
    text = re.sub(r'```(\w*)\n', r'\n```\1\n', text)

    # 去掉图片链接的 markdown 语法但保留描述
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[\1]', text)

    # 压缩过多的空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 截断过长的答案
    if len(text) > 30000:
        text = text[:30000] + "\n\n... (内容过长，已截断)"

    return text.strip()


def main():
    print("🔍 扫描 Learning_Review_Plan 目录...")

    all_questions = []

    # 遍历所有 md 文件
    for root, dirs, files in os.walk(LEARNING_DIR):
        for f in sorted(files):
            if f.endswith(".md"):
                filepath = os.path.join(root, f)
                rel = os.path.relpath(filepath, LEARNING_DIR)

                # 跳过计划类文件
                if "计划" in f or "分析" in f:
                    print(f"  ⏭ 跳过: {rel} (计划/分析)")
                    continue

                questions = extract_questions_from_file(filepath)
                if questions:
                    print(f"  ✅ {rel}: 提取 {len(questions)} 题")
                    all_questions.extend(questions)
                else:
                    print(f"  ⚠️ {rel}: 无可提取的题目")

    # 分配 ID
    for i, q in enumerate(all_questions, 1):
        q["id"] = f"L{i:03d}"

    print(f"\n📊 共提炼 {len(all_questions)} 道面试题")

    # 按分类统计
    cat_counts = {}
    for q in all_questions:
        cat_counts[q["category"]] = cat_counts.get(q["category"], 0) + 1
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {cnt} 题")

    # 写入题库文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 学习复习计划题库 (Learning_Review_Plan)\n\n")
        f.write(f"> 共 {len(all_questions)} 题\n")
        f.write(f"> 来源: credit_risk_control_system/Learning_Review_Plan\n\n")
        f.write("---\n\n")

        for q in all_questions:
            f.write(f"### {q['id']}\n")
            f.write(f"**分类：** {q['category']}\n")
            f.write(f"**题目：** {q['title']}\n")
            f.write(f"**参考答案：** {q['answer']}\n")
            f.write(f"\n---\n\n")

    print(f"\n✅ 生成题库: {OUTPUT_FILE}")
    print(f"   文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
