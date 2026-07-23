---
id: L065
source: learning
category: 信贷风控建模
title: 请讲讲XGBoost 训练 + 模型评估完整指南中的动手练习：完整训练+评估（1.5h）
generated: 2026-07-23T15:41:19.866909
---

# 请讲讲XGBoost 训练 + 模型评估完整指南中的动手练习：完整训练+评估（1.5h）

> 来源: 学习复习计划 | 分类: 信贷风控建模

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