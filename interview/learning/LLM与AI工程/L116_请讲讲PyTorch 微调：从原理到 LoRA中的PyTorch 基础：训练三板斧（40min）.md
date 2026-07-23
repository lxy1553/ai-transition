---
id: L116
source: learning
category: LLM与AI工程
title: 请讲讲PyTorch 微调：从原理到 LoRA中的PyTorch 基础：训练三板斧（40min）
generated: 2026-07-23T15:41:19.874821
---

# 请讲讲PyTorch 微调：从原理到 LoRA中的PyTorch 基础：训练三板斧（40min）

> 来源: 学习复习计划 | 分类: LLM与AI工程

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