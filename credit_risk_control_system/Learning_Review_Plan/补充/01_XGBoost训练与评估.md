# XGBoost 训练 + 模型评估完整指南

> 目标：理解 XGBoost 核心原理，能手写完整训练流程和评估指标体系。

---

## 一、XGBoost 核心概念（30min）

### 1.1 为什么用 XGBoost 而不是深度学习？

```
数据量 < 10 万条 → XGBoost 效果 > 深度学习
数据量 > 100 万条 → 深度学习才有优势
信贷风控（几万条样本）→ XGBoost 是行业标准

核心优势:
1. 自带正则化 — 不容易过拟合
2. 处理缺失值 — 自动学习缺失值方向
3. 特征重要性 — 可解释性强
4. 训练速度快 — 不需要 GPU
```

### 1.2 XGBoost 的核心参数

```python
# 项目中使用的参数 (src/models/trainer.py 第149-161行)

params = {
    'objective': 'binary:logistic',     # 二分类任务
    'eval_metric': 'auc',               # 评估指标
    'max_depth': 5,                     # 树深度 — 越大越容易过拟合
    'learning_rate': 0.05,              # 学习率 — 越小越需要更多树
    'n_estimators': 500,                # 树的数量
    'subsample': 0.8,                   # 行采样 — 防过拟合
    'colsample_bytree': 0.8,            # 列采样 — 防过拟合
    'min_child_weight': 10,             # 叶子节点最小权重 — 防过拟合
    'reg_alpha': 0.1,                   # L1 正则化
    'reg_lambda': 1.0,                  # L2 正则化
    'early_stopping_rounds': 50,        # 早停
    'scale_pos_weight': n_neg / n_pos,  # 样本不平衡处理
}
```

**参数选择逻辑**：

```
max_depth=5 而不是 10:
  树太深 → 模型记住噪声 → 过拟合
  树太浅 → 模型学不到模式 → 欠拟合
  5 是信贷风控的经验值

scale_pos_weight = 负样本数 / 正样本数:
  坏样本 10%，好样本 90% → weight = 9
  让模型更关注"少数派"（坏人）
  不设这个参数 → 模型会倾向于预测所有人都是好人（因为 90% 是对的）
```

---

## 二、完整训练流程（1h）

### 2.1 项目中的训练代码

打开项目 `src/models/trainer.py` 第 126-224 行：

```python
class ModelTrainer:
    def train_xgboost(self, X_train, y_train, X_test, y_test, feature_names):

        # Step 1: 样本不平衡处理
        n_pos = (y_train == 1).sum()
        n_neg = (y_train == 0).sum()
        params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1

        # Step 2: 训练
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],  # 用测试集做早停
                  verbose=False)

        # Step 3: 预测
        y_train_pred = model.predict_proba(X_train)[:, 1]
        y_test_pred = model.predict_proba(X_test)[:, 1]

        # Step 4: 评估
        report = self.evaluator.evaluate(
            y_train, y_train_pred, y_test, y_test_pred
        )

        return ModelWrapper(...), report
```

**早停（Early Stopping）的工作原理**：

```
训练第 1 轮: train AUC=0.65, test AUC=0.62
训练第 10 轮: train AUC=0.80, test AUC=0.74
训练第 50 轮: train AUC=0.95, test AUC=0.72  ← test AUC 开始下降
训练第 60 轮: train AUC=0.96, test AUC=0.71  ← 连续 10 轮没提升

early_stopping_rounds=10:
  发现 test AUC 连续 10 轮不增长 → 停止训练
  回滚到第 50 轮的模型（test AUC 最高那次）
```

### 2.2 动手练习：手写完整训练流程

```python
import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split

# 生成模拟数据
np.random.seed(42)
n_samples = 5000
X = np.random.randn(n_samples, 10)
y = (X[:, 0] + X[:, 1] * 2 + np.random.randn(n_samples) * 0.5 > 0.5).astype(int)

# 切分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# ★ 参考答案
params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'max_depth': 5,
    'learning_rate': 0.05,
    'n_estimators': 500,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
}
n_pos = (y_train == 1).sum()
n_neg = (y_train == 0).sum()
params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1

model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_train_pred = model.predict_proba(X_train)[:, 1]
y_test_pred = model.predict_proba(X_test)[:, 1]

from sklearn.metrics import roc_auc_score
print(f"AUC train: {roc_auc_score(y_train, y_train_pred):.4f}")
print(f"AUC test:  {roc_auc_score(y_test, y_test_pred):.4f}")
```

