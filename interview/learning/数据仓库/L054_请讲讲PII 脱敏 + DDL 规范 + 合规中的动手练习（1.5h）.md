---
id: L054
source: learning
category: 数据仓库
title: 请讲讲PII 脱敏 + DDL 规范 + 合规中的动手练习（1.5h）
generated: 2026-07-23T15:41:19.865340
---

# 请讲讲PII 脱敏 + DDL 规范 + 合规中的动手练习（1.5h）

> 来源: 学习复习计划 | 分类: 数据仓库

### 练习 1：为电商数据写脱敏策略（45min）


```python
# ★ 参考答案

def mask_收货人姓名(name: str) -> str:
    """掩码: 张三→张*。保留姓氏用于地域分析"""
    if not name or not isinstance(name, str):
        return "***"
    return name[0] + "*" * (len(name) - 1)

def mask_收货手机号(phone: str) -> str:
    """掩码: 保留前3后4, 可分析运营商号段"""
    if not phone or not isinstance(phone, str) or len(phone) < 11:
        return "INVALID_PHONE"
    return phone[:3] + "****" + phone[-4:]

def generalize_收货地址(address: str) -> str:
    """
    泛化: "北京市朝阳区望京街道XX小区3号楼502" → "北京市朝阳区"
    保留区级用于物流区域分析，去掉门牌号保护隐私
    """
    if not address or not isinstance(address, str):
        return "UNKNOWN"
    # 提取到区级: 按"市"和"区"切
    parts = address.split('区')
    if len(parts) >= 2:
        return parts[0] + '区'
    parts = address.split('县')
    if len(parts) >= 2:
        return parts[0] + '县'
    return "UNKNOWN"

def hash_支付卡号(card_no: str) -> str:
    """哈希: SHA256 不可逆，只用于去重和关联"""
    if not card_no or not isinstance(card_no, str):
        return "INVALID"
    import hashlib
    return hashlib.sha256(card_no.encode()).hexdigest()[:16]

```

### 练习 2：写生产级 DDL（30min）

为电商的 `dwd_order` 写生产级 DDL。要求：
- 至少 8 个业务字段 + COMMENT
- PARTITIONED BY
- TBLPROPERTIES 至少 4 项
- 标注 PII 列


```sql
-- ★ 参考答案
CREATE TABLE IF NOT EXISTS dwd.dwd_order (
    order_id          STRING    COMMENT '订单ID。原始为空→MISSING',
    user_id           STRING    COMMENT '用户ID',
    pay_amount        DOUBLE    COMMENT '支付金额(元)。已修正:负数→0',
    shipping_address  STRING    COMMENT '★ 收货地址(已脱敏:保留到区级)',
    phone             STRING    COMMENT '★ 手机号(已脱敏:138****0000)',
    status            STRING    COMMENT '订单状态(已标准化):PAID/SHIPPED/RETURNED',
    category          STRING    COMMENT '商品品类',
    province          STRING    COMMENT '省份(从address解析)。UNKNOWN→10分',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dt                STRING    COMMENT '分区键 — 下单日期 YYYY-MM-DD'
)
COMMENT '清洗后的电商订单明细 — PII列已脱敏'
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