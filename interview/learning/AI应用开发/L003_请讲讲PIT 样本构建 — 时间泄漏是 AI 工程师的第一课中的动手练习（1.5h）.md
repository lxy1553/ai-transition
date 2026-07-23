---
id: L003
source: learning
category: AI应用开发
title: 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的动手练习（1.5h）
generated: 2026-07-23T15:41:19.858277
---

# 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的动手练习（1.5h）

> 来源: 学习复习计划 | 分类: AI应用开发

### 练习 1：写时间泄漏检测器（30min）


```python
def detect_time_leakage(
    samples: pd.DataFrame,
    feature_time_col: str,
    label_time_col: str,
) -> dict:
    """
    检测训练样本中是否存在时间泄漏。
    """
    # ★ 参考答案
    feature_dt = pd.to_datetime(samples[feature_time_col])
    label_dt = pd.to_datetime(samples[label_time_col])

    leaked = feature_dt >= label_dt
    leaked_indices = samples.index[leaked].tolist()
    n_leaked = len(leaked_indices)
    n_total = len(samples)

    return {
        "total_samples": n_total,
        "leaked_samples": n_leaked,
        "leak_rate": round(n_leaked / n_total, 4) if n_total > 0 else 0.0,
        "leaked_indices": leaked_indices,
        "is_critical": (n_leaked / n_total > 0.01) if n_total > 0 else False,
    }


# 测试用例
test_samples = pd.DataFrame({
    'user_id': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'feature_dt': [
        '2026-07-01', '2026-07-01',
        '2026-07-01', '2026-07-01', '2026-08-01'
    ],
    'label_dt': [
        '2026-08-01', '2026-08-01',
        '2026-08-01', '2026-08-01', '2026-07-15'
    ],
})
result = detect_time_leakage(test_samples, 'feature_dt', 'label_dt')
print(result)
# 预期: total=5, leaked=1 (u5: 2026-08-01 >= 2026-07-15), is_critical=False (20% > 1%)

```

### 练习 2：为电商推荐写 PIT 样本构建（45min）


```python
def build_电商推荐_训练样本(
    user_features: pd.DataFrame,   # 曝光时刻的特征
    click_labels: pd.DataFrame,    # T+7 的购买标签
) -> pd.DataFrame:
    """
    电商推荐场景的 PIT 样本构建。
    """
    # ★ 参考答案
    # 1. merge 按 user_id + item_id 关联（比信贷多一维）
    samples = user_features.merge(
        click_labels,
        on=['user_id', 'item_id'],
        how='inner',           # 必须两个时间点都有数据
    )

    # 2. 显式过滤时间泄漏
    samples['show_time'] = pd.to_datetime(samples['show_time'])
    samples['click_time'] = pd.to_datetime(samples['click_time'])
    samples = samples[samples['show_time'] < samples['click_time']]

    return samples


# 测试数据
user_features = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u2'],
    'item_id': ['A', 'B', 'A'],
    'show_time': ['2026-07-01', '2026-07-01', '2026-07-01'],
    'user_age': [25, 25, 30],
})
click_labels = pd.DataFrame({
    'user_id': ['u1', 'u2'],
    'item_id': ['A', 'A'],
    'label': [1, 0],
    'click_time': ['2026-07-05', '2026-07-10'],
})

samples = build_电商推荐_训练样本(user_features, click_labels)
print(samples[['user_id', 'item_id', 'label', 'show_time', 'click_time']])
# 预期: u1-A 保留(label=1, 07-01 < 07-05), u2-A 保留(label=0, 07-01 < 07-10)
# u1-B 没有标签行 → inner join 自动丢弃
print(f"\n样本数: {len(samples)}")  # 预期: 2

```

### 练习 3：时间泄漏会怎样？（15min）

运行项目中的模型训练，观察时间泄漏的效果：


```bash
cd credit_risk_control_system

# 先看"正常"的模型（数据是随机生成的，所以效果差——这是预期的）
python3 scripts/train_model.py --from-warehouse --n-samples 2000
# 观察: AUC(train) ≈ 0.99, AUC(test) ≈ 0.47 → 严重过拟合随机噪声

# 思考: 如果 AUC(test) = 0.95（非常高），反而是坏事！
# 说明可能存在时间泄漏，模型看到了不该看的信息。

```

---