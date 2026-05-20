# Day 12-13 - SQL 解释助手 CLI

这是第 2 周的小项目：输入 SQL，输出结构化解释、风险和建议。

当前版本使用本地规则，不调用真实 LLM。这样可以先把工程链路跑通：输入、分析、结构化输出、
风险决策。

## 功能

- 支持示例 SQL 和命令行 SQL 输入
- 提取 SQL 中的表名
- 粗略提取 select 字段
- 识别常见数仓风险
- 输出结构化 JSON

## 运行

在仓库根目录执行：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day12_sql_explainer_cli/main.py --example
```

传入 SQL：

```bash
python3 projects/day12_sql_explainer_cli/main.py --sql "select user_id, count(*) from orders where dt='2026-05-08' group by user_id"
```

## 输出字段

| 字段 | 说明 |
|------|------|
| `summary` | SQL 的简要说明 |
| `tables` | 识别到的表 |
| `fields` | select 字段 |
| `risk_level` | 风险等级 |
| `can_publish` | 是否建议上线 |
| `risks` | 风险列表 |
| `suggestions` | 优化建议 |
| `missing_context` | 缺少的上下文 |

## 后续扩展

- 接入真实 LLM API 生成自然语言解释
- 增加 SQL 解析库，提高表和字段识别准确性
- 结合表结构元数据解释字段业务含义
- 用 RAG 检索指标口径和数仓规范文档