---

## 三、模型评估指标体系（1h）

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

## 四、动手练习：完整训练+评估（1.5h）

```python
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import xgboost as xgb

# 生成模拟数据（5 个特征，其中 2 个有预测力）
np.random.seed(42)
n = 10000
X = pd.DataFrame({
    'feature_0': np.random.randn(n),
    'feature_1': np.random.randn(n),
    'feature_2': np.random.choice(['A', 'B', 'C'], n),
    'feature_3': np.random.randn(n),
    'feature_4': np.random.randn(n),
})
# label = feature_0 + feature_1*2 + 噪声
y = (X['feature_0'] + X['feature_1'] * 2 + np.random.randn(n) * 0.8 > 0).astype(int)

# 处理类别特征
X = pd.get_dummies(X, columns=['feature_2'])

# TODO: 完成以下步骤
# 1. 按 70/30 切分（注意保持标签分布一致 — stratify=y）
# 2. 训练 XGBoost（参考项目参数，含 scale_pos_weight 和 early_stopping）
# 3. 计算 train 和 test 的 AUC
# 4. 计算 KS
# 5. 计算 PSI
# 6. 绘制 Lift 表
# 7. 输出: 模型是否满足上线标准？

# ★ 参考答案
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

n_pos = (y_train == 1).sum()
params['scale_pos_weight'] = (y_train == 0).sum() / n_pos if n_pos > 0 else 1
model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_train_pred = model.predict_proba(X_train)[:, 1]
y_test_pred = model.predict_proba(X_test)[:, 1]

from sklearn.metrics import roc_auc_score
auc_train = roc_auc_score(y_train, y_train_pred)
auc_test = roc_auc_score(y_test, y_test_pred)

order = np.argsort(y_test_pred)[::-1]
y_sorted = y_test[order]
n_pos_test = (y_test == 1).sum()
cum_pos = np.cumsum(y_sorted == 1) / n_pos_test
cum_neg = np.cumsum(y_sorted == 0) / (y_test == 0).sum()
ks = float(np.max(np.abs(cum_pos - cum_neg)))

boundaries = np.percentile(y_train_pred, np.linspace(0, 100, 11))
ep = np.histogram(y_train_pred, bins=boundaries)[0] / len(y_train_pred)
ap = np.histogram(y_test_pred, bins=boundaries)[0] / len(y_test_pred)
ep = np.clip(ep, 1e-6, 1); ap = np.clip(ap, 1e-6, 1)
psi = float(np.sum((ap - ep) * np.log(ap / ep)))

print(f"AUC train: {auc_train:.4f}, AUC test: {auc_test:.4f}")
print(f"KS: {ks:.4f} {'✅' if ks >= 0.25 else '❌'} (需≥0.25)")
print(f"PSI: {psi:.4f} {'✅' if psi < 0.25 else '❌'} (需<0.25)")
print(f"Overfit gap: {auc_train - auc_test:.4f} {'✅' if auc_train - auc_test < 0.05 else '❌'} (需<0.05)")
print(f"上线: {'✅ 通过' if ks >= 0.25 and psi < 0.25 else '❌ 不达标'}")
```

---

## 五、常见问题

### Q1: 为什么 train AUC=0.99, test AUC=0.47？

```
典型过拟合:
- 数据量太少 → 模型记住了噪声
- 树太深（max_depth=10）→ 模型过度拟合
- 缺少正则化（reg_alpha/reg_lambda=0）
- 没有早停

解决方案:
- 增加数据量
- 降低 max_depth（3-6）
- 增加正则化参数
- 开启 early_stopping
- 增加 subsample/colsample
```

### Q2: scale_pos_weight 怎么算？

```
正样本（坏人）: 100 条
负样本（好人）: 900 条
scale_pos_weight = 900 / 100 = 9.0

含义: 预测错一个坏人的惩罚是预测错一个好人的 9 倍
      模型会更努力地去识别坏人

注意: 如果设太大（比如 50），模型会把所有人都预测成坏人
      如果设太小（比如 1），模型会忽视坏人
```

### Q3: 特征工程重要还是模型调参重要？

```
结论: 特征工程 >>> 模型调参

有一个经典经验:
  好的特征 + 默认参数 → 效果很好
  差的特征 + 最优调参 → 效果很差

所以项目中的 DWS 宽表设计（17 个特征、WOE/IV 筛选）
比 XGBoost 的超参调优重要得多。
```
