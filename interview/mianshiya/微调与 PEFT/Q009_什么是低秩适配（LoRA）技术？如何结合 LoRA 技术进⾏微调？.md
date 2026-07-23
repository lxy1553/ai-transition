---
id: Q009
source: mianshiya
category: 微调与 PEFT
title: 什么是低秩适配（LoRA）技术？如何结合 LoRA 技术进⾏微调？
generated: 2026-07-23T15:41:19.796892
---

# 什么是低秩适配（LoRA）技术？如何结合 LoRA 技术进⾏微调？

> 来源: 面试鸭题库 | 分类: 微调与 PEFT

低秩适配（LoRA）的核⼼思路是，⼤模型微调时参数量太⼤，训练慢、显存吃紧，⼲脆不直接改原始权重，⽽是⽤低
秩矩阵去近似增量。
模型原本的权重矩阵 $W$ 是个⼤胖⼦，⽐如 768×768。LoRA 不动它，转⽽引⼊两个⼩矩阵 $A$ 和 $B$，维度分别是
$768×r$ 和 $r×768$，其中 $r$ 很⼩，⼀般取 8 到 64。训练时只更新这两个⼩矩阵，前向传播时等效注⼊ $\Delta W
= A \times B$。
这样显存和计算量就从和原矩阵成正⽐，变成和 $r$ 相关。⽐如 r=8，参数量直接降到原来的 1/96，训练速度翻倍都
不⽌。
结合 LoRA 做微调，流程也简单：
1）冻结原始模型所有权重
2）在指定层（⽐如注意⼒中的 Q、V 投影）插⼊ LoRA 模块
3）只训练新增的⼩矩阵，其余参数不动
4）推理时把 $A \times B$ 加到原权重上，或者直接合并进原权重
主流框架都有⽀持。Hugging Face 的 peft  库⼏⾏代码就能上：
from peft import LoraConfig, get_peft_model
lora_config = LoraConfig(
r=8,
lora_alpha=16,
target_modules=["q_proj", "v_proj"],
lora_dropout=0.1,
bias="none",
task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)
适合资源有限、多任务切换的场景。像微调⼀个 7B 模型，⽤ LoRA 能在单卡 24G 显存下搞定，否则根本搞不定。