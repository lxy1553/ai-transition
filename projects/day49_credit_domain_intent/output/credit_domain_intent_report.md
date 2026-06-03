# Day 49 信贷主题域与 Agent 意图识别报告

## 信贷主题域目录

| 主题域 | 说明 | 常见指标 | 主要离线表 | 实时事件 |
|--------|------|----------|------------|----------|
| 授信申请 | 用户发起授信申请、提交资料、渠道进入和申请状态流转。 | 申请量, 审批通过率, 拒绝率, 渠道申请占比 | dws_credit_apply_channel_1d, ads_credit_daily_metrics | credit_apply_submitted |
| 额度管理 | 额度审批、额度调整、额度使用和额度冻结。 | 授信额度, 额度使用率, 额度冻结数 | dwd_credit_limit_detail_di, ads_credit_daily_metrics | credit_limit_changed |
| 风控决策 | 策略命中、审批拒绝、风险等级和实时反欺诈。 | 策略命中率, 实时拒绝率, 高风险占比 | ads_risk_strategy_dashboard, dws_credit_apply_channel_1d | risk_decision_made |
| 放款 | 放款申请、放款成功、放款失败和放款金额。 | 放款金额, 放款成功率, 放款失败数 | ads_credit_daily_metrics, dwd_loan_disbursement_detail_di | loan_disbursed, loan_disbursement_failed |
| 还款 | 主动还款、自动扣款、还款失败和渠道异常。 | 还款成功率, 还款失败数, 失败原因分布 | dws_repayment_overdue_1d, dwd_loan_repayment_detail_di | repayment_succeeded, repayment_failed |
| 逾期贷后 | 逾期天数、账龄、M1/M2、贷后表现和催收前置分析。 | 逾期率, M1 余额, 迁徙率, 回收率 | dws_repayment_overdue_1d, ads_postloan_daily_metrics | overdue_status_changed |
| 催收 | 催收触达、承诺还款、催收结果和坐席效果。 | 触达率, 承诺还款率, 催回金额 | dwd_collection_action_detail_di, ads_collection_daily_metrics | collection_action_created |

## 意图分类规则

| 意图 | 触发信号 | 必要上下文 | 兜底策略 |
|------|----------|------------|----------|
| offline_metric | 昨天, 近 7 天, 上月, 趋势, 按渠道, 按产品, 日报 | 时间范围, 指标, 维度 | 缺少时间范围或指标时进入 clarification。 |
| realtime_metric | 近 5 分钟, 当前, 实时, 是否异常, 突增 | 窗口, 业务线或维度, 实时指标 | 缺少窗口或维度时进入 clarification。 |
| metric_definition | 口径, 怎么算, 定义, 分子, 分母 | 指标名 | 没有可靠引用时返回 insufficient_evidence。 |
| lineage | 来自哪些表, 来源, 血缘, 上游, 下游 | 指标或表名 | 找不到血缘时返回资料不足。 |
| sensitive_export | 导出, 手机号, 身份证, 客户名单, 银行卡, 明细全部 | 用户权限 | 默认安全阻断。 |

## 样例分类结果

| Case | 用户问题 | 主题域 | 意图 | 风险 | 路由原因 |
|------|----------|--------|------|------|----------|
| D49-001 | 近 7 天各渠道授信通过率趋势。 | 授信申请 | offline_metric | low | 历史趋势和渠道维度属于离线指标查询。 |
| D49-002 | 近 5 分钟 STR_BLACKLIST 策略拒绝率是否异常？ | 风控决策 | realtime_metric | medium | 近 5 分钟和是否异常是实时窗口信号。 |
| D49-003 | 审批通过率的分子和分母分别是什么？ | 授信申请 | metric_definition | low | 询问指标口径，应走 RAG 口径问答并返回引用。 |
| D49-004 | 逾期率来自哪些上游表和下游报表？ | 逾期贷后 | lineage | low | 询问来源和下游影响范围，应走血缘工具。 |
| D49-005 | 导出所有逾期客户的手机号和身份证号。 | 逾期贷后 | sensitive_export | high | 客户敏感明细导出必须阻断并审计。 |
| D49-006 | 看一下还款失败是不是异常。 | 还款 | clarification_required | medium | 缺少窗口、渠道和判断口径，不能直接查实时或离线指标。 |

## 意图分布

| 意图 | 数量 |
|------|------|
| clarification_required | 1 |
| lineage | 1 |
| metric_definition | 1 |
| offline_metric | 1 |
| realtime_metric | 1 |
| sensitive_export | 1 |

## 生产启示

- Agent 先识别主题域，再识别意图，最后才能选择工具路线。
- 离线、实时、口径、血缘和敏感导出是完全不同的处理路径。
- 意图不清或缺少必要上下文时，正确行为是澄清，不是猜测。
- 敏感导出不进入 SQL、实时事件或导出工具，必须安全阻断并审计。
