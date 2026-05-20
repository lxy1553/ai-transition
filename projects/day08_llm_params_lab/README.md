# Day 8 - LLM 参数实验

这个小项目用于练习 LLM 调用参数的理解，不依赖真实 API Key。

它不会真正调用模型，而是把不同参数配置整理成实验记录，帮助你建立下面几个概念：

- `system prompt` 和 `user prompt` 的分工
- `temperature` 对稳定性和发散度的影响
- `max_tokens` 对回答长度和成本的影响
- 为什么数据问答、SQL 解释、NL2SQL 更偏向稳定输出

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day08_llm_params_lab/main.py
```

## 输出内容

脚本会打印三组实验：

1. 低温度：适合 SQL 解释、RAG 问答、结构化输出。
2. 中温度：适合总结、改写、普通问答。
3. 高温度：适合创意发散，不适合严肃数据场景。

同时会给出一个粗略 token 成本估算示例。

## 今日记录

运行后，把自己的观察补到 `notes/day08_llm_basics.md` 的“今日复盘”部分。
