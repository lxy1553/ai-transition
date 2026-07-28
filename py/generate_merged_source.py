#!/usr/bin/env python3
"""从 interview/汇总/ 生成网站题库文件，并更新 parser.js"""
import re
from pathlib import Path
from datetime import datetime

MERGED_DIR = Path("/Users/lxy/Documents/ai_transition/interview/汇总")
DOCS_DIR = Path("/Users/lxy/Documents/ai_transition/docs")

# source key for the merged bank
SOURCE_KEY = "merged"
SOURCE_FILE = DOCS_DIR / "merged_questions.md"
SOURCE_LABEL = "分类汇总"


def main():
    all_q = []
    for md_file in sorted(MERGED_DIR.glob("*.md")):
        if md_file.name in ("README.md", "_index.json"):
            continue

        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()

        cat_match = re.search(r'^category:\s*(.+)', text, re.MULTILINE)
        category = cat_match.group(1).strip() if cat_match else md_file.stem

        # 按 H2 题目分割
        h2s = list(re.finditer(r'^## (\d+)\. (.+)$', text, re.MULTILINE))
        for i, m in enumerate(h2s):
            title = m.group(2).strip()
            start = m.end()
            end = h2s[i + 1].start() if i + 1 < len(h2s) else len(text)
            answer = text[start:end].strip()
            # 去掉 > ID 行
            answer = re.sub(r'^> .*\n?', '', answer, flags=re.MULTILINE).strip()
            if len(answer) > 50:
                all_q.append({"title": title, "answer": answer, "category": category})

    # 写入合并文件（使用通用 Q 格式）
    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 面试题库 · 分类汇总\n\n")
        f.write(f"> 共 {len(all_q)} 题 | 更新: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"> 来源: interview/汇总/\n\n---\n\n")

        for i, q in enumerate(all_q, 1):
            qid = f"M{i:04d}"
            f.write(f"### {qid}\n")
            f.write(f"**分类：** {q['category']}\n")
            f.write(f"**题目：** {q['title']}\n")
            f.write(f"**参考答案：** {q['answer']}\n")
            f.write(f"\n---\n\n")

    print(f"✅ 生成: {SOURCE_FILE} ({len(all_q)} 题)")

    # ---- 更新 parser.js ----
    parser_path = Path("/Users/lxy/Documents/ai_transition/projects/interview_qa_website/js/parser.js")
    with open(parser_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 添加新 URL
    new_url = (
        f"  const URL_MERGED =\n"
        f"    'https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/merged_questions.md';\n"
    )
    if "URL_MERGED" not in js:
        js = js.replace(
            "  const URL_LEARNING =",
            new_url + "  const URL_LEARNING ="
        )

    # 添加 parseMerged 函数
    if "parseMerged" not in js:
        parse_fn = (
            "  // ---- merged 汇总文件解析 ------------------------------------------\n\n"
            "  function parseMerged(text) {\n"
            "    const questions = [];\n"
            "    const blocks = text.split(/\\n(?=### M\\d+)/);\n"
            "    for (const block of blocks) {\n"
            "      const q = parseGenericBlock(block);\n"
            "      if (q && q.title) {\n"
            "        q.source = 'merged';\n"
            "        const cat = q.category;\n"
            "        if (/RAG|Agent|大模型/.test(cat)) q.difficulty = 'hard';\n"
            "        else if (/数据仓库|NL2SQL|信贷/.test(cat)) q.difficulty = 'medium';\n"
            "        else q.difficulty = 'medium';\n"
            "        questions.push(q);\n"
            "      }\n"
            "    }\n"
            "    return questions;\n"
            "  }\n\n"
        )
        # Insert before "// ---- 公开 API ---"
        js = js.replace("  // ---- 公开 API", parse_fn + "  // ---- 公开 API")

    # Update loadAll: add URL_MERGED fetch and parse
    js = js.replace(
        "    const [text1, text2, text3, text4] = await Promise.all([\n      fetchText(URL_MIANSHIYA, force),\n      fetchText(URL_CORE, force),\n      fetchText(URL_XIAOLIN, force),\n      fetchText(URL_LEARNING, force)\n    ]);\n    const q1 = parseMianshiya(text1);\n    const q2 = parseInterviewCore(text2);\n    const q3 = parseXiaolin(text3);\n    const q4 = parseLearning(text4);\n    const all = [...q1, ...q2, ...q3, ...q4];\n\n    const t1 = getCacheTime(URL_MIANSHIYA);\n    const t2 = getCacheTime(URL_CORE);\n    const t3 = getCacheTime(URL_XIAOLIN);\n    const t4 = getCacheTime(URL_LEARNING);\n    const cacheTime = Math.min(t1, t2, t3, t4) || Date.now();",
        "    const allTexts = await Promise.all([\n      fetchText(URL_MIANSHIYA, force),\n      fetchText(URL_CORE, force),\n      fetchText(URL_XIAOLIN, force),\n      fetchText(URL_LEARNING, force),\n      fetchText(URL_MERGED, force)\n    ]);\n    const q1 = parseMianshiya(allTexts[0]);\n    const q2 = parseInterviewCore(allTexts[1]);\n    const q3 = parseXiaolin(allTexts[2]);\n    const q4 = parseLearning(allTexts[3]);\n    const q5 = parseMerged(allTexts[4]);\n    const all = [...q1, ...q2, ...q3, ...q4, ...q5];\n\n    const t1 = getCacheTime(URL_MIANSHIYA);\n    const t2 = getCacheTime(URL_CORE);\n    const t3 = getCacheTime(URL_XIAOLIN);\n    const t4 = getCacheTime(URL_LEARNING);\n    const t5 = getCacheTime(URL_MERGED);\n    const cacheTime = Math.min(t1, t2, t3, t4, t5) || Date.now();"
    )

    # Update return
    js = js.replace(
        "return { loadAll, URL_MIANSHIYA, URL_CORE, URL_XIAOLIN, URL_LEARNING, getCacheTime };",
        "return { loadAll, URL_MIANSHIYA, URL_CORE, URL_XIAOLIN, URL_LEARNING, URL_MERGED, getCacheTime };"
    )

    with open(parser_path, "w", encoding="utf-8") as f:
        f.write(js)
    print("✅ 更新 parser.js: 添加 URL_MERGED + parseMerged")

    # ---- 更新 index.html 筛选 ----
    html_path = Path("/Users/lxy/Documents/ai_transition/projects/interview_qa_website/index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    if "分类汇总" not in html:
        html = html.replace(
            '<option value="learning">学习复习计划</option>',
            '<option value="learning">学习复习计划</option>\n    <option value="merged">分类汇总</option>'
        )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 更新 index.html: 添加'分类汇总'筛选项")

    print(f"\n🎉 全部完成！网站将加载 {len(all_q)} 道汇总题目")


if __name__ == "__main__":
    main()
