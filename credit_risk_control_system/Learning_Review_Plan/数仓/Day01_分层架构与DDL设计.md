# Day 01：分层数据仓库架构设计与 DDL

> 目标：理解 ODS→DWD→DWS→ADS 四层架构，能手写表结构 DDL。

---

## 一、为什么需要分层？（30min）

### 1.1 不分层的问题

假设你把所有数据堆在一张表里：

```sql
-- 反模式：一张大表承载所有
CREATE TABLE all_data (
    user_id STRING,
    user_name STRING,       -- 明文姓名
    id_card STRING,          -- 明文身份证
    apply_amount DOUBLE,     -- 有些是 -1000（脏数据）
    product_type STRING,     -- 有些是 NULL
    event_type STRING,       -- 行为事件
    overdue_cnt INT,         -- 聚合后的逾期次数
    ...
);
```

三个致命问题：

| 问题 | 后果 |
|------|------|
| 安全和合规 | 任何人查这张表都能看到明文身份证，违反个人信息保护法 |
| 数据质量 | 分析师不知道 apply_amount=-1000 是脏数据还是真实退款 |
| 复用性差 | 每次有新需求都要重新扫全表 → 10 亿行扫一次 5 分钟 |

### 1.2 分层的解决思路

```
ODS: "我照镜子" — 源系统是什么样，我就是什么样
DWD: "我洗衣服" — 脏数据清洗掉，敏感信息遮挡住，但衣服还是那件衣服
DWS: "我分类叠衣服" — 按人按日期归拢，一件衣服变成统计数字
ADS: "我摆到衣柜里" — 每个抽屉对应一个用途（训练/报表/监控）
```

---

## 二、ODS 层：原始数据 1:1 镜像（1h）

### 2.1 核心原则

**ODS 不做任何处理**。四个原因：

1. **可追溯**：下游数据有问题 → 回到 ODS 查原始值
2. **可重放**：清洗规则变更 → 从 ODS 重新跑，不需要重新接入源系统
3. **可审计**：监管要求"保留原始记录 5 年"，ODS 就是原始记录
4. **解耦**：源系统改造不影响下游（ODS 做缓冲层）

### 2.2 实战：阅读项目代码

打开 `src/data/warehouse/ods_layer.py`：

```python
# 第 30-79 行 — 表元数据管理

@dataclass
class ODSTable:
    """每张 ODS 表的"身份证"

    三个核心字段：
    - source_system: 从哪来？（数据血缘的起点）
    - ingest_method: 怎么来的？（binlog 实时 / API log / SDK / 文件）
    - partition_key: 按什么分区？（决定查询性能）
    """
    name: str
    source_system: str
    ingest_method: str
    partition_key: str = "dt"
    description: str = ""


# ★ 为什么用独立的字典注册所有表？
ODS_TABLES = {
    "ods_application": ODSTable(
        name="ods_application",
        source_system="mysql_credit_core",  # ← 告诉所有人：这表来自 MySQL
        ingest_method="binlog",              # ← 告诉所有人：通过 binlog 同步
        description="用户贷款申请表",
    ),
    "ods_user_behavior": ODSTable(
        name="ods_user_behavior",
        source_system="sdk_analytics",       # ← 来自埋点 SDK
        ingest_method="sdk",
        description="用户行为埋点流",
    ),
}
```

**为什么这么设计？**

- 用 `dataclass` 而不是 `dict`：IDE 自动补全 + 类型安全 + 不会被意外修改
- 单独定义 `ODS_TABLES`：新增表只需加一行，代码自动感知（`ODS_TABLES.values()` 遍历）
- `source_system` 是强制字段：强制开发者注明来源 → 数据血缘从这里开始

### 2.3 动手：看实际 ODS 数据

```bash
cd credit_risk_control_system
python3 -c "
import pandas as pd
df = pd.read_parquet('data/warehouse/ods/dt=2026-07-01/ods_application.parquet')
print('列名:', list(df.columns))
print('行数:', len(df))
print()
# 看一条原始数据
row = df.iloc[0]
print('user_name:', row['user_name'], '← 明文！必须在 DWD 脱敏')
print('id_card:', row['id_card'], '← 明文！')
print('apply_amount:', row['apply_amount'], '← 可能有负数')
print('product_type:', row['product_type'], '← 可能是 None')
"
```

