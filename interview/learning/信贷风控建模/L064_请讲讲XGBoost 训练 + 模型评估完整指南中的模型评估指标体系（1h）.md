---
id: L064
source: learning
category: 信贷风控建模
title: 请讲讲XGBoost 训练 + 模型评估完整指南中的模型评估指标体系（1h）
generated: 2026-07-23T15:41:19.866781
---

# 请讲讲XGBoost 训练 + 模型评估完整指南中的模型评估指标体系（1h）

> 来源: 学习复习计划 | 分类: 信贷风控建模

### 3.1 AUC — 排序能力


```python
def calculate_auc(y_true, y_pred):
    """
    AUC = 随机抽一个正样本一个负样本，模型把正样本排前面的概率。

    AUC = 0.5 → 和扔硬币一样
    AUC = 0.7 → 70% 的概率能把好坏分开
    AUC = 1.0 → 完美

    信贷标准: AUC >= 0.65 才能上线
    """
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(y_true, y_pred)

```

### 3.2 KS — 区分能力（必须能手写）


```python
def calculate_ks(y_true, y_pred):
    """
    KS = max(|好样本累积比例 - 坏样本累积比例|)

    为什么 KS 和 AUC 都要看？
    - AUC 衡量"整体"排序能力
    - KS 衡量"在最佳切分点"的区分能力
    - 高 AUC + 低 KS → 排序对但分不开（阈值附近模糊）

    信贷标准: KS >= 0.25
    """
    order = np.argsort(y_pred)[::-1]        # 按预测概率降序排
    y_sorted = y_true[order]

    n_pos = (y_true == 1).sum()
    n_neg = (y_true == 0).sum()

    cum_pos = np.cumsum(y_sorted == 1) / n_pos  # 坏样本累积
    cum_neg = np.cumsum(y_sorted == 0) / n_neg  # 好样本累积

    return float(np.max(np.abs(cum_pos - cum_neg)))

```

### 3.3 PSI — 分布稳定性


```python
def calculate_psi(expected, actual, bins=10):
    """
    PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)

    PSI < 0.1 → 稳定
    PSI 0.1-0.25 → 轻微漂移，关注
    PSI > 0.25 → 严重漂移，触发重训

    为什么用训练集的分位做分箱边界？
    → 保持分箱边界固定，才能比较"线上 vs 训练"的分布差异
    """
    boundaries = np.percentile(expected, np.linspace(0, 100, bins + 1))
    ep = np.histogram(expected, bins=boundaries)[0] / len(expected)
    ap = np.histogram(actual, bins=boundaries)[0] / len(actual)

    ep = np.clip(ep, 1e-6, 1)
    ap = np.clip(ap, 1e-6, 1)
    return float(np.sum((ap - ep) * np.log(ap / ep)))

```

### 3.4 Lift 分析


```python
def calculate_lift(y_true, y_pred, bins=10):
    """
    Lift = 该分箱的坏账率 / 整体平均坏账率

    理想模型: 按预测概率降序分 10 箱
      Bin 0（最高危）: lift > 2.0  → 坏账率是平均的 2 倍
      Bin 9（最低危）: lift < 0.5  → 坏账率不到平均的一半

    如果 lift 曲线单调递减 → 模型排序正确
    如果 lift 曲线没有单调性 → 模型有问题
    """
    df = pd.DataFrame({'prob': y_pred, 'true': y_true})
    df = df.sort_values('prob', ascending=False)
    df['bin'] = pd.qcut(df['prob'], q=bins, labels=False)

    avg_bad_rate = y_true.mean()
    lift_table = df.groupby('bin').agg(
        bad_rate=('true', 'mean'),
        count=('true', 'count'),
    ).reset_index()
    lift_table['lift'] = lift_table['bad_rate'] / avg_bad_rate

    return lift_table

```

---