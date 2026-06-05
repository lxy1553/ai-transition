# Day 50 - 指标字典 + RAG 口径问答

这个项目用于 Day 50 的本地练习：把金融信贷离线指标和实时指标整理成指标字典，
再用规则版 RAG 回答“这个指标怎么算、分子分母是什么、窗口是什么、来源表是什么”。

它不连接真实大模型，也不查真实数据库。
今天重点是：口径解释走指标字典和 RAG 引用，不应该直接走 SQL 查询。

## 练习目标

- 建立离线指标字典，写清分子、分母、时间字段、来源表和适用粒度。
- 建立实时指标字典，写清窗口、事件时间、处理时间、延迟阈值和来源事件。
- 把指标字典切成可检索的 RAG chunk。
- 回答口径问题时返回引用来源。
- 对敏感明细导出问题做安全阻断。
- 生成评测结果和 Markdown 报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day50_metric_dictionary_rag/main.py
```

运行后生成：

```text
projects/day50_metric_dictionary_rag/output/metric_dictionary.json
projects/day50_metric_dictionary_rag/output/metric_rag_chunks.json
projects/day50_metric_dictionary_rag/output/metric_rag_qa_cases.json
projects/day50_metric_dictionary_rag/output/metric_rag_eval_results.json
projects/day50_metric_dictionary_rag/output/metric_dictionary_rag_report.md
```

## 生产映射

真实金融信贷 Agent 里，用户问“通过率怎么算”时，不应该直接生成 SQL 查表。
更稳的路线是：

```text
用户问题
-> 意图识别为 metric_definition
-> 指标字典 / RAG 检索
-> 返回分子、分母、窗口、来源表、适用范围和 citation
-> 写审计
```

离线指标适合解释历史日报、趋势和经营口径。
实时指标必须额外解释窗口、延迟阈值和告警规则。
涉及手机号、身份证号、客户名单等敏感明细的问题，不属于口径问答，应该安全阻断。
