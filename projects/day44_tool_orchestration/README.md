# Day 44 - 工具协同与多工具调用策略

这个项目用于 Day 44 的本地练习：给金融信贷 NL2SQL / RAG Agent 定义工具注册表、工具选择规则、失败回退和循环保护。

它不接真实 LLM，也不执行真实 SQL。
当前目标是把“什么问题该调哪些工具、什么情况下必须停下、失败时怎么回退”写成可检查的结构化方案。

## 练习目标

- 定义工具注册表，包括用途、输入输出、风险等级和前置条件。
- 为常见业务问题设计工具调用路线。
- 校验高风险工具必须满足前置条件。
- 检查最大步数和重复调用，避免无意义循环。
- 生成 JSON、Mermaid 和 Markdown 报告，便于后续 Day 45 做端到端评测。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day44_tool_orchestration/main.py
```

运行后生成：

```text
projects/day44_tool_orchestration/output/tool_orchestration_plan.json
projects/day44_tool_orchestration/output/tool_orchestration.mmd
projects/day44_tool_orchestration/output/tool_orchestration_report.md
```

## 生产映射

真实生产环境里，这套策略会落到 Agent 编排层：

- 指标查询：Schema -> SQL 生成 -> SQL 校验 -> 查询执行 -> 结果解释。
- 规则解释：RAG 检索 -> 引用回答。
- 敏感导出：安全阻断或转人工。
- 条件缺失：要求补充时间范围、产品、地区或用户权限。
- 工具异常：返回可解释错误，并记录 request_id 和失败原因。

金融信贷场景下，多工具 Agent 的价值不是“自动调用更多工具”，而是在权限、安全、成本和审计边界内，把正确工具按正确顺序串起来。
