---
id: L002
source: learning
category: AI应用开发
title: 请举例说明从代码看 PIT 正确性（1h）如何实现？
generated: 2026-07-23T15:41:19.858132
---

# 请举例说明从代码看 PIT 正确性（1h）如何实现？

> 来源: 学习复习计划 | 分类: AI应用开发

### 2.1 阅读项目核心代码

打开 `src/data/warehouse/ads_layer.py` 第 41-81 行：


```python
def build_training_samples(
    self,
    dws_wide_table: pd.DataFrame,   # 用户在 T 时刻的特征快照
    label_df: pd.DataFrame,          # 用户在 T+30 天的逾期标签
    performance_window_days: int = 30,
) -> pd.DataFrame:
    """
    ★ 这段代码看似简单，但承载了整个建模流程最重要的假设：
    ★ dt_特征 < dt_标签

    如果这个假设被破坏 → 模型学到的都是假规律 → 上线即报废
    """
    samples = dws_wide_table.merge(
        label_df,
        on='user_id',        # 同一个用户
        how='inner',         # 必须两个时间点都有数据
    )
    return samples

```

**为什么用 `merge` 而不是 `pd.concat`？**


```python
# 对比实验：三种拼接方式

import pandas as pd
import numpy as np

# 模拟数据
features = pd.DataFrame({
    'user_id': ['u1', 'u2', 'u3'],
    'feature_a': [1.0, 2.0, 3.0],
    'feature_time': ['2026-07-01', '2026-07-01', '2026-07-01'],
})
labels = pd.DataFrame({
    'user_id': ['u3', 'u1', 'u2'],  # ← 注意！顺序和 features 不一样！
    'label': [0, 1, 0],
    'label_time': ['2026-08-01', '2026-08-01', '2026-08-01'],
})

# 方式 A: concat — 按行号对齐（不关心 user_id）
samples_A = pd.concat([features, labels], axis=1)
print("concat 结果:")
print(samples_A)
# user_id_x  u1  1.0  → label=0   ✅ 碰巧对 (同一行对齐了)
# user_id_x  u2  2.0  → label=1   ❌ 错！u2 的特征配了 u1 的标签
# user_id_x  u3  3.0  → label=0   ❌ 错！u3 的特征配了 u2 的标签

# 方式 B: merge — 按 user_id 关联（不关心行号）
samples_B = features.merge(labels, on='user_id', how='inner')
print("merge 结果:")
print(samples_B)
# u1  1.0  → label=1   ✅ 正确（merge 按 user_id 配对了）
# u2  2.0  → label=0   ✅ 正确
# u3  3.0  → label=0   ✅ 正确

```

**核心教训**：`concat` 假设两个 DataFrame 的行顺序一致——这个假设在生产中几乎永远不成立。`merge` 用 key 关联——key 是事实，行号是巧合。

### 2.2 谁保证了"特征时间 < 标签时间"？

两层保证：


```python
# 第一层：标签生成时（上游保证）
# scripts/generate_data_pipeline.py 第 122 行
label_df = pd.DataFrame({
    'user_id': users,
    'label': np.random.choice([0, 1], len(users)),
    'label_date': dt,  # ← 生产中是 dt + 30 天后的逾期观察
})

# 第二层：拼接时（本层保证）
# merge 只负责按 user_id 关联，不强写时间约束。
# 但如果在 SQL 中执行（生产环境），可以加显式约束：
# SELECT w.*, l.label
# FROM dws.user_risk_feature_wide w
# JOIN labels l ON w.user_id = l.user_id
#   AND w.dt = DATE_SUB(l.label_date, 30)  ← 时间约束写进 WHERE

```

---