# Day 34 - NL2SQL 结果解释器

这个项目练习 NL2SQL 的第五步：把 Day 33 的查询执行结果解释成业务人员能读懂的话。

它会处理：

- 单指标结果：把 `application_count = 380` 解释成授信申请量；
- 分组结果：说明哪个渠道、城市或产品表现最高；
- 趋势结果：说明最近几天是上升、下降还是波动；
- 对比结果：说明当前值、上期值和变化幅度；
- 明细结果：把审批状态、风险等级、额度解释成业务语言；
- 被阻断结果：说明为什么不能查，而不是只返回空结果。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day34_nl2sql_result_interpreter/main.py
```

## 输出文件

```text
projects/day34_nl2sql_result_interpreter/output/result_interpretation_results.json
projects/day34_nl2sql_result_interpreter/output/result_interpretation_report.md
```

## 生产映射

真实生产里，结果解释层通常接在查询执行之后。
它不能编造 SQL 结果里没有的信息，只能基于结构化结果解释业务含义，
并补充口径说明、风险提示和建议追问。

