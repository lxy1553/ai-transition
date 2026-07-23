---
id: L118
source: learning
category: LLM与AI工程
title: 请说说LoRA 参数选择指南
generated: 2026-07-23T15:41:19.875185
---

# 请说说LoRA 参数选择指南

> 来源: 学习复习计划 | 分类: LLM与AI工程

```
r（秩）:
  r=4  → 最快，效果最差 → 简单的格式转换
  r=8  → 推荐，效果不错 → 通用场景
  r=16 → 较慢，效果更好 → 需要学习复杂模式
  r=64 → 接近全量微调 → 数据量大（>1000 条）时用

lora_alpha（缩放）:
  建议: lora_alpha = 2 × r
  r=8 → alpha=16
  r=16 → alpha=32

target_modules（微调哪些层）:
  推荐: ["q_proj", "v_proj"]（最小的改动）
  进阶: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
  → 模块越多，效果越好，显存需求越大

```

---