---
id: L005
source: learning
category: AI应用开发
title: 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的今日要点
generated: 2026-07-23T15:41:19.858523
---

# 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的今日要点

> 来源: 学习复习计划 | 分类: AI应用开发

```
核心公式:
  ✅ 正确的训练样本: X(T) → y(T+N)
  ❌ 时间泄漏:       X(T+N) → y(T+N)

三个铁律:
  1. merge on key, never concat by index
  2. 显式过滤 feature_time < label_time（双重保险）
  3. AUC(test) 异常高（>0.95）→ 先怀疑时间泄漏，再高兴

```

---