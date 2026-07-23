---
id: L053
source: learning
category: 数据仓库
title: 请讲讲PII 脱敏 + DDL 规范 + 合规中的DDL 写作规范（1h）
generated: 2026-07-23T15:41:19.865218
---

# 请讲讲PII 脱敏 + DDL 规范 + 合规中的DDL 写作规范（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

### 2.1 生产级 DDL 必须包含的元素

打开 `config/ddl/02_dwd_tables.sql` 看完整示例：


```sql
CREATE TABLE IF NOT EXISTS dwd.dwd_application (
    user_id           STRING    COMMENT '用户ID。原始为空→填充MISSING',
    apply_amount      DOUBLE    COMMENT '申请金额(元)。已修正: 负数→0',
    user_name         STRING    COMMENT '★ 已脱敏: 黄敏→黄*',
    id_card           STRING    COMMENT '★ 已脱敏: 934184********8691',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dq_quarantined    BOOLEAN   COMMENT '★ 隔离标记。dq_score<60→TRUE',
    dt                STRING    COMMENT '分区键 — 日期 YYYY-MM-DD'
)
COMMENT '清洗+脱敏后的用户申请明细 — dq_score<60记录被隔离'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_application',          -- 从哪来
    'transformation' = 'clean_application()',         -- 做了什么
    'pii_columns' = 'user_name,id_card,phone,ip_address',  -- 敏感列
    'retention_days' = '365',                         -- 保留多久
    'data_owner' = '风控团队',
    'update_frequency' = 'daily'
);

```

### 2.2 COMMENT 的写作标准


```
好的 COMMENT = 含义 + 格式/阈值 + 风险方向（如果是特征列）

示例:
  ✓ "近30天深夜操作占比(22-05时)。>60%→高度可疑"     ← 含义+阈值+方向
  ✗ "深夜操作占比"                                   ← 只有含义
  ✗ "night_ops_ratio_30d"                            ← 重复列名

  ✓ "已脱敏: 黄敏→黄*"。                              ← 原值→脱敏值
  ✗ "脱敏后的姓名"                                    ← 没说明怎么脱敏

  ✓ "分区键 — 申请日期 YYYY-MM-DD"                    ← 含义+格式
  ✗ "日期"                                           ← 太简略

```

### 2.3 TBLPROPERTIES 的必备项


```
必须包含:
  'source_system' / 'source_table'  — 数据来源
  'retention_days'                   — 生命周期
  'pii_columns'（如有）              — 敏感列清单
  'update_frequency'                 — 更新频率

建议包含:
  'data_owner'                       — 负责人
  'transformation'                   — 转换规则简述

```

---