你应该看到：明文姓名、明文身份证、可能有 `None` 和异常值——这就是 ODS 层"不处理"的体现。

### 2.4 练习：手写电商 ODS 定义（30min）

在空白 `.py` 文件中完成以下代码：

```python
from dataclasses import dataclass

@dataclass
class ODSTable:
    name: str
    source_system: str
    ingest_method: str
    partition_key: str = "dt"
    description: str = ""

# ★ 参考答案
电商_ODS_TABLES = {
    "ods_order": ODSTable(
        name="ods_order",
        source_system="mysql_order_center",
        ingest_method="binlog",
        description="用户订单表（来自 MySQL 订单中心 Binlog）",
    ),
    "ods_user_track": ODSTable(
        name="ods_user_track",
        source_system="sdk_analytics",
        ingest_method="sdk",
        description="用户行为轨迹（埋点 SDK 实时上报）",
    ),
    "ods_inventory": ODSTable(
        name="ods_inventory",
        source_system="wms_system",
        ingest_method="api_log",
        description="库存表（WMS 仓库系统 API 同步）",
    ),
}
```

---

## 三、DWD 层：清洗不聚合（40min）

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

## 四、DWS 层：聚合建模（30min）

### 4.1 粒度变化

这是最关键的概念。打开 `src/data/warehouse/dws_layer.py` 第 44 行：

```
输入: DWD 明细（3 张表，不同粒度）
  dwd_application: 500 行（一行一个申请）
  dwd_behavior:    5000 行（一行一个行为事件）
  dwd_repayment:   500 行（一行一个还款记录）

输出: DWS 宽表（1 张表，统一粒度）
  user_risk_feature_wide: ~450 行（一行一个用户一天）
```

```python
# 第 84-88 行 — 三路聚合再合并
wide_table = (
    profile_features                   # 申请表 → 6 个特征
    .merge(behavior_features,          # 行为表 → 6 个特征
           on='user_id', how='left')   # ★ left join: 保留新用户
    .merge(repayment_features,         # 还款表 → 5 个特征
           on='user_id', how='left')
)
wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)
```

**为什么先聚合再 join，而不是先 join 再聚合？**

```
先 join 再聚合（错误）:
  申请表 5行 × 行为表 100行 = 500行 → 聚合时 COUNT 被放大到 500

先聚合再 join（正确）:
  申请表 → 聚合 → 1行  \
  行为表 → 聚合 → 1行  → join → 1行（无膨胀）
  还款表 → 聚合 → 1行  /
```

### 4.2 阅读 DDL

打开 `config/ddl/03_dws_wide_table.sql`，观察 COMMENT 怎么写：

```sql
night_ops_ratio_30d  DOUBLE COMMENT '★ 近30天深夜操作占比(22-05时)。风控强特征。>60%→高度可疑',
on_time_rate         DOUBLE COMMENT '★ 按时还款率=1-逾期次/总次。新用户=1.0。3笔2逾期→0.33→高风险',
```

COMMENT 里写了三个信息：**含义 + 业务判断 + 风险方向**。这不是数据工程师一个人的事——是和业务方、AI 工程师一起确认的。

---

## 五、ADS 层：数据产品（30min）

打开 `config/ddl/04_ads_tables.sql`，看三种数据产品的设计：

```
ads_training_samples    → 消费者: XGBoost 模型训练   格式: Parquet
ads_model_monitor_daily → 消费者: Grafana 监控大盘   格式: CSV
ads_portfolio_analysis  → 消费者: 风控报表/BI        格式: JSON
```

**核心原则：每个 ADS 表对应一个明确的消费者。不是"数据都有了你们自己查"，而是"你们要什么我给你们什么"。**

---

## 六、DDL 写作规范（30min）

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

## 七、今日检查清单

- [ ] 能画出四层架构图，标注每层的粒度和职责
- [ ] 能解释 ODS 为什么不做清洗（三个理由）
- [ ] 能解释"先聚合再 join vs 先 join 再聚合"的区别
- [ ] 能写出带 COMMENT 和 TBLPROPERTIES 的生产级 DDL
- [ ] 完成了电商 ODS 表定义代码
- [ ] 完成了 dwd_order 的 DDL 编写

### 延伸思考

1. 如果公司只有 3 张源表，还需要四层吗？能不能合并 ODS+DWD 为一层？
2. DWS 层的 left join 在什么情况下会导致数据膨胀？（提示：一对多关系）
