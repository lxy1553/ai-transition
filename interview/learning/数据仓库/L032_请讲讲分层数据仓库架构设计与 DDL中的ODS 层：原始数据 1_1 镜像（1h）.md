---
id: L032
source: learning
category: 数据仓库
title: 请讲讲分层数据仓库架构设计与 DDL中的ODS 层：原始数据 1:1 镜像（1h）
generated: 2026-07-23T15:41:19.862273
---

# 请讲讲分层数据仓库架构设计与 DDL中的ODS 层：原始数据 1:1 镜像（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

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