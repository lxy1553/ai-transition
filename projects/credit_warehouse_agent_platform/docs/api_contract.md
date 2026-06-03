# API 契约

当前项目提供 CLI 入口；生产服务化时建议包装成以下 HTTP API。

## 健康检查

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "app_name": "credit-warehouse-agent-platform",
  "version": "2026-06-demo"
}
```

## 构建仓库

```http
POST /warehouse/build
```

用途：触发离线数据接入、治理、指标加工和实时聚合。

响应：

```json
{
  "applications": 12,
  "repayments": 10,
  "realtime_events": 8,
  "quality_errors": 0,
  "alerts": 2
}
```

## Agent 问答

```http
POST /agent/ask
```

请求：

```json
{
  "question": "本周授信通过率按渠道表现如何？",
  "role": "risk_analyst"
}
```

响应：

```json
{
  "request_id": "uuid",
  "final_status": "answered",
  "route": ["security_guard", "intent_router", "metric_resolver", "sql_guard", "warehouse_query", "result_interpreter", "audit_logger"],
  "answer": "授信通过率最高的是...",
  "citations": [
    {
      "type": "metric",
      "id": "credit_approval_rate",
      "source_table": "dws_credit_daily_metrics"
    }
  ],
  "sql": "select ..."
}
```

## 运行评测

```http
POST /evaluation/run
```

响应：

```json
{
  "summary": {
    "total_cases": 8,
    "passed_cases": 8,
    "failed_cases": 0,
    "pass_rate": 1.0
  }
}
```

## 审计查询

```http
GET /audit/{request_id}
```

生产要求：该接口只能给安全审计、技术排查或授权管理员使用。
