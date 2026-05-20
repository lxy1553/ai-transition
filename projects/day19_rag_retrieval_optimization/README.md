# Day 19 - RAG 召回优化

这个项目基于 Day 17 的 SQLite 知识库索引，评估不同召回策略的命中效果。

## 运行

先生成 Day 17 索引：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

再运行 Day 19 实验：

```bash
python3 projects/day19_rag_retrieval_optimization/main.py
```

## 输出

```text
projects/day19_rag_retrieval_optimization/output/retrieval_eval.json
projects/day19_rag_retrieval_optimization/output/retrieval_report.md
```

## 实验策略

| 策略 | 说明 |
|------|------|
| baseline_top3 | 原始问题，取 top 3 |
| expanded_top3 | query rewrite 后取 top 3 |
| expanded_top5 | query rewrite 后取 top 5 |
