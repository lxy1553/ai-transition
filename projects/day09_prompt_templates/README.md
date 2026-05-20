# Day 9 - Prompt 模板练习

这个项目把 Prompt 拆成可复用模板，重点练习角色、任务、上下文、约束和输出格式。

它不调用真实 LLM，只在本地生成模板文本，适合先把 Prompt 结构练稳。

## 运行

```bash
python3 projects/day09_prompt_templates/main.py
```

## 练习

运行后阅读输出的三个模板：

- SQL 解释
- 数据问答
- 简历项目包装

脚本还会生成：

```text
projects/day09_prompt_templates/output/prompt_templates.md
```

然后把 `notes/day09_prompt_practice.md` 里的练习和复盘补齐。
