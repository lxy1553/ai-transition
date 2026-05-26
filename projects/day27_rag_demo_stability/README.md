# Day 27 - RAG 演示与稳定性检查

这个项目用于演示前快速检查 Day 20 RAG API 的关键链路。

它不启动 HTTP 服务，而是直接复用 `projects/day20_rag_api/main.py` 里的核心函数，
检查成功样例、无答案边界和参数校验。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day27_rag_demo_stability/main.py
```

## 输出文件

```text
projects/day27_rag_demo_stability/output/demo_stability_results.json
projects/day27_rag_demo_stability/output/demo_stability_report.md
```

## 检查内容

- Day 17 索引是否存在；
- 固定成功问题是否返回 answer、citations 和 request_id；
- 无相关资料时是否返回 `cannot_answer_reason`；
- 空问题和 top_k 越界是否能被参数校验拦住；
- 报告里是否能看出哪些检查通过、哪些检查失败。

## 生产映射

真实项目上线或演示前，也需要类似的 smoke test。
它不是完整评测体系，但能快速发现主链路断裂、索引缺失、边界处理缺失和演示样例不稳定。
