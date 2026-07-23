---
id: L007
source: learning
category: AI应用开发
title: 请说说原始事件 vs 特征向量（20min）
generated: 2026-07-23T15:41:19.858778
---

# 请说说原始事件 vs 特征向量（20min）

> 来源: 学习复习计划 | 分类: AI应用开发

### 1.1 模型看不懂事件，只看懂数字


```
业务系统产生的是"事件流":
  user_000042 | page_view  | /mine  | 2026-07-01 23:45:39
  user_000042 | click      |        | 2026-07-01 18:14:58
  user_000042 | submit     | /mine  | 2026-07-01 23:45:39
  user_000042 | page_view  | /repay | 2026-07-01 18:23:45
  user_000042 | page_view  | /mine  | 2026-07-01 06:34:07
  ...（共 11 条）

模型需要的是"特征向量"（一行数字）:
  user_000042 | apply_cnt_7d=1 | night_ops_ratio=0.27 | page_view_7d=5 | error_7d=2 | ...

特征工程 = 把上面 11 行变成下面 1 行

```

---