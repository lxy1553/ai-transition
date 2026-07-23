---
id: L117
source: learning
category: LLM与AI工程
title: 请讲讲PyTorch 微调：从原理到 LoRA中的LoRA：高效微调（1h）
generated: 2026-07-23T15:41:19.874939
---

# 请讲讲PyTorch 微调：从原理到 LoRA中的LoRA：高效微调（1h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

### 3.1 为什么需要 LoRA？


```
全量微调的问题:
  一个大模型有 70 亿参数（7B）
  每次微调都要更新全部 70 亿参数
  -> 需要巨大显存（24GB+）
  -> 存储多个微调版本（每个版本 14GB）

LoRA 的核心思想:
  不更新原来的 70 亿参数（冻结掉）
  在旁边加一个小型"适配器"（几百万参数）
  只更新适配器

效果:
  微调效果 ≈ 全量微调
  显存需求: 24GB → 8GB
  模型体积: 14GB → 20MB
  切换任务: 只需要换 20MB 的适配器文件

```

### 3.2 LoRA 原理


```
原始:
  W (70亿参数矩阵)
  y = W × x  (全量更新)

LoRA:
  W_frozen (70亿参数, 冻结不动)
  + A × B (几十万参数, 可训练)

  y = W_frozen × x + (A × B) × x

  A 的维度: d_in × r
  B 的维度: r × d_out
  r = 8（极小的中间维度）

  为什么 A×B 能模拟大矩阵变化？
  因为参数更新通常是"低秩"的（变化量可以压缩到很小的维度）

```

### 3.3 使用 HuggingFace PEFT 实现 LoRA 微调


```python
# ── 安装 ──
# pip install transformers peft datasets accelerate bitsandbytes

import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer
)
from peft import (
    get_peft_model, LoraConfig, TaskType,
    prepare_model_for_kbit_training
)

# ═══════════════════════════════════════════
# Step 1: 加载基础模型
# ═══════════════════════════════════════════

model_name = "Qwen/Qwen2.5-1.5B-Instruct"  # 1.5B 参数, 消费级显卡能跑

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,   # 半精度 — 省一半显存
    device_map="auto",            # 自动分配 GPU/CPU
)

# ═══════════════════════════════════════════
# Step 2: 配置 LoRA
# ═══════════════════════════════════════════

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,          # 因果语言模型
    r=8,                                       # LoRA 秩（越小越省，越弱）
    lora_alpha=32,                             # 缩放系数
    lora_dropout=0.1,                          # Dropout（防过拟合）
    target_modules=["q_proj", "v_proj"],        # 只微调注意力层的 Q 和 V 矩阵
)

# 冻结原始参数，添加 LoRA 适配器
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出: trainable params: 2.1M || all params: 1.5B || trainable%: 0.14
# 说明: 只更新 0.14% 的参数（210 万 / 15 亿）

# ═══════════════════════════════════════════
# Step 3: 准备训练数据
# ═══════════════════════════════════════════

# 训练数据格式: 指令 + 输入 + 输出
train_data = [
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "上周各渠道通过率是多少？",
        "output": "SELECT channel, AVG(approval_rate) FROM ads_model_monitor_daily WHERE dt >= '2026-06-30' AND dt <= '2026-07-06' GROUP BY channel;"
    },
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "近7天平均评分是多少？",
        "output": "SELECT AVG(avg_score) FROM ads_model_monitor_daily WHERE dt >= '2026-07-02';"
    },
    # ... 至少 100-500 条这样的数据
]


def format_example(example):
    """构造 Prompt 格式"""
    prompt = f"""指令: {example['instruction']}
输入: {example['input']}
输出: {example['output']}"""
    return tokenizer(prompt, truncation=True, max_length=512,
                     padding="max_length")


# ═══════════════════════════════════════════
# Step 4: 配置训练参数并训练
# ═══════════════════════════════════════════

training_args = TrainingArguments(
    output_dir="./lora_sql_output",           # 模型保存路径
    num_train_epochs=3,                       # 训练轮数
    per_device_train_batch_size=4,            # 批大小（GPU显存决定）
    gradient_accumulation_steps=4,            # 梯度累积（等效 batch=16）
    learning_rate=2e-4,                      # LoRA 学习率（比全量微调大）
    warmup_steps=100,                        # 预热步数
    logging_steps=50,                        # 日志间隔
    save_strategy="epoch",                   # 每轮保存
    fp16=True,                                # 混合精度（省显存）
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

# 开始训练
trainer.train()

# ═══════════════════════════════════════════
# Step 5: 保存和推理
# ═══════════════════════════════════════════

# 保存 LoRA 适配器（只有 20MB）
model.save_pretrained("./lora_sql_adapter")

# 推理测试
def generate_sql(question: str) -> str:
    prompt = f"""指令: 根据自然语言问题生成 SQL 查询
输入: {question}
输出:"""

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        temperature=0.0,     # SQL 不需要创意
        do_sample=False,      # 贪婪解码，确保确定性
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generate_sql("昨天申请总数是多少？"))

```

---