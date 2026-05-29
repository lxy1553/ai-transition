# Day 35 - NL2SQL 助手整合演示

这个项目把 Day 30-Day 34 的产物串成一个可演示的 NL2SQL 助手：

```text
用户问题
-> 问题解析
-> SQL 生成
-> SQL 校验
-> 查询执行
-> 结果解释
```

它不是重新写一套规则，而是读取前面每一层的 JSON 结果，检查整条链路能否串起来。
这样更接近生产项目里的分层思路：每层职责清楚，通过稳定契约传递结果。

## 运行方式

生成完整演示报告：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day35_nl2sql_assistant/main.py
```

演示单个问题：

```bash
python3 projects/day35_nl2sql_assistant/main.py --question "本周逾期率比上周变化多少？"
```

## 输出文件

```text
projects/day35_nl2sql_assistant/output/nl2sql_assistant_demo_results.json
projects/day35_nl2sql_assistant/output/nl2sql_assistant_demo_report.md
```

## 生产映射

Day 35 对应“可演示版本”。
面试或项目讲解时，可以按以下顺序讲：

- 输入自然语言问题；
- 问题解析抽取指标、维度、时间和风险；
- SQL 生成只使用 Schema Catalog 中的表字段；
- SQL Validator 拦截危险、越权和高成本查询；
- 查询执行层只执行放行 SQL；
- 结果解释层输出业务回答、关键发现、风险提示和建议追问。

成功查询和安全阻断都要展示。
这能说明 NL2SQL 项目不是只会生成 SQL，而是具备生产环境需要的安全、权限、成本和可解释能力。
