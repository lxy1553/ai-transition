# API 契约草案

真实上线时，这个 RAG 能力可以包装成 HTTP API。

## POST /credit-rag/ask

### Request

```json
{
  "question": "授信通过率应该查哪张表，口径是什么？",
  "user_id": "u001",
  "role": "credit_dev",
  "business_domain": "credit",
  "top_k": 5
}
```

### Response

```json
{
  "request_id": "req_xxx",
  "answer": "根据已授权资料，授信通过率...",
  "answer_status": "answered",
  "cannot_answer_reason": null,
  "citations": [
    {
      "doc_id": "warehouse_dictionary",
      "title": "金融信贷数仓数据字典",
      "chunk_id": "chunk_xxx",
      "source_path": "knowledge/warehouse_dictionary.md",
      "position": 3,
      "security_level": "internal"
    }
  ],
  "audit": {
    "role": "credit_dev",
    "blocked_by_policy": false,
    "retrieved_chunks": 5,
    "used_chunks": 3
  }
}
```

## 错误与拒答

| 场景 | 处理 |
|------|------|
| 空问题 | 返回参数错误 |
| 敏感信息导出 | 返回 `blocked_sensitive_query` |
| 角色无权限 | 返回 `no_authorized_context` |
| 没有命中资料 | 返回 `no_relevant_context` |
| top_k 越界 | 返回参数错误 |

## 关键原则

答案正文和 citations 都必须经过同一套权限过滤。
不能出现“答案没泄露，但引用来源泄露敏感文档标题或路径”的情况。

