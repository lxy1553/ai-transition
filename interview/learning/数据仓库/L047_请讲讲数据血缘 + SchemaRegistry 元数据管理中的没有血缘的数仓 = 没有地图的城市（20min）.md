---
id: L047
source: learning
category: 数据仓库
title: 请讲讲数据血缘 + SchemaRegistry 元数据管理中的没有血缘的数仓 = 没有地图的城市（20min）
generated: 2026-07-23T15:41:19.864339
---

# 请讲讲数据血缘 + SchemaRegistry 元数据管理中的没有血缘的数仓 = 没有地图的城市（20min）

> 来源: 学习复习计划 | 分类: 数据仓库

```
场景：DWD 层的 apply_amount 列类型从 INT 改成 DOUBLE
  问题：哪些下游表会受影响？

有血缘 → 秒级溯源:
  apply_amount (dwd_application)
    → apply_amount_avg (dws.user_risk_feature_wide)
      → 训练样本表 ads_training_samples
        → XGBoost 模型的特征列
  结论：模型需要重训，因为特征类型变了

没有血缘 → 灾难:
  让各团队自己去排查 → 3 天后才发现模型评分异常

```

---