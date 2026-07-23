---
id: L036
source: learning
category: 数据仓库
title: 请讲讲分层数据仓库架构设计与 DDL中的DDL 写作规范（30min）
generated: 2026-07-23T15:41:19.862743
---

# 请讲讲分层数据仓库架构设计与 DDL中的DDL 写作规范（30min）

> 来源: 学习复习计划 | 分类: 数据仓库

### 6.1 生产级 DDL 必须包含的元素


```sql
CREATE TABLE IF NOT EXISTS {layer}.{table_name} (
    col1  TYPE  COMMENT '含义。格式/阈值/风险方向',
    ...
    dt    STRING COMMENT '分区键 YYYY-MM-DD'
)
COMMENT '表的业务描述'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'mysql_xxx',     -- 数据从哪个系统来
    'ingest_method' = 'binlog',        -- 怎么接入的
    'pii_columns' = 'col1,col2',       -- 哪些列是敏感信息
    'retention_days' = '90',           -- 保留多少天
    'data_owner' = '风控团队',         -- 谁对这表负责
    'update_frequency' = 'daily'       -- 多久更新一次
);

```

### 6.2 练习：手写 DDL（30min）

为电商的 `dwd_order` 表写 DDL。要求包含：
- 至少 8 个业务字段
- 每个字段有 COMMENT
- TBLPROPERTIES 包含 source_system、retention_days
- 标注 PII 列


```sql
-- ★ 参考答案
CREATE TABLE IF NOT EXISTS dwd.dwd_order (
    order_id          STRING    COMMENT '订单ID。原始为空→MISSING',
    user_id           STRING    COMMENT '用户ID。必填字段',
    pay_amount        DOUBLE    COMMENT '支付金额(元)。已修正: 负数→0',
    shipping_address  STRING    COMMENT '★ 收货地址(已脱敏: 北京市朝阳区→北京市**区)',
    phone             STRING    COMMENT '★ 手机号(已脱敏: 138****0000)',
    status            STRING    COMMENT '订单状态(已标准化): PAID/SHIPPED/DELIVERED/RETURNED/UNKNOWN',
    category          STRING    COMMENT '商品品类: 电子/服装/食品/图书',
    province          STRING    COMMENT '省份(从address解析)。未知→UNKNOWN',
    order_time        TIMESTAMP COMMENT '下单时间',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dt                STRING    COMMENT '分区键 — 下单日期 YYYY-MM-DD'
)
COMMENT '清洗后的电商订单明细 — dq_score<60隔离'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_order',
    'transformation' = 'clean_order()',
    'pii_columns' = 'shipping_address,phone',
    'retention_days' = '365',
    'update_frequency' = 'daily'
);

```

---