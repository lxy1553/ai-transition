---
id: L062
source: learning
category: 信贷风控建模
title: 请讲讲XGBoost 训练 + 模型评估完整指南中的XGBoost 核心概念（30min）
generated: 2026-07-23T15:41:19.866521
---

# 请讲讲XGBoost 训练 + 模型评估完整指南中的XGBoost 核心概念（30min）

> 来源: 学习复习计划 | 分类: 信贷风控建模

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