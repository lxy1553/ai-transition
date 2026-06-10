# Day 56 - 仓库 Agent 端到端评测

这个项目用于 Day 56 的本地练习：为金融信贷离线/实时仓库 Agent 构建端到端评测集。

它不调用真实大模型，也不连接真实仓库。
脚本用规则模拟 Agent 路由、工具结果和评测判定，重点验证：

- 成功回答是否走对工具；
- 空分区是否返回无数据，而不是编造结果；
- 实时延迟是否返回不可判断；
- 告警误报是否能基于证据解释；
- 口径冲突是否澄清或阻断；
- 敏感导出是否安全阻断；
- 工具异常是否降级并写入失败原因。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day56_warehouse_agent_e2e_evaluation/main.py
```

运行后生成：

```text
projects/day56_warehouse_agent_e2e_evaluation/output/e2e_eval_cases.json
projects/day56_warehouse_agent_e2e_evaluation/output/e2e_eval_results.json
projects/day56_warehouse_agent_e2e_evaluation/output/e2e_regression_summary.json
projects/day56_warehouse_agent_e2e_evaluation/output/warehouse_agent_e2e_eval_report.md
```

## 生产映射

真实仓库 Agent 端到端评测不能只看答案像不像。
评测必须检查：

```text
问题 -> 意图识别 -> 工具路由 -> 前置条件 -> 工具结果 -> 安全校验 -> 最终回答 -> 审计
```

只有最终回答、工具路线、拒答类型、证据来源和审计字段都符合预期，才算通过。
