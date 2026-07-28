#!/usr/bin/env python3
"""去重+合并小分类+重新生成网站源"""
import re, json
from pathlib import Path
from datetime import datetime

MERGED = Path("/Users/lxy/Documents/ai_transition/interview/汇总")
DOCS = Path("/Users/lxy/Documents/ai_transition/docs")

# ---- 工具函数 ----

def parse_questions(text):
    """从 md 文本提取题目列表 [(title, answer)]"""
    qs = []
    h2s = list(re.finditer(r'^## (\d+)\. (.+)$', text, re.MULTILINE))
    for i, m in enumerate(h2s):
        title = m.group(2).strip()
        start = m.end()
        end = h2s[i + 1].start() if i + 1 < len(h2s) else len(text)
        answer = text[start:end].strip()
        answer = re.sub(r'\n---\s*$', '', answer).strip()
        qs.append((title, answer))
    return qs


def write_file(filepath, category, questions):
    """写分类 md 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"---\ncategory: {category}\ntotal: {len(questions)}\n")
        f.write(f"generated: {datetime.now().isoformat()}\n---\n\n")
        f.write(f"# 🏷️ {category}\n\n> 共 {len(questions)} 题\n\n---\n\n")

        if len(questions) > 1:
            f.write("## 📑 目录\n\n")
            for i, (title, _) in enumerate(questions, 1):
                clean = re.sub(r'[*_`\[\]]', '', title).strip()
                anchor = re.sub(r'[？?，,。\s]', '', clean)
                anchor = re.sub(r'[^\w一-鿿-]', '', anchor)
                f.write(f"{i}. [{clean}](#{anchor})\n")
            f.write("\n---\n\n")

        for i, (title, answer) in enumerate(questions, 1):
            f.write(f"## {i}. {title}\n\n")
            f.write(answer)
            f.write("\n\n---\n\n")


# ---- 1. 去重 ----

def deduplicate():
    """删除标题高度相似的重复题（保留答案更长的）"""
    dupes = {
        "Agent 智能体.md": [
            "LLM 和 Agent 有什么区别？",
        ],
        "MCP 工具调用与协议.md": [
            "什么是 MCP 协议，它在 AI 大模型系统中的作⽤是什么？",
        ],
    }
    for fname, bad_titles in dupes.items():
        fp = MERGED / fname
        with open(fp) as f:
            text = f.read()
        cat = re.search(r'^category:\s*(.+)', text, re.MULTILINE).group(1)
        qs = parse_questions(text)
        before = len(qs)
        qs = [(t, a) for t, a in qs if t not in bad_titles]
        write_file(fp, cat, qs)
        print(f"  🗑 {fname}: {before}→{len(qs)} (删除 {before-len(qs)} 重复)")

# ---- 2. 合并小分类 ----

def merge_small():
    """将 <10 题的小分类合并到大分类"""
    merges = [
        ("信贷风控建模.md", "大模型工程与训练.md", "信贷风控建模"),
        ("数据仓库与治理.md", "NL2SQL 自然语言查询.md", "数据仓库与治理"),
    ]

    for small_f, big_f, small_label in merges:
        sp, bp = MERGED / small_f, MERGED / big_f
        if not sp.exists():
            continue

        with open(sp) as f:
            scat = re.search(r'^category:\s*(.+)', f.read(), re.MULTILINE).group(1)
        with open(bp) as f:
            btext = f.read()
            bcat = re.search(r'^category:\s*(.+)', btext, re.MULTILINE).group(1)

        small_qs = parse_questions(open(sp).read())
        big_qs = parse_questions(btext)
        big_titles = {t for t, _ in big_qs}

        # 去重后合并
        new_qs = [(t, f"> 📎 原分类: {scat}\n\n{a}") for t, a in small_qs if t not in big_titles]
        merged = big_qs + new_qs

        write_file(bp, bcat, merged)
        sp.unlink()

        print(f"  📦 {small_f}({len(small_qs)}题) → {big_f}: "
              f"新增 {len(new_qs)} 题, 合并后 {len(merged)} 题")


# ---- 3. 重新生成网站源 ----

def regenerate_source():
    all_q = []
    for fp in sorted(MERGED.glob("*.md")):
        if fp.name in ("README.md", "_index.json"):
            continue
        with open(fp) as f:
            text = f.read()
        cat = re.search(r'^category:\s*(.+)', text, re.MULTILINE).group(1)
        for title, answer in parse_questions(text):
            # 去掉答案中的 blockquote 元数据行（网站显示不需要）
            clean = re.sub(r'^> .*\n?', '', answer, flags=re.MULTILINE).strip()
            if len(clean) > 50:
                all_q.append({"title": title, "answer": clean, "category": cat})

    out = DOCS / "merged_questions.md"
    with open(out, 'w') as f:
        f.write(f"# 面试题库\n\n> 共 {len(all_q)} 题 | {datetime.now().strftime('%Y-%m-%d')}\n\n---\n\n")
        for i, q in enumerate(all_q, 1):
            f.write(f"### M{i:04d}\n**分类：** {q['category']}\n**题目：** {q['title']}\n")
            f.write(f"**参考答案：** {q['answer']}\n\n---\n\n")
    print(f"\n✅ 网站源: {out} ({len(all_q)} 题)")
    return len(all_q)


# ---- 4. 更新 _index.json ----

def update_index():
    cats = []
    for fp in sorted(MERGED.glob("*.md")):
        if fp.name in ("README.md", "_index.json"):
            continue
        with open(fp) as f:
            text = f.read()
        cat = re.search(r'^category:\s*(.+)', text, re.MULTILINE).group(1)
        cnt = len(re.findall(r'^## \d+\. ', text, re.MULTILINE))
        cats.append({"category": cat, "count": cnt, "file": fp.name})
    with open(MERGED / "_index.json", 'w') as f:
        json.dump(cats, f, ensure_ascii=False, indent=2)
    return cats


# ---- main ----
if __name__ == '__main__':
    print("🗑 去重...")
    deduplicate()

    print("\n📦 合并小分类...")
    merge_small()

    print("\n📊 最终统计:")
    cats = update_index()
    for c in cats:
        print(f"  {c['count']:3d} 题  {c['category']}")

    total = sum(c['count'] for c in cats)
    print(f"  ---\n  {total:3d} 题  {len(cats)} 个分类")

    regenerate_source()
