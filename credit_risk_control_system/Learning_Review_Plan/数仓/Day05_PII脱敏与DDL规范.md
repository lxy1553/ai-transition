# Day 05：PII 脱敏 + DDL 规范 + 合规

> 目标：掌握分级脱敏策略设计，能写出满足生产规范的 DDL。

---

## 一、脱敏不是"全删"——是"保留该保留的"（30min）

### 1.1 DataMasker 的四种策略

打开 `src/data/warehouse/dwd_layer.py` 第 48-78 行：

```python
class DataMasker:
    # 策略1: 掩码(Mask) — 保留部分结构，可做统计分析
    @staticmethod
    def mask_name(name):        # 黄敏 → 黄*
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_id_card(id_card):  # 934184...8691 → 934184********8691
        return id_card[:6] + "********" + id_card[-4:]

    @staticmethod
    def mask_phone(phone):      # 13872128795 → 138****8795
        return phone[:3] + "****" + phone[-4:]

    # 策略2: 哈希(Hash) — 不可逆但可去重
    @staticmethod
    def hash_user_id(user_id):  # user_000042 → a1b2c3d4e5f6...
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
```

**策略选择矩阵**：

| 策略 | 可逆性 | 可分析性 | 适用场景 |
|------|--------|---------|---------|
| Mask(掩码) | 部分可逆 | 高（保留结构） | 姓名、身份证、手机 |
| Hash(哈希) | 不可逆 | 仅可去重 | user_id、设备 ID |
| Generalize(泛化) | 不可逆 | 中（高维→低维） | IP→网段、年龄→年龄段 |
| Encrypt(加密) | 可逆（凭密钥） | 高 | 银行卡号（需结算时解密） |

### 1.2 为什么保留部分信息？

```
身份证: 934184********8691
  前6位 934184 = 地区码 → 可衍生"户籍省份"特征
  中间8位 = 出生日期 → 可衍生""年龄"特征
  后4位 = 校验码 → 可去重

全部哈希 → 丢失了地区和年龄两个有用特征
保留前6后4 → 既保护了隐私，又保留了分析价值
```

---

## 二、DDL 写作规范（1h）

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

## 三、动手练习（1.5h）

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

## 四、跨业务思考（30min）

### GDPR "被遗忘权"场景

```
用户要求删除所有个人数据 → 数仓应该怎么做？

方案 A: DELETE FROM ... WHERE user_id = 'xxx'
  问题: Hive/Iceberg 不支持行级删除（或性能极差）
  问题: 删了之后聚合指标会变（昨日 GMV 从 100 变成 99）

方案 B: 软删除 — 保留数据但标记 deleted=True
  优势: 聚合指标不变
  问题: 技术上数据没有被"删除"

方案 C: 匿名化 — 把 user_id 替换为 anonymous_xxx
  优势: 聚合指标不变，原始用户无法识别
  问题: 如果其他表也有 user_id → 关联失效

实际做法: 根据法规选择 B(金融, 必须保留审计) 或 C(电商, 可匿名)
```

---

## 五、检查清单

- [ ] 能说出 Mask/Hash/Generalize/Encrypt 的区别和适用场景
- [ ] 完成了电商脱敏策略代码（4 个函数）
- [ ] 完成了 dwd_order 的生产级 DDL
- [ ] 能解释 GDPR "被遗忘权"在数仓中的应对方案
