# Day 49 - 信贷主题域与 Agent 意图识别

这个项目用于 Day 49 的本地练习：把金融信贷主题域和 Agent 意图分类连起来。

它不连接真实数据库或大模型，而是用模拟主题域、规则和用户问题说明生产路由边界。

## 练习目标

- 梳理授信、额度、风控、放款、还款、逾期、催收主题域。
- 区分离线指标、实时状态、口径解释、血缘追溯、敏感导出和澄清问题。
- 生成主题域目录、意图分类规则、样例分类结果、路由图和报告。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day49_credit_domain_intent/main.py
```

运行后生成：

```text
projects/day49_credit_domain_intent/output/credit_domain_catalog.json
projects/day49_credit_domain_intent/output/intent_classification_rules.json
projects/day49_credit_domain_intent/output/intent_classification_cases.json
projects/day49_credit_domain_intent/output/credit_domain_intent_routing.mmd
projects/day49_credit_domain_intent/output/credit_domain_intent_report.md
```

## 生产映射

Agent 的第一步不是直接生成 SQL，而是做两层判断：

```text
用户问题
-> 主题域识别
-> 意图识别
-> 工具路线选择
-> 权限 / 前置条件 / 审计
```

典型路线：

- 历史趋势、日报、按渠道/产品分析：离线指标查询；
- 近 5 分钟、当前异常、实时告警：实时指标或告警工具；
- 口径、怎么算、分子分母：RAG 口径问答；
- 来自哪些表、上下游：血缘工具；
- 导出手机号、身份证号、客户名单：安全阻断。
