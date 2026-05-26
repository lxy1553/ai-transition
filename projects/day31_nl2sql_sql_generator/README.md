# Day 31 - NL2SQL SQL 生成器

这个项目练习 NL2SQL 的第三步：把 Day 30 的结构化问题解析结果，结合 Day 29 的 Schema Catalog，
生成可审查的只读 SQL 草稿。

它会处理：

- 指标查询：昨天授信申请量；
- 维度分组：上周每个渠道的授信通过率；
- 趋势查询：最近 7 天放款金额趋势；
- TopN 查询：放款金额最高的城市、逾期金额前 5 的账龄；
- 对比查询：本周逾期率比上周变化；
- 明细查询：按申请编号查询审批状态；
- 风险拦截：敏感字段、缺少时间范围、找不到候选表。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day31_nl2sql_sql_generator/main.py
```

## 输出文件

```text
projects/day31_nl2sql_sql_generator/output/sql_generation_results.json
projects/day31_nl2sql_sql_generator/output/sql_generation_report.md
```

## 生产映射

真实生产里，SQL 生成器通常不会直接执行 SQL。
它只生成 SQL 草稿，并把表、字段、时间条件、权限风险、成本风险交给后续 SQL 校验层。
Day 31 先生成可解释 SQL，Day 32 再重点做 SQL 安全校验。
