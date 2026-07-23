---
id: L034
source: learning
category: 数据仓库
title: 请讲讲分层数据仓库架构设计与 DDL中的DWS 层：聚合建模（30min）
generated: 2026-07-23T15:41:19.862499
---

# 请讲讲分层数据仓库架构设计与 DDL中的DWS 层：聚合建模（30min）

> 来源: 学习复习计划 | 分类: 数据仓库

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