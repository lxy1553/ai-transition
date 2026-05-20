# Day 10 - 结构化输出 Demo

真实场景：SQL 上线前风险检查。

这个 Demo 模拟模型返回一段 SQL 风险检查 JSON，然后用 Python 做字段、类型、
枚举和业务规则校验。

## 运行

```bash
python3 projects/day10_structured_output_demo/main.py
```

## 重点

- 自然语言回答适合人看，不适合系统自动处理
- JSON 字段必须稳定
- `risk_level` 要使用固定枚举：`low`、`medium`、`high`
- 不仅要校验 JSON 格式，还要校验业务规则
