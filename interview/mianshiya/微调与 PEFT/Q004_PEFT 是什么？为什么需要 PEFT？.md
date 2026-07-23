---
id: Q004
source: mianshiya
category: 微调与 PEFT
title: PEFT 是什么？为什么需要 PEFT？
generated: 2026-07-23T15:41:19.796250
---

# PEFT 是什么？为什么需要 PEFT？

> 来源: 面试鸭题库 | 分类: 微调与 PEFT

PEFT 全称是 Parameter-Eﬃcient Fine-Tuning，直⽩点说就是“只动⼀⼩部分参数来微调⼤模型”。现在⼤模型动不
动就上百亿、上千亿参数，⽐如 Llama、ChatGLM 这种，直接全量微调成本太⾼了，显存、算⼒、时间都吃不消。
其实我们发现，微调的时候没必要更新所有参数。PEFT 的思路是冻结原模型绝⼤部分权重，只训练少量额外引⼊或选
中的参数，就能达到接近全量微调的效果。这样显存能省下 70% 以上，训练速度也快很多，普通⼏张卡甚⾄单卡也能
搞。
常⻅的 PEFT ⽅法⾥，LoRA 是最⽕的。它在原始层旁边加个低秩矩阵做增量，训练时只更新这个⼩矩阵。⽐如⼀个
7B 模型，⽤ LoRA 可能只改 0.1% 的参数，效果却不差。HuggingFace 的 peft  库已经⽀持得⾮常好，配合
transformers 能轻松上⼿。
代码⻓这样：
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
除了 LoRA，还有 Adapter、Preﬁx-tuning 等⽅法，但 LoRA 因为⽆推理延迟、实现简单，成了主流选择。特别是资源
有限⼜想定制⼤模型的场景，⽐如企业私有模型微调，PEFT ⼏乎是标配⽅案。
参数⾼效微调（PEFT）的核⼼思路是什么？列举 3 种典型⽅法
参数⾼效微调的核⼼思路是只微调模型中极⼩⼀部分参数，冻结绝⼤部分原始参数，从⽽在保持下游任务性能的同
时，⼤幅降低计算和存储开销。
⼤模型动辄上百亿参数，全量微调需要⼏⼗甚⾄上百 GB 显存，普通团队根本搞不定。PEFT 的做法是“以⼩博⼤”，
通过引⼊少量可训练参数来适配新任务，⽐如只调 0.1%~1% 的参数就能达到接近全量微调的效果。
1） LoRA（Low-Rank Adaptation）
在原始权重旁注⼊低秩矩阵，训练时只更新这些⼩矩阵。推理时可以合并到原权重中，完全不增加推理延迟。
HuggingFace Transformers 已深度集成，现已成为主流选择。
2） Adapter
在 Transformer 模块间插⼊⼩型前馈⽹络（通常两层 MLP），原模型冻结，只训练插⼊的模块。虽然效果好，但会增
加推理延迟，因为每次前向都要⾛额外⽹络。
3） Prompt Tuning / Preﬁx Tuning
通过可学习的“软提⽰”向量引导模型输出，本质是把任务建模成“填提⽰”的过程。Preﬁx Tuning 把这些向量拼接
在每⼀层输⼊前，Prompt Tuning 只加在第⼀层。节省参数，但对初始化敏感，⼩模型上容易不稳定。