# 权限安全与审计

权限配置来源：`config/access_policy.json`

## 角色设计

| 角色 | 能力 |
|------|------|
| `guest` | 只能看 public 级别内容 |
| `customer_service` | 可看内部汇总指标，不能看客户明细、实时风控和 SQL |
| `collection_agent` | 可看贷后汇总指标，不能看客户敏感明细 |
| `credit_ops` | 可看授信经营汇总指标，不能看 SQL |
| `risk_analyst` | 可看风控实时指标和 SQL，不可看客户明细 |
| `credit_dev` | 可看元数据、血缘、SQL 和实时指标，不可看客户明细 |
| `security_admin` | 可看 restricted 内容，用于安全审计和审批场景 |

## 敏感字段

敏感请求关键词包括：

```text
手机号、身份证、银行卡、住址、联系人、客户名单、客户明细、导出、customer_id
```

普通角色命中敏感请求时，Agent 返回 `safely_blocked`，不进入查询工具。

## SQL 暴露控制

- `risk_analyst` 和 `credit_dev` 可以看到 SQL。
- 业务角色默认只看业务解释和 citations。
- 生产环境可进一步把 SQL 脱敏或只开放给技术角色。

## 审计日志

审计输出：

```text
output/audit_log.jsonl
output/warehouse.sqlite:audit_events
```

记录字段：

- request_id
- role
- question
- final_status
- route
- created_at

审计日志不写客户手机号、身份证、联系人、住址等明文敏感信息。
