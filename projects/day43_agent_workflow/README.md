# Day 43 - Agent 工作流定义

这个项目用于 Day 43 的本地练习：把金融信贷 NL2SQL / RAG 助手拆成可控的 Agent 工作流。

它暂时不接真实 LLM，也不执行真实 SQL。
当前目标是先把每一步的职责、输入输出、工具、失败回退和审计点定义清楚。
这样后续扩展多工具调用时，不会变成模型自由发挥、出错后无法排查的黑盒。

## 练习目标

- 设计“用户问题 -> 意图识别 -> Schema / 知识检索 -> SQL 生成 -> 校验 -> 执行 -> 解释 -> 审计”的流程。
- 为每一步定义允许使用的工具和失败回退方式。
- 导出 JSON，方便后续程序读取。
- 导出 Mermaid 流程图，方便写 README、面试讲解和作品集展示。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day43_agent_workflow/main.py
```

运行后生成：

```text
projects/day43_agent_workflow/output/agent_workflow.json
projects/day43_agent_workflow/output/agent_workflow.mmd
projects/day43_agent_workflow/output/agent_workflow_report.md
```

## 生产映射

真实生产环境里，这个工作流会接入：

- RAG 检索服务：查业务口径、字段解释、规则文档。
- NL2SQL 服务：解析问题、生成 SQL、解释结果。
- SQL 校验器：限制只读查询、敏感字段、高成本扫描和缺少时间条件的问题。
- 查询执行服务：使用受控账号访问数仓或指标库。
- 审计系统：记录 request_id、用户、工具调用、SQL、校验结果和最终响应。

金融信贷场景下，Agent 的核心不是“自动做更多事”，而是“在可控范围内自动完成更多确定步骤”。

