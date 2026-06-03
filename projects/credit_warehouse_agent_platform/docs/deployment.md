# 部署说明

## 本地部署

```bash
cd /Users/lxy/Documents/ai_transition
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 projects/credit_warehouse_agent_platform/main.py --run-all
```

## 验证命令

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 projects/credit_warehouse_agent_platform/main.py \
  --question "今天实时高风险事件和告警情况？" \
  --role risk_analyst
```

```bash
PYTHONPATH=projects/credit_warehouse_agent_platform \
python3 -m unittest discover -s projects/credit_warehouse_agent_platform/tests
```

注意：`--run-all` 和单元测试都会重建本地 SQLite 输出库。
不要把这两个命令并发执行；真实 CI 中应按“构建 -> 测试 -> 交付产物生成”的顺序串行运行。

## 交付产物检查

| 文件 | 用途 |
|------|------|
| `output/warehouse.sqlite` | 本地准生产仓库 |
| `output/data_quality_report.md` | 数据质量报告 |
| `output/realtime_alerts.json` | 实时告警 |
| `output/demo_answers.json` | Agent 演示问题答案 |
| `output/eval_results.json` | 评测结构化结果 |
| `output/evaluation_report.md` | 评测报告 |
| `output/audit_log.jsonl` | 问答审计日志 |
| `output/delivery_report.md` | 总交付报告 |

## 生产替换点

| 本地实现 | 生产替换 |
|----------|----------|
| CSV | 数据接入调度、湖仓表、对象存储 |
| JSONL 实时事件 | Kafka / Pulsar |
| SQLite | Hive / Iceberg / Doris / ClickHouse / PostgreSQL |
| 规则 Agent | LLM Tool Calling + 编排层 |
| 本地审计 JSONL | 审计数据库 / 日志平台 |
| 本地评测 JSON | 评测平台 / CI 回归任务 |

## 发布前检查

- 配置文件里没有真实密钥。
- 敏感问题会返回 `safely_blocked`。
- 业务角色不会看到 SQL。
- 实时问题只有授权角色能访问。
- `evaluation_report.md` 通过率达到预期。
- 审计日志能按 request_id 回放。
