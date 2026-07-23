---
id: Q005
source: mianshiya
category: 微调与 PEFT
title: PEFT 和全量微调的区别？
generated: 2026-07-23T15:41:19.796380
---

# PEFT 和全量微调的区别？

> 来源: 面试鸭题库 | 分类: 微调与 PEFT

PEFT 本质上是解决⼤模型微调成本太⾼的问题。全量微调要更新整个模型所有参数，显存和计算资源消耗巨⼤，⽐如
⼀个 13B 的模型，光梯度存储就得上百 GB 显存。
⽽ PEFT 的思路是冻结原模型⼤部分参数，只训练⼀⼩部分新增或改造的模块。这样⼀来，显存占⽤能降到原来的
1/10 甚⾄更低，普通单卡也能跑。
1）全量微调：每个参数都参与更新，效果理论上最好，但训练慢、成本⾼，需要完整的优化器状态和梯度保存。适合
有充⾜算⼒且对性能极致要求的场景，⽐如公司级训练集群搞通⽤能⼒升级。
2）PEFT ⽅法：以 LoRA 为例，它在原始权重旁并⾏注⼊低秩矩阵，训练时只更新这些⼩矩阵。假设原始权重是 $W
\in \mathbb{R}^{768\times 768}$，LoRA 拆成两个⼩矩阵 $A \in \mathbb{R}^{768\times r}$ 和 $B \in
\mathbb{R}^{r\times 768}$，其中 $r$ 通常设为 8 或 16。这样可训练参数数量从⼏⼗亿骤降到百万级。
// 伪代码⽰意  LoRA 注⼊
Matrix W = loadOriginalWeight(); // 冻结
Matrix A = randomInit(768, 8);   // 可训练
Matrix B = randomInit(8, 768);   // 可训练
Matrix loraOutput = input * (W + A * B); // W 不更新
常⻅变体还有 Adapter Tuning、Preﬁx Tuning 等，但 LoRA 因其不改变推理结构、兼容性好成为主流。HuggingFace
的 peft  库已经⽀持多种模式，配合 transformers  ⼏⾏代码就能上。
效果上，多数任务中 LoRA 能达到全量微调 95% 以上的性能，但对强推理或复杂指令遵循任务可能略有差距。关键是
省了太多资源，让 7B/13B 模型在消费级 GPU 上也能快速迭代。