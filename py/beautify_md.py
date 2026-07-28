#!/usr/bin/env python3
"""美化 interview/ 下所有 MD 文件，提升可阅读性"""

import re
from pathlib import Path

INTERVIEW_DIR = Path("/Users/lxy/Documents/ai_transition/interview")


def beautify(text: str) -> str:
    """对单个 md 文件内容做美化"""

    # ---- 1. 修复重复编号：标题中 "1. 1. xxx" → "1. xxx" ----
    text = re.sub(r'^(## )\d+\. (\d+\.\s*)', r'\1\2', text, flags=re.MULTILINE)

    # ---- 2. 清理空图片占位符 [图片: ] → 删除 ----
    text = re.sub(r'\n?\[图片: ?\]\n?', '\n', text)

    # ---- 3. 修复锚点头：## [标题](#xxx) → ### 标题 ----
    def fix_anchor_heading(m):
        title = m.group(1)
        # 去掉 emoji 后面的锚点链接但保留 emoji 和文字
        clean_title = re.sub(r'\s*\[([^\]]+)\]\([^)]+\)', r'\1', title)
        level = m.group(0).count('#')
        return f"{'#' * level} {clean_title}"
    text = re.sub(r'^#{2,4}\s+\[([^\]]+)\]\(#[^)]+\)', fix_anchor_heading, text, flags=re.MULTILINE)

    # ---- 4. 面试对话格式化：将 👔 和 🙋‍♂️ 对话转为引用块 ----
    lines = text.split('\n')
    result = []
    in_dialog = False
    dialog_buf = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        is_dialog_line = bool(re.match(r'^[👔🙋‍♂️🤔]', stripped))

        if is_dialog_line and not in_dialog:
            # flush any pending content
            if dialog_buf:
                result.append('\n'.join(dialog_buf))
                dialog_buf = []
            in_dialog = True
            dialog_buf.append(f"> {stripped}")
        elif is_dialog_line and in_dialog:
            dialog_buf.append(f"> {stripped}")
        elif not is_dialog_line and in_dialog:
            # end of dialog
            if dialog_buf:
                result.append('\n'.join(dialog_buf))
                result.append('')  # blank line after dialog
                dialog_buf = []
            in_dialog = False
            result.append(line)
        else:
            result.append(line)

    if dialog_buf:
        result.append('\n'.join(dialog_buf))
    text = '\n'.join(result)

    # ---- 5. 为裸代码块补语言标记 ----
    text = re.sub(r'```\s*\n(?!```)', '```text\n', text)

    # ---- 6. 压缩多余空行（>3个连续空行 → 2个） ----
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # ---- 7. 清理残余的纯锚点链接行 ----
    text = re.sub(r'^\s*\[([^\]]+)\]\(#[^)]+\)\s*$', '', text, flags=re.MULTILINE)

    # ---- 8. 确保分隔线前后有空行 ----
    text = re.sub(r'([^\n])\n---\n', r'\1\n\n---\n', text)
    text = re.sub(r'\n---\n([^\n])', r'\n---\n\n\1', text)

    # ---- 9. 清理标题中多余的 # 前缀 ----
    # 有些标题是 "## [### xxx](#xxx)" 这种格式
    text = re.sub(r'^#{2,4}\s+\[#{1,3}\s+', '### ', text, flags=re.MULTILINE)

    # ---- 10. 增强关键段落标记 ----
    # 给 "简要回答"、"详细解析"、"核心概念" 等关键词加粗
    for kw in ['简要回答', '详细解析', '核心概念', '面试官说', '总结', '关键点']:
        text = re.sub(rf'(?<!\*)({kw})(?!\*)', rf'**{kw}**', text)

    return text.strip() + '\n'


def add_toc(text: str, filename: str) -> str:
    """在 frontmatter 后面插入目录"""
    # 找到第二个 ---（frontmatter 结束）
    parts = text.split('---', 2)
    if len(parts) < 3:
        return text

    frontmatter = parts[0] + '---' + parts[1] + '---'
    body = parts[2]

    # 提取所有 H2 标题
    h2s = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
    if len(h2s) < 3:  # 题目太少不生成目录
        return text

    toc_lines = ['\n## 📑 目录\n']
    for i, h2 in enumerate(h2s, 1):
        # 清理标题中的 markdown 格式
        clean = re.sub(r'[*_`\[\]]', '', h2).strip()
        anchor = clean.lower().replace(' ', '-').replace('？', '').replace('?', '').replace('，', '').replace('。', '')
        toc_lines.append(f"{i}. [{clean}](#{anchor})")
    toc_lines.append('')

    return frontmatter + '\n' + '\n'.join(toc_lines) + '\n' + body


def process_file(filepath: Path):
    """处理单个 md 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    # 跳过 README 和非 md 文件
    if filepath.name == 'README.md':
        return

    beautified = beautify(original)
    beautified = add_toc(beautified, filepath.name)

    if beautified != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(beautified)
        return True
    return False


def main():
    count = 0
    for filepath in sorted(INTERVIEW_DIR.rglob('*.md')):
        if filepath.name in ('README.md', '_index.json'):
            continue
        changed = process_file(filepath)
        if changed:
            count += 1
            rel = filepath.relative_to(INTERVIEW_DIR)
            # 统计题目数
            q_count = len(re.findall(r'^## \d+\.', open(filepath).read(), re.MULTILINE))
            print(f"  ✨ {rel} ({q_count} 题)")

    print(f"\n✅ 美化完成！共处理 {count} 个文件")


if __name__ == '__main__':
    main()
