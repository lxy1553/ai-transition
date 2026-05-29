# 金融信贷数仓 RAG 助手

这个项目是一个生产级 RAG 项目雏形，面向金融信贷开发 / 大数据开发工程师背景。
它模拟真实信贷公司里的知识问答场景：授信政策、风控规则、数仓表结构、还款逾期、权限合规。

项目重点不是“模型回答一段话”，而是把 RAG 做成可入库、可检索、可权限过滤、
可引用、可审计、可评测的工程链路。

## 业务背景

信贷团队常见问题包括：

- 授信通过率应该查哪张表，口径是什么？
- 反欺诈拒绝规则和人工复核规则有什么区别？
- 逾期 DPD、M1、M2 在数仓里怎么落表？
- 客服能不能查询客户手机号或身份证？
- 贷后催收同事能看到哪些还款和逾期字段？
- RAG 回答为什么必须返回引用来源？

这些问题不适合只靠模型自由回答。
生产系统必须基于可信资料回答，并结合权限、敏感字段、引用来源和审计日志。

## 项目结构

```text
projects/credit_rag_warehouse_assistant/
├── config/access_policy.json
├── docs/architecture.md
├── docs/api_contract.md
├── eval/eval_cases.json
├── knowledge/
├── warehouse/warehouse_catalog.json
├── main.py
└── output/
```

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/credit_rag_warehouse_assistant/main.py --rebuild --demo --eval
```

单独提问：

```bash
python3 projects/credit_rag_warehouse_assistant/main.py \
  --question "授信通过率应该查哪张表，口径是什么？" \
  --role credit_dev
```

测试权限拒答：

```bash
python3 projects/credit_rag_warehouse_assistant/main.py \
  --question "客服可以查询客户身份证号吗？" \
  --role customer_service
```

## 输出文件

```text
output/rag_index.sqlite
output/demo_answers.json
output/eval_results.json
output/evaluation_report.md
output/audit_log.jsonl
```

## 生产能力清单

| 能力 | 本项目实现 |
|------|------------|
| 离线入库 | 读取 `knowledge/*.md`，解析 metadata，切 chunk，写 SQLite |
| 数仓上下文 | `warehouse_catalog.json` 描述 ODS / DWD / DWS / ADS 分层和表字段 |
| 权限控制 | 基于角色、security_level 和 allowed_roles 过滤 chunk |
| 敏感拦截 | 手机号、身份证、银行卡、客户名单等问题提前拒答 |
| 检索 | 关键词 + 中文业务词 + 表名字段命中打分 |
| 引用来源 | 返回 doc_id、title、chunk_id、source_path、position |
| 审计 | 每次问答写 `audit_log.jsonl` |
| 评测 | 固定 eval cases 检查 should_answer 和 expected_sources |

## 面试讲法

这个项目可以这样讲：

> 我做了一个金融信贷数仓 RAG 助手。
> 离线侧把授信政策、风控规则、数仓数据字典、还款逾期和合规文档入库；
> 在线侧根据用户角色做权限过滤，再检索授权资料，返回答案和 citations。
> 系统不会把敏感资料直接交给模型，也不会只返回自然语言；
> 每次回答都有 request_id、引用来源和审计日志，可以定位是资料问题、召回问题、权限问题还是回答问题。
