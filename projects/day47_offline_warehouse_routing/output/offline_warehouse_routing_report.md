# Day 47 信贷离线仓库分层与 Agent 离线路由报告

## 分层原则

- ODS 保留业务原始数据，默认不作为 Agent 查询入口。
- DWD 是清洗后的明细事实层，只在有权限、精确过滤和 limit 时查询。
- DWS 是主题汇总层，适合维度分析、趋势分析和指标聚合。
- ADS 是应用指标层，适合经营日报、看板总览和高频问答。
- Agent 查询离线指标时优先 ADS/DWS，避免直接扫 ODS/DWD 明细。

## 分层表清单

| 层级 | 表名 | 主题 | 粒度 | Agent 用法 |
|------|------|------|------|------------|
| ODS | ods_credit_apply_raw_di | 授信申请 | 一条原始授信申请记录 | 不建议 Agent 直接查询；只用于排查明细和上游来源。 |
| ODS | ods_repayment_raw_di | 还款流水 | 一条原始还款流水 | 不建议直接查；涉及客户、银行卡和交易明细。 |
| DWD | dwd_credit_apply_detail_di | 授信申请 | 清洗后的授信申请明细 | 只在需要明细过滤且有权限时使用，必须带时间范围和 limit。 |
| DWD | dwd_loan_repayment_detail_di | 还款 | 清洗后的还款明细 | 用于还款明细分析；普通指标优先走 DWS 或 ADS。 |
| DWS | dws_credit_apply_channel_1d | 授信经营 | 按日期、渠道汇总的授信申请指标 | 适合 Agent 查询渠道维度的申请量、通过率和拒绝率。 |
| DWS | dws_repayment_overdue_1d | 贷后还款 | 按日期、产品汇总的还款和逾期指标 | 适合 Agent 查询逾期率、还款成功率和贷后趋势。 |
| ADS | ads_credit_daily_metrics | 信贷日报 | 面向经营日报的一天一行应用指标 | Agent 查询经营日报、总览指标和趋势时的首选入口。 |
| ADS | ads_risk_strategy_dashboard | 风控看板 | 按日期、策略、产品汇总的风控看板指标 | 适合 Agent 查询策略命中率、拒绝率和风险看板指标。 |

## Agent 离线路由样例

| Case | 用户问题 | 预期层级 | 预期表 | 路由原因 |
|------|----------|----------|--------|----------|
| D47-001 | 昨天信贷整体申请量、审批通过率和放款金额是多少？ | ADS | ads_credit_daily_metrics | 经营日报总览优先走 ADS 应用指标表，避免从明细层临时聚合。 |
| D47-002 | 近 7 天各渠道授信通过率趋势。 | DWS | dws_credit_apply_channel_1d | 按渠道分析需要 DWS 汇总层，既保留维度又避免扫描申请明细。 |
| D47-003 | 查一下某个申请 ID 的审批状态和风险等级。 | DWD | dwd_credit_apply_detail_di | 单笔申请明细需要 DWD，但必须先做权限校验、精确过滤和 limit。 |
| D47-004 | 导出昨天所有申请人的手机号和身份证号。 | blocked | none | 敏感明细导出不允许进入离线 SQL 查询链路。 |
| D47-005 | 上个月各产品逾期率变化。 | DWS | dws_repayment_overdue_1d | 贷后产品维度趋势适合 DWS 还款逾期汇总层。 |

## 生产启示

- 离线指标问答不是让 Agent 随便挑表，而是先判断问题粒度和指标用途。
- 总览指标优先 ADS，维度趋势优先 DWS，明细问题必须先过权限和精确过滤。
- ODS 和 DWD 通常包含敏感明细，不能作为普通业务问答的默认入口。
- SQL Validator 要检查分区、limit、只读、敏感字段和扫描成本。
