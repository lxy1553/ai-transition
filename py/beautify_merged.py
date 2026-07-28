#!/usr/bin/env python3
"""深度美化 汇总/ 目录下的合并文件，大幅提升可阅读性"""

import re
from pathlib import Path

MERGED_DIR = Path("/Users/lxy/Documents/ai_transition/interview/汇总")


def beautify(text: str) -> str:
    # ---- 1. 修复代码块：```text → ```json / ```python / ``` ----
    # 检测包含 JSON 的代码块
    text = re.sub(r'```text\n(\s*\{)', r'```json\n\1', text)
    text = re.sub(r'```text\n(\s*(?:import|from|def|class|#|@|if|for|while|try|with|return))', r'```python\n\1', text)
    # 修复 ```text 结尾写成 ```text 的错误
    text = re.sub(r'```text\s*\n(?!\n)', '```\n', text)
    text = re.sub(r'```text$', '```', text, flags=re.MULTILINE)

    # ---- 2. 标题层级规范化：H4-H6 → H3 ----
    text = re.sub(r'^#{4,6}\s+', '### ', text, flags=re.MULTILINE)

    # ---- 3. 修复重复的粗体标记 ** ** → ** ----
    text = re.sub(r'\*\*\s+\*\*', '', text)

    # ---- 4. 清理空行（连续4+空行→2空行）----
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # ---- 5. 确保分隔线 `---` 前后有空行 ----
    text = re.sub(r'([^\n])\n---\n', r'\1\n\n---\n', text)
    text = re.sub(r'\n---\n([^\n#])', r'\n---\n\n\1', text)

    # ---- 6. 修复列表项格式：- 后面加空格 ----
    text = re.sub(r'^(\s*)-(\S)', r'\1- \2', text, flags=re.MULTILINE)

    # ---- 7. 清理 URL 锚点标题残留 ----
    text = re.sub(r'\n\[([^\]]+)\]\(#[^)]+\)\n', '\n', text)

    # ---- 8. 增强关键段落：添加 emoji 标记 ----
    markers = [
        (r'(?m)^(###\s*)(工作原理|工作流程|核心概念|核心组件|基本架构)', r'\1🔧 \2'),
        (r'(?m)^(###\s*)(为什么|原因|背景|问题|局限|弊端|挑战)', r'\1❓ \2'),
        (r'(?m)^(###\s*)(解决方案|如何|怎么|方法|策略|优化|最佳实践)', r'\1💡 \2'),
        (r'(?m)^(###\s*)(总结|小结|要点|关键)', r'\1📌 \2'),
    ]
    for pattern, replacement in markers:
        text = re.sub(pattern, replacement, text)

    # ---- 9. 修复 TOC 锚点（去掉空格让链接生效）----
    def fix_toc_link(m):
        title = m.group(1)
        anchor = m.group(2)
        anchor = re.sub(r'[？?，,。\s]', '', anchor)
        anchor = re.sub(r'[^\w一-鿿-]', '', anchor)
        return f'[{title}](#{anchor})'
    text = re.sub(r'\[([^\]]+)\]\(#([^)]+)\)', fix_toc_link, text)

    # ---- 10. 数字列表后确保换行 ----
    text = re.sub(r'^(\d+)[\.、]\s*([^\n]{60,})', r'\1. \2', text, flags=re.MULTILINE)

    # ---- 11. 给长段落分段（超过500字的连续文本插入空行）----
    # （保持原样，这个容易出问题）

    # ---- 12. 清理残留的 "####" 后面跟 `**` 的怪异格式 ----
    text = re.sub(r'^####\s+\*\*(.+?)\*\*', r'### \1', text, flags=re.MULTILINE)

    return text.strip() + '\n'


def main():
    count = 0
    for filepath in sorted(MERGED_DIR.glob("*.md")):
        if filepath.name in ("README.md", "_index.json"):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()

        beautified = beautify(original)

        if beautified != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(beautified)
            count += 1

        q_count = len(re.findall(r'^## \d+\.', beautified, re.MULTILINE))
        print(f"  ✨ {filepath.name} ({q_count} 题)")

    print(f"\n✅ 美化完成！共处理 {count} 个文件")


if __name__ == "__main__":
    main()
