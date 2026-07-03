# Day 57 - 数据质量 + 错误治理

金融信贷离线/实时仓库数据质量规则、质量状态路由、错误治理和 Bad Case 回归验证。

## 为什么需要这个项目？

数据质量问题不是"数仓同学自己的事"。只要仓库数据不稳定，Agent 就会把错误结果包装成看起来合理的回答。

例如：
- 实时事件重复 → 实时申请量虚高
- 分区延迟到达 → 日报指标偏低
- 补偿任务没跑完 → 逾期率短时间异常
- 状态字段为空 → 风控拒绝率解释失真

本项目的核心产出是：**数据质量 → Agent 风险 → 处理规则 → 回归保护** 这条链路的完整实现。

## 项目结构

```
day57_data_quality_error_governance/
├── README.md                          # 本文件
├── quality_rules.json                 # 10 条数据质量规则清单
├── quality_bad_cases.json             # 10 条质量 Bad Case 回归样例（联动 Day 56）
├── main.py                            # 主脚本：质量检查 + 状态路由 + 回归验证 + 报告生成
└── output/
    ├── quality_governance_results.json  # JSON 格式治理报告
    └── quality_governance_report.md     # Markdown 格式治理报告
```

## 数据质量规则清单（10 条）

| 规则 ID | 分类 | 风险 | 仓库类型 | 质量状态 |
|---------|------|------|----------|----------|
| DQ-001 | 空值（审批结果字段） | high | offline | warning |
| DQ-002 | 重复（申请事件重复落库） | high | realtime | warning |
| DQ-003 | 乱序（结果先于明细） | medium | realtime | warning |
| DQ-004 | 延迟（分区延迟到达） | high | offline | warning |
| DQ-005 | 补偿（补偿任务未完成） | high | offline | warning |
| DQ-006 | 幂等（幂等写入失败） | high | both | **blocked** |
| DQ-007 | 状态不一致（离线/实时） | high | both | warning |
| DQ-008 | 晚到数据（超过窗口延迟阈值） | medium | realtime | warning |
| DQ-009 | 空分区 | critical | offline | **blocked** |
| DQ-010 | 数据倾斜（单渠道异常） | medium | realtime | warning |

## 三种质量状态与路由决策

```
quality_ok → normal_answer   → 正常回答，数据可信
quality_warning → degraded_answer → 降级说明，标注不确定性和可信度
quality_blocked → blocked_answer  → 阻断回答，不给确定结论，给排查建议
```

## 运行方式

```bash
# 在项目根目录下
python projects/day57_data_quality_error_governance/main.py
```

或：

```bash
cd projects/day57_data_quality_error_governance
python main.py
```

不需要外部依赖（纯 Python 标准库），不调用真实 LLM。

## 运行输出

```
[1/5] 加载数据质量规则清单...     已加载 10 条
[2/5] 加载质量 Bad Case 回归样例... 已加载 10 条
[3/5] 执行质量检查...             整体状态 + 路由决策
[4/5] 执行 Bad Case 回归验证...    10/10 通过
[5/5] 生成治理报告...             JSON + Markdown
```

## Bad Case 与 Day 56 联动

10 条 bad case 每条对应一个 Day 56 评测场景和一条质量规则：

- **BC-001** 空分区 → Day 56 空分区查询场景 → DQ-009
- **BC-002** 重复事件 → Day 56 告警误报场景 → DQ-002
- **BC-003** 分区延迟 → Day 56 实时延迟场景 → DQ-004
- **BC-004** 补偿未完成 → Day 56 口径冲突场景 → DQ-005
- **BC-005** 空值 → Day 56 有界解释场景 → DQ-001
- **BC-006** 幂等失败 → Day 56 口径冲突场景 → DQ-006
- **BC-007** 乱序事件 → Day 56 实时延迟场景 → DQ-003
- **BC-008** 晚到数据 → Day 56 实时延迟场景 → DQ-008
- **BC-009** 状态不一致 → Day 56 有界解释场景 → DQ-007
- **BC-010** 数据倾斜 → Day 56 告警误报场景 → DQ-010

## 审计字段设计（为 Day 58 准备）

定义了 4 层 19 个审计字段：

1. **请求层（request_level）**：request_id、trace_id、timestamp、user_question、agent_intent
2. **质量检查层（quality_check_level）**：quality_status、triggered_rules、quality_detail、data_freshness、completeness_score、duplication_rate
3. **决策层（decision_level）**：action、confidence、degradation_reason、block_reason、suggestions
4. **回归层（regression_level）**：bad_case_id、regression_check_passed、linked_day56_scenario

## 面试要点

- **Q131**：为什么金融信贷仓库 Agent 必须感知数据质量状态？—— 因为 Agent 依赖离线分区、实时窗口、补偿任务和上游事件质量，不知道数据是否完整就可能把暂时错误的数据说成确定结论。
- **Q132**：数据质量问题为什么要接入错误治理和回归测试？—— 因为这不是一次性故障，会重复出现。只靠人工排查，下次还会犯同样错。正确做法：规则 → 审计 → Bad Case → 回归。
