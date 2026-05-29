---
doc_id: security_compliance
title: 信贷数据权限与合规审计规范
domain: compliance
security_level: public
allowed_roles: credit_dev,risk_analyst,collection_operator,customer_service,admin
warehouse_tables: dim_customer_profile,dwd_credit_application,dwd_loan_account,dwd_overdue_detail
---

# 信贷数据权限与合规审计规范

信贷数据包含大量敏感信息，RAG 系统必须先做权限控制，再做检索和回答。
不能把无权限 chunk 放进模型上下文，也不能在 citations 中暴露敏感文档标题、路径或字段。

手机号、身份证、银行卡、精确住址、通讯录、客户名单和明文证件信息属于敏感信息。
普通客服只能获取公开说明和合规答复，不能通过 RAG 查询客户级敏感字段。

每次问答必须记录 request_id、用户角色、问题、命中资料、拒答原因和 citations。
如果出现越权风险，要能根据 audit log 回放当时的检索结果和策略命中情况。

生产系统中，权限过滤应发生在 LLM 生成之前。
prompt 只能作为最后一层约束，不能替代鉴权、metadata filter、敏感词识别和审计日志。

