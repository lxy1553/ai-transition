---
id: L112
source: learning
category: LLM与AI工程
title: 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的Token 管理与成本控制
generated: 2026-07-23T15:41:19.874387
---

# 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的Token 管理与成本控制

> 来源: 学习复习计划 | 分类: LLM与AI工程

```python
# Token 计数 — 每条消息的 token 数 = 输入 token + 输出 token

def estimate_cost(prompt_tokens: int, response_tokens: int,
                  model: str = "deepseek-chat") -> float:
    """估算单次 API 调用的成本"""
    prices = {
        "deepseek-chat": {"input": 0.5, "output": 2},   # 元/百万 token
        "gpt-4o":        {"input": 5, "output": 20},
        "claude-3":      {"input": 3, "output": 15},
    }

    p = prices[model]
    input_cost = prompt_tokens / 1_000_000 * p["input"]
    output_cost = response_tokens / 1_000_000 * p["output"]
    return input_cost + output_cost

# 典型 token 消耗（中文）:
# 100 字 ≈ 130 token
# 1 轮对话 ≈ 500-1000 input token
# 1 条 SQL 生成 ≈ 50-100 output token
# 1 天 1000 次 NL2SQL 调用 ≈ 1-2 元（DeepSeek）

```

---