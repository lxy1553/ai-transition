# Day 24 - RAG 拒答与边界

这个项目用于练习 RAG 系统的拒答策略。

它不调用真实 LLM，而是用确定性规则模拟生产里的回答决策层：

- 敏感信息直接拒答；
- 越权请求直接拒答；
- 高风险操作直接拒答；
- 问题模糊时先澄清；
- 没有检索依据时拒答；
- 有可靠来源且没有触发风险时才允许回答。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day24_hallucination_guardrails/main.py
```

## 输入文件

```text
projects/day24_hallucination_guardrails/rules.json
projects/day24_hallucination_guardrails/cases.json
```

`rules.json` 保存拒答规则和低置信度阈值。
`cases.json` 保存固定测试样本，用来检查策略是否误放行或误拒。

## 输出文件

```text
projects/day24_hallucination_guardrails/output/refusal_eval_results.json
projects/day24_hallucination_guardrails/output/refusal_eval_report.md
```

## 生产映射

真实生产系统里，这个脚本对应 RAG API 调用 LLM 前的安全决策层。
它通常会接入权限系统、数据分类分级、检索分数、citations、审计日志和人工反馈。

拒答策略的目标不是让系统少回答，而是避免在无依据、越权、敏感或危险场景下给出错误答案。
