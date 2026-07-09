# PyTorch 微调：从原理到 LoRA

> 目标：理解 PyTorch 微调的核心概念，掌握 LoRA 高效微调的代码实现。

---

## 一、什么是微调？（20min）

### 1.1 预训练 vs 微调

```
预训练（Pre-training）:
  用海量数据（万亿 token）训练基础能力
  "学会了语法、推理、知识"
  成本: 数百万美元, 需要数千张 GPU
  只有大公司能做

微调（Fine-tuning）:
  用少量领域数据（几千条）调整模型行为
  "学会了信贷风控的术语和规则"
  成本: 几十元, 只需要 1 张消费级 GPU
  个人开发者也能做
```

### 1.2 什么场景需要微调？

```
场景 A: 你的项目用 LLM 做如下事 → 需要微调
  - 生成特定格式的 SQL（你的数仓有自己的列名和命名规范）
  - 识别你项目中的特定概念（night_ops_ratio, on_time_rate）
  - 模仿特定的文风（审批拒绝通知函）

场景 B: 你的项目用 RAG 就够了 → 不需要微调
  - LLM 只需回答知识库中已有的内容
  - 不需要控制输出格式
  - 不需要学习新的概念（知识库里都有）
```

**总结：RAG 解决"知道什么"，微调解决"怎么回答"**。

---

## 二、PyTorch 基础：训练三板斧（40min）

```python
import torch
import torch.nn as nn
import torch.optim as optim

# ═══════════════════════════════════════════
# 一个完整的 PyTorch 训练循环
# ═══════════════════════════════════════════

# Step 1: 定义模型
model = nn.Sequential(
    nn.Linear(10, 64),   # 输入 10 维 → 隐藏层 64 维
    nn.ReLU(),            # 激活函数（引入非线性）
    nn.Linear(64, 2),     # 隐藏层 64 维 → 输出 2 维（二分类）
)
# 参数总量: 10×64 + 64 + 64×2 + 2 = 642 + 128 + 2 = 834 个参数

# Step 2: 定义损失函数和优化器
criterion = nn.CrossEntropyLoss()    # 分类任务的标准损失
optimizer = optim.Adam(model.parameters(), lr=0.001)  # Adam 自适应学习率

# Step 3: 训练循环
def train_one_epoch(model, dataloader, criterion, optimizer):
    model.train()  # 切换到训练模式
    total_loss = 0

    for batch_x, batch_y in dataloader:
        # 前向传播: 计算预测值
        outputs = model(batch_x)           # 模型推断
        loss = criterion(outputs, batch_y)  # 计算损失

        # 反向传播: 计算梯度并更新参数
        optimizer.zero_grad()  # 清零梯度
        loss.backward()         # 计算梯度
        optimizer.step()        # 更新参数

        total_loss += loss.item()

    return total_loss / len(dataloader)

# Step 4: 评估
def evaluate(model, dataloader):
    model.eval()  # 切换到评估模式
    correct = 0
    total = 0

    with torch.no_grad():  # 评估时不需要梯度计算（省显存）
        for batch_x, batch_y in dataloader:
            outputs = model(batch_x)
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

    return correct / total
```

---

## 三、LoRA：高效微调（1h）

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

## 四、LoRA 参数选择指南

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

## 五、动手练习

```python
"""
练习 1: 用 LoRA 微调一个小模型生成 SQL

步骤:
1. 使用 Qwen2.5-0.5B（0.5B 参数，单 CPU 也能跑）
2. 准备 50 条 NL2SQL 训练数据（参考项目的表结构）
3. 配置 LoRA (r=8)
4. 训练 3 轮
5. 对比微调前后的 SQL 生成质量

练习 2: 判断你的项目需要微调还是 RAG

填写下表:
| 场景 | 用 RAG 还是微调？ | 理由 |
|------|----------------|------|
| LLM 需要知道你项目特有的概念 | | |
| LLM 需要控制输出格式（JSON/SQL） | | |
| 知识库会频繁更新 | | |
| 回答需要非常精确（不能有幻觉） | | |
"""
```

---

## 六、常见问题

### Q1: 微调后模型会忘记原来的能力吗？

```
会，这叫"灾难性遗忘"。

解决方案:
1. 混合训练: 在领域数据中混入 20% 通用数据
2. LoRA: 灾难性遗忘比全量微调轻很多（原始参数没变）
3. 学习率不要太大: 2e-4 是 LoRA 的安全值
```

### Q2: 消费级显卡（RTX 3060 12GB）能微调多大的模型？

```
Qwen2.5-1.5B  ← ✅ 12GB 显存足够
Qwen2.5-3B    ← ✅ 需要量化 + LoRA
Qwen2.5-7B    ← ⚠️ 需要量化 + LoRA + 梯度累积
LLaMA-13B     ← ❌ 显存不够

建议从 1.5B 开始尝试，跑通流程后再上更大的模型。
```
