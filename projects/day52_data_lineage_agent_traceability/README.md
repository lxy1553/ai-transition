# Day 52 - 数据血缘 + Agent 可追溯

这个项目用于 Day 52 的本地练习：把金融信贷离线指标、实时指标、加工任务和下游报表整理成
数据血缘图，再让 Agent 通过血缘工具回答“这个指标来自哪里、影响哪些下游、告警证据是什么”。

它不连接真实血缘平台，也不调用真实大模型。
今天重点是：血缘追溯不是解释口径，也不是查当前指标值，而是回答来源、加工链路和影响范围。

## 练习目标

- 建立信贷离线指标血缘：ODS -> DWD -> DWS -> ADS -> 指标 -> 报表。
- 建立实时告警血缘：实时事件 -> 实时任务 -> 实时指标 -> 告警。
- 支持上游来源追溯、下游影响分析和实时告警证据解释。
- 对敏感明细导出做安全阻断。
- 生成血缘图、问答样例、评测结果和 Markdown 报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day52_data_lineage_agent_traceability/main.py
```

运行后生成：

```text
projects/day52_data_lineage_agent_traceability/output/lineage_graph.json
projects/day52_data_lineage_agent_traceability/output/lineage_mermaid.md
projects/day52_data_lineage_agent_traceability/output/lineage_qa_cases.json
projects/day52_data_lineage_agent_traceability/output/lineage_eval_results.json
projects/day52_data_lineage_agent_traceability/output/data_lineage_agent_report.md
```

## 生产映射

真实金融信贷 Agent 里，血缘工具通常用于这些问题：

```text
授信通过率来自哪些上游表？
如果 DWS 授信渠道汇总表异常，会影响哪些报表？
实时风控拒绝率告警来自哪些事件和任务？
昨天日报通过率异常，应该先排查哪些链路？
```

Agent 回答血缘问题时，要返回上游节点、加工任务、下游节点、证据来源和影响范围。
如果用户要求导出客户手机号、身份证号或客户名单，血缘工具不能继续查明细，应进入安全阻断。
