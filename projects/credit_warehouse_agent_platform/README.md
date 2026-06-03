# 金融信贷离线/实时仓库 + Agent 平台

这是一个准生产级金融信贷数据仓库 + Agent 项目。

它把离线仓库、实时风控链路、指标口径、元数据治理、权限安全、Agent 问答、审计日志、评测回归和部署文档打成一个完整交付包。
项目不连接真实生产数据库和真实 LLM，而是使用 CSV、JSONL、SQLite 和规则 Agent 模拟生产链路，保证本地可复现、可演示、可扩展。

## 业务定位

面向金融信贷数据和 AI 应用场景：

- 授信经营分析：申请量、通过率、放款金额、渠道表现。
- 风控实时监控：反欺诈、高风险事件、实时告警。
- 贷后分析：M1 逾期率、还款快照、催收队列。
- 数仓治理：ODS/DWD/DWS/RT 分层、指标口径、表血缘和数据质量。
- Agent 问答：业务用户用自然语言查询指标、口径、血缘和实时告警。
- 安全审计：角色权限、敏感字段拦截、SQL 暴露控制和审计日志。

## 目录结构

```text
projects/credit_warehouse_agent_platform/
├── app/
│   └── platform.py
├── config/
│   ├── access_policy.json
│   ├── agent_routes.json
│   ├── metrics_catalog.json
│   └── warehouse_catalog.json
├── data/
│   ├── batch/
│   └── realtime/
├── docs/
├── eval/
├── output/
├── tests/
└── main.py
```

## 一键运行

在仓库根目录执行：

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 projects/credit_warehouse_agent_platform/main.py --run-all
```

运行后生成：

```text
projects/credit_warehouse_agent_platform/output/warehouse.sqlite
projects/credit_warehouse_agent_platform/output/data_quality_report.md
projects/credit_warehouse_agent_platform/output/realtime_alerts.json
projects/credit_warehouse_agent_platform/output/demo_answers.json
projects/credit_warehouse_agent_platform/output/eval_results.json
projects/credit_warehouse_agent_platform/output/evaluation_report.md
projects/credit_warehouse_agent_platform/output/audit_log.jsonl
projects/credit_warehouse_agent_platform/output/delivery_report.md
```

## 单独提问

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 projects/credit_warehouse_agent_platform/main.py \
  --question "本周授信通过率按渠道表现如何？" \
  --role risk_analyst
```

权限阻断示例：

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 projects/credit_warehouse_agent_platform/main.py \
  --question "导出逾期客户手机号和身份证号" \
  --role customer_service
```

## 回归测试

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 -m unittest discover -s projects/credit_warehouse_agent_platform/tests
```

`--run-all` 和单元测试都会重建本地 SQLite 输出库，验证时请串行执行，不要并发运行。

## 生产能力清单

| 能力 | 本项目实现 |
|------|------------|
| 数据接入 | 批量 CSV + 实时 JSONL |
| 数仓治理 | ODS/DWD/DWS/RT 分层、数据质量报告、元数据目录 |
| 指标口径 | 指标 Catalog、公式、来源表、血缘、权限密级 |
| 实时链路 | 风控事件分钟聚合、P1 告警 |
| 权限安全 | 角色、可访问域、数据密级、敏感问题拦截、SQL 暴露开关 |
| Agent 问答 | 指标查询、口径解释、实时告警、血缘查询、安全拒答 |
| 审计 | JSONL 审计 + SQLite 审计表 |
| 评测 | 固定 eval cases 检查状态、路线、引用和 SQL 暴露 |
| 部署文档 | 架构、数据契约、指标、安全、API、部署和运维说明 |

## 作品集讲法

> 我做了一个准生产金融信贷离线/实时仓库 + Agent 平台。
> 离线侧接入授信申请和还款快照，按 ODS、DWD、DWS 分层治理并沉淀指标口径；
> 实时侧接入风控事件，按分钟聚合并生成高风险告警；
> Agent 侧支持指标问答、口径解释、实时告警和血缘查询，并强制角色权限、敏感字段拦截和审计日志。
> 项目不是单纯 Demo，而是包含数据接入、治理、指标、实时、安全、Agent、审计、评测和部署闭环。
