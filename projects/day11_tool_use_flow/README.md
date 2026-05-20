# Day 11 - Tool Use 流程 Demo

真实场景：SQL 上线前风险检查助手。

这个 Demo 用本地 Python 函数模拟一次 Tool Use：

```text
用户输入 SQL
-> 模型选择工具
-> 工具执行风险检查
-> 工具返回结构化结果
-> 系统生成最终回答
```

## 运行

```bash
python3 projects/day11_tool_use_flow/main.py
```

## 重点

- 模型负责理解问题和选择工具
- 工具负责确定性检查
- 工具结果必须结构化
- 最终回答基于工具结果生成，不能瞎猜
