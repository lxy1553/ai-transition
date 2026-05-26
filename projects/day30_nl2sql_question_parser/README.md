# Day 30 - NL2SQL 问题解析器

这个项目练习 NL2SQL 的第二步：把用户自然语言问题解析成结构化字段。

它会抽取：

- 指标：授信申请量、授信通过率、放款金额、逾期率；
- 维度：渠道、城市、信贷产品、风险等级、逾期账龄；
- 时间范围：昨天、上周、本周、最近 7 天、本月；
- TopN：前 10、最高的 10 个；
- 过滤条件：城市、申请编号、风险等级、审批状态；
- 风险标记：敏感字段、缺少时间范围、无法识别指标等。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day30_nl2sql_question_parser/main.py
```

## 输出文件

```text
projects/day30_nl2sql_question_parser/output/question_parse_results.json
projects/day30_nl2sql_question_parser/output/question_parse_report.md
```

## 生产映射

真实生产里，问题解析器通常位于 API 入参之后、Schema Router 和 SQL 生成之前。
它先把问题拆成 metric、dimensions、time_range、filters 和 risk_flags，
再把结构化结果交给后续 SQL 生成、权限校验和成本控制模块。
