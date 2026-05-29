# 架构说明

## 总体链路

```text
知识文档 + 数仓目录
-> 文档解析
-> chunk 切分
-> metadata / 权限标签
-> SQLite 索引
-> 用户问题
-> 敏感意图识别
-> 角色权限过滤
-> 检索与排序
-> 基于授权 chunk 生成答案
-> citations / request_id / audit log
-> 评测集回归
```

## 离线入库

离线入库负责把信贷知识变成可检索、可过滤、可引用的知识单元。

本项目的入库资料包括：

- 授信政策和额度审批规则；
- 风控反欺诈规则；
- 金融信贷数据仓库表结构；
- 还款、逾期、贷后和催收口径；
- 权限、敏感信息和合规审计规范。

每个文档都带 metadata：

- `doc_id`
- `domain`
- `security_level`
- `allowed_roles`
- `warehouse_tables`

这些字段会进入 chunk metadata，用于在线检索、权限过滤和引用返回。

## 在线问答

在线问答不直接把所有检索结果交给模型。
它会先判断用户角色是否有权限访问相关 chunk，再用授权 chunk 组织回答。

如果用户问题涉及身份证、手机号、银行卡、客户名单等敏感信息，系统会先拒答。
拒答结果也会写入审计日志，便于后续复盘和合规检查。

## 生产扩展

这个本地项目可以继续扩展成真实服务：

- SQLite 换成 OpenSearch / Elasticsearch / 向量数据库；
- 本地规则检索换成 hybrid search + rerank；
- extractive answer 换成 LLM answer，但 prompt 只能使用授权上下文；
- CLI 包装成 FastAPI；
- audit log 写入日志平台或审计库；
- eval cases 接入 CI 回归。

