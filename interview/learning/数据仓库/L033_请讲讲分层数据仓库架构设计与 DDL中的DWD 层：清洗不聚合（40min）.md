---
id: L033
source: learning
category: 数据仓库
title: 请讲讲分层数据仓库架构设计与 DDL中的DWD 层：清洗不聚合（40min）
generated: 2026-07-23T15:41:19.862399
---

# 请讲讲分层数据仓库架构设计与 DDL中的DWD 层：清洗不聚合（40min）

> 来源: 学习复习计划 | 分类: 数据仓库

### 3.1 DWD 层对 ODS 做了什么

打开 `src/data/warehouse/dwd_layer.py`，看 `clean_application()` 方法的 6 个步骤：


```
Step 1: 必填检查 → user_id 为空扣 30 分
Step 2: 金额修正 → 负数清零、空值填 0
Step 3: 标准化   → product_type: cash_loan → CASH_LOAN
Step 4: 脱敏     → 姓名: 黄敏 → 黄*
Step 5: 收入修正 → 空值填 0
Step 6: 隔离     → dq_score < 60 的不入下游

```

**关键：DWD 层"清洗但不聚合"**

- ODS 一行 = DWD 一行（行数不变）
- 只是这一行的内容变干净了、变安全了
- 聚合是 DWS 层的事

### 3.2 阅读 DDL 对比

打开 `config/ddl/01_ods_tables.sql` 和 `config/ddl/02_dwd_tables.sql`，对比同一列的 COMMENT 变化：


```sql
-- ODS:
user_name STRING COMMENT '★ 用户真实姓名(明文PII)'

-- DWD:
user_name STRING COMMENT '★ 已脱敏: 黄敏→黄*'

```

COMMENT 的变化 = 数据在层间流转的"日志"。

---