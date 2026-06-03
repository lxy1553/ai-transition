# 架构说明

## 总体链路

```text
批量数据 CSV
  -> ODS 原始层
  -> DWD 清洗明细层
  -> DWS 指标汇总层
  -> Agent 指标问答

实时事件 JSONL
  -> ODS_RT 实时原始层
  -> RT_DWS 分钟聚合层
  -> 实时告警
  -> Agent 实时问答

配置与治理
  -> warehouse_catalog
  -> metrics_catalog
  -> access_policy
  -> agent_routes

Agent 请求
  -> security_guard
  -> intent_router
  -> metric / realtime / lineage tools
  -> result_interpreter
  -> audit_logger
```

## 模块说明

| 模块 | 作用 | 准生产映射 |
|------|------|------------|
| 数据接入 | 读取批量和实时样例数据 | 生产可替换为调度任务、Kafka、Flink |
| 数仓治理 | 分层建表、数据质量校验、元数据入库 | 生产可接 Hive、Iceberg、dbt、数据地图 |
| 指标平台 | 管理指标定义、公式、来源表、血缘和密级 | 生产可接指标平台或语义层 |
| 实时链路 | 聚合风险事件并生成告警 | 生产可接 Flink SQL、Prometheus、告警平台 |
| 权限安全 | 角色、密级、敏感请求和 SQL 暴露控制 | 生产可接 IAM、数据权限系统、DLP |
| Agent 编排 | 根据意图选择指标、实时、血缘或安全阻断路线 | 生产可接 LLM tool calling |
| 审计评测 | 记录 request_id、路线、状态，运行固定评测集 | 生产可接审计库、日志平台、评测平台 |

## 关键边界

- Agent 不直接访问明细敏感字段。
- 指标查询必须经过权限判断。
- SQL 是否返回由角色开关控制。
- 实时风险事件只允许授权角色查看。
- 所有问答都写审计日志。
- 评测集必须覆盖成功、拒答、实时、血缘和权限阻断。
