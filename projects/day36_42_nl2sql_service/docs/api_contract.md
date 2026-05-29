# Day 37 - 接口规范

## `GET /health`

用途：检查服务是否可用，以及 Day 35 演示产物是否存在。

响应：

```json
{
  "status": "ok",
  "app_name": "Week 6 NL2SQL Service",
  "env": "dev",
  "version": "0.1.0",
  "demo_ready": true
}
```

## `GET /nl2sql/questions`

用途：列出当前演示版支持的问题。

响应：

```json
{
  "success": true,
  "questions": ["本周逾期率比上周变化多少？"]
}
```

## `POST /nl2sql/ask`

用途：提交自然语言问题，返回业务解释和链路状态。

请求：

```json
{
  "question": "本周逾期率比上周变化多少？",
  "user_id": "demo_user",
  "include_trace": true
}
```

响应：

```json
{
  "request_id": "...",
  "question": "本周逾期率比上周变化多少？",
  "final_status": "answered",
  "answer": "当前周期逾期率为 7.03%，上期为 8.56%，较上期下降 1.53 个百分点。",
  "key_findings": [],
  "risk_notes": [],
  "follow_up_questions": [],
  "pipeline": {
    "parse": "available",
    "sql_generation": "passed",
    "sql_validation": "passed",
    "query_execution": "executed",
    "result_interpretation": "available"
  },
  "sql": "..."
}
```

## `GET /nl2sql/trace/{request_id}`

用途：按 request_id 查看审计轨迹。

生产里这个接口通常只给管理员或研发排查使用。

