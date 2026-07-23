---
id: Q118
source: interview_core
category: Agent
title: Agent 做血缘追溯时，为什么必须返回证据和影响范围？
generated: 2026-07-23T15:41:19.824932
---

# Agent 做血缘追溯时，为什么必须返回证据和影响范围？

> 来源: 核心题库 | 分类: Agent

血缘追溯通常服务生产排查和审计，不能只回答“可能是某张表的问题”。
如果没有证据，排查人员无法确认 Agent 的结论来自真实血缘图还是模型猜测。
如果没有影响范围，数据团队也不知道要通知哪些业务方、暂停哪些报表、回补哪些任务。

生产级血缘回答至少要包含上游节点、下游节点、依赖关系、加工任务、指标或报表 ID、告警规则和必要的版本信息。
例如 `dws_credit_apply_channel_1d` 异常时，要说明它会影响 `ads_credit_daily_metrics`、
`metric_credit_approval_rate` 和 `report_credit_operation_daily`，并给出对应调度任务或依赖边。

在金融信贷场景里，错误报表可能影响授信经营分析、风控策略复盘、贷后逾期判断和管理层日报。
因此 Agent 的血缘回答必须可追溯、可复核、可审计。