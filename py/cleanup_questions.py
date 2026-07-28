#!/usr/bin/env python3
"""清理面试题库：去掉垃圾标题、重复题、无意义题"""
import re
from pathlib import Path

MERGED = Path("/Users/lxy/Documents/ai_transition/interview/汇总")


def should_delete(title, category):
    """判断标题是否应该删除，返回 (True, reason) 或 (False, '')"""
    t = title.strip()

    # ---- A. 无意义/垃圾标题 ----
    garbage = [
        (r'面试官问.*常见问题.*怎么回答', '无意义问题'),
        (r'^先说清三个概念', '上下文缺失'),
        (r'^具体如何使用.*生产项目', '太模糊'),
        (r'^请详细讲解\**核心概念\**与原理', '无具体主题'),
        (r'^请举例说明更多实际例子如何实现', '空泛举例'),
    ]
    for pat, reason in garbage:
        if re.search(pat, t):
            return True, reason

    # ---- B. 含文件路径/时间标记的自动生成标题 ----
    if re.search(r'请讲讲.*\.md.*中的', t):
        return True, '含文件路径残留'
    if re.search(r'（\d+min）|（\d+h）|\(\d+min\)|\(\d+h\)', t):
        return True, '含学习时间标记'
    if re.search(r'请讲讲.*中的动手练习', t):
        return True, '动手练习标题'
    if re.search(r'请举例说明.*(?:一个让你记住|从代码看|核心代码|假设在|项目中的)', t):
        return True, '自动生成举例标题'
    if re.search(r'请说说(?:原始事件|主流 LLM|LoRA 参数|XGBoost 与机器学习|机器学习和深度学习)', t):
        return True, '自动生成说说标题'
    if re.search(r'^请详细讲解(?:完整训练流程|更新与监控)', t):
        return True, '自动生成讲解标题'
    if re.search(r'请讲讲\*?\*?(?:★ 参考答案|feature_service|PyTorch 微调|向量数据库|分区策略|PII 脱敏|数据血缘|维度建模|分层数据仓库|数据质量体系|综合项目|LangChain|LLM API|RAG 全链路|可解释性|生产级降级|模型评估|规则 \+ 模型|特征工程|PIT 样本)', t):
        return True, '自动生成讲讲标题'
    if re.search(r'请谈谈(?:设计任务)', t):
        return True, '自动生成谈谈标题'

    # ---- C. Claude Code 非题目 ----
    non_questions = ['Project Overview', 'Commands', 'Architecture', 'Conventions',
                     'Hard Constraints', 'Gotchas', 'Your Role']
    if t in non_questions:
        return True, '非面试题(CLAUDE.md章节名)'

    # ---- D. 含 "万字图解" 的标题（与正式题目重复） ----
    if re.search(r'万字图解$', t):
        return True, '与正式题目重复(图解宣传标题)'

    # ---- E. "请讲讲" "请说说" 且标题过长/含特殊字符 ----
    if t.startswith('请讲讲') and len(t) > 50:
        return True, '过长自动生成标题'
    if t.startswith('请说说') and len(t) > 40:
        return True, '过长自动生成标题'
    if t.startswith('请举例说明') and len(t) > 40:
        return True, '过长自动生成标题'
    if re.search(r'（\d+min）|（\d+h）', t):
        return True, '含时间标记'

    return False, ''


def main():
    all_deletions = []
    kept = 0
    deleted = 0

    for md_file in sorted(MERGED.glob("*.md")):
        if md_file.name in ("README.md", "_index.json"):
            continue

        with open(md_file, 'r') as f:
            content = f.read()

        cat_match = re.search(r'^category:\s*(.+)', content, re.MULTILINE)
        category = cat_match.group(1).strip() if cat_match else md_file.stem

        # 找所有 H2 题目
        h2s = list(re.finditer(r'^## (\d+)\. (.+)$', content, re.MULTILINE))

        to_remove = []
        for m in h2s:
            title = m.group(2).strip()
            kill, reason = should_delete(title, category)
            if kill:
                to_remove.append((m.start(), m.end(), title, reason))
                print(f"  🗑 [{category}] {title[:70]}  → {reason}")
                deleted += 1
            else:
                kept += 1

        # 从后往前删除（避免索引偏移）
        if to_remove:
            lines = content.split('\n')
            # 将位置转为行号
            for start_pos, end_pos, title, reason in reversed(to_remove):
                # 找到这个标题的开始行
                line_start = content[:start_pos].count('\n')
                # 找到下一个 H2 或 --- 结束
                rest = content[end_pos:]
                next_h2 = re.search(r'\n(?=## \d+\. |\n---)', rest)
                if next_h2:
                    line_end = (content[:end_pos] + rest[:next_h2.start()]).count('\n')
                else:
                    line_end = len(lines)

                del lines[line_start:line_end + 1]

            # 重新编号
            new_lines = []
            q_num = 0
            for line in lines:
                m = re.match(r'^## (\d+)\. (.+)$', line)
                if m:
                    q_num += 1
                    line = f'## {q_num}. {m.group(2)}'
                # Also fix TOC lines
                tm = re.match(r'^(\d+)\. (\[.+\])$', line.strip())
                if tm:
                    q_num2 = q_num  # use current counter
                    # let TOC be regenerated separately
                new_lines.append(line)

            # 更新 TOC
            new_text = '\n'.join(new_lines)
            # Regenerate TOC
            h2s_new = re.findall(r'^## (\d+)\. (.+)$', new_text, re.MULTILINE)
            toc_lines = []
            for num, title in h2s_new:
                clean = re.sub(r'[*_`\[\]]', '', title).strip()
                anchor = re.sub(r'[？?，,。\s]', '', clean)
                anchor = re.sub(r'[^\w一-鿿-]', '', anchor)
                toc_lines.append(f'{num}. [{clean}](#{anchor})')

            # Replace old TOC
            toc_pattern = r'(## 📑 目录\n\n)(.*?)(\n\n)'
            if re.search(toc_pattern, new_text, re.DOTALL):
                new_text = re.sub(
                    toc_pattern,
                    f'\\1\n' + '\n'.join(toc_lines) + f'\n\\3',
                    new_text, flags=re.DOTALL
                )

            # Update count in frontmatter
            new_text = re.sub(r'^total:\s*\d+', f'total: {len(h2s_new)}', new_text, flags=re.MULTILINE)
            new_text = re.sub(r'^count:\s*\d+', f'count: {len(h2s_new)}', new_text, flags=re.MULTILINE)

            with open(md_file, 'w') as f:
                f.write(new_text)

            all_deletions.extend(to_remove)
            print(f"  📝 {md_file.name}: 删除 {len(to_remove)} 题, 剩余 {len(h2s_new)} 题")

    print(f"\n{'='*60}")
    print(f"✅ 清理完成！")
    print(f"   保留: {kept} 题")
    print(f"   删除: {deleted} 题")
    print(f"   剩余: {kept} 题")


if __name__ == '__main__':
    main()
