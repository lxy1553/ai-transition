---
id: L035
source: learning
category: 数据仓库
title: 请讲讲分层数据仓库架构设计与 DDL中的ADS 层：数据产品（30min）
generated: 2026-07-23T15:41:19.862612
---

# 请讲讲分层数据仓库架构设计与 DDL中的ADS 层：数据产品（30min）

> 来源: 学习复习计划 | 分类: 数据仓库

打开 `config/ddl/04_ads_tables.sql`，看三种数据产品的设计：


```
ads_training_samples    → 消费者: XGBoost 模型训练   格式: Parquet
ads_model_monitor_daily → 消费者: Grafana 监控大盘   格式: CSV
ads_portfolio_analysis  → 消费者: 风控报表/BI        格式: JSON

```

**核心原则：每个 ADS 表对应一个明确的消费者。不是"数据都有了你们自己查"，而是"你们要什么我给你们什么"。**

---