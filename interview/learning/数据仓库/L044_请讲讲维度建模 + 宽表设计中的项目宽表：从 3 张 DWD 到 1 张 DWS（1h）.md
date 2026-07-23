---
id: L044
source: learning
category: 数据仓库
title: 请讲讲维度建模 + 宽表设计中的项目宽表：从 3 张 DWD 到 1 张 DWS（1h）
generated: 2026-07-23T15:41:19.863833
---

# 请讲讲维度建模 + 宽表设计中的项目宽表：从 3 张 DWD 到 1 张 DWS（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

### 2.1 三路聚合 → left join → fillna

打开 `src/data/warehouse/dws_layer.py` 第 44-99 行 `build_wide_table()`：


```python
def build_wide_table(self, dwd_application, dwd_behavior, dwd_repayment, dt):
    # Step 1: 三路分别聚合（各自压缩到用户粒度）
    profile_features = self._build_profile_features(dwd_application)    # → 6列
    behavior_features = self._build_behavior_features(dwd_behavior, dt)  # → 6列
    repayment_features = self._build_repayment_features(dwd_repayment)   # → 5列

    # Step 2: 三表 left join（保留新用户）
    wide_table = (
        profile_features
        .merge(behavior_features, on='user_id', how='left')    # ★ left
        .merge(repayment_features, on='user_id', how='left')   # ★ left
    )

    # Step 3: 缺失值填充
    wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

    return wide_table  # 450行 × 19列

```

### 2.2 为什么 left join 而不是 inner join？


```
场景: 新用户 user_X，刚注册，只有申请记录
  dwd_application: user_X 有 1 行
  dwd_behavior:    user_X 无（从未打开过 App）
  dwd_repayment:   user_X 无（从未借过钱）

inner join:
  user_X → 被丢弃 ❌ → 训练集里没有新用户 → 模型不认识新用户

left join:
  user_X → 保留 ✓ → 行为特征=0, 还款特征=0 → 模型能学到"全0=新用户"

```

### 2.3 聚合函数选择：为什么 income 取 MAX？

打开 `_build_profile_features()` 第 103-131 行：


```python
agg = app_df.groupby('user_id').agg(
    monthly_income=('monthly_income', 'max'),  # ← 为什么是 max？
)

# 场景: 用户填了 3 次申请，收入分别为 8000, 8000, 5000
# max = 8000 → "取用户最诚实的申报"（据说高的是真的）
# mean = 7000 → "被 5000 拉低了"
# min = 5000 → "用户可能想看起来穷一点"
# 选择 max = 偏保守的乐观估计（相信用户最高的那次申报）

```

---