# Day 26 - RAG 性能与成本优化

这个项目用于练习 RAG 系统里的上下文控制和缓存策略。

它会对比两种策略：

- `baseline`：召回内容基本都进入 prompt，不做缓存；
- `optimized`：过滤低分 chunk、按来源去重、限制 token budget，并缓存重复问题。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day26_rag_performance_cost/main.py
```

## 输出文件

```text
projects/day26_rag_performance_cost/output/cost_eval_results.json
projects/day26_rag_performance_cost/output/cost_optimization_report.md
```

## 生产映射

真实生产系统里，这个脚本对应 RAG API 的成本治理层。
它不替代真实 token 计费系统，但能帮助你理解：

- chunk 数量如何影响 input token；
- 去重和 token budget 如何减少上下文；
- 高频问题缓存如何减少模型调用；
- 为什么每次请求都要记录成本、延迟和缓存命中情况。
