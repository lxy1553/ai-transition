# Day 22 - Query Rewrite 实验

这个项目基于 Day 17 的 SQLite 知识库索引，比较不同 query rewrite 策略对召回结果的影响。

## 目标

验证用户问题经过改写后，是否更容易命中正确资料。

本项目只评估检索，不做最终答案生成。生产里 query rewrite 是 RAG 在线问答链路中的前置步骤：

```text
用户问题 -> query rewrite -> 检索 -> rerank -> 上下文 -> 生成答案
```

## 策略

| 策略 | 说明 |
|------|------|
| original_top3 | 原始问题直接检索，取 top 3 |
| rewritten_top3 | 用规则扩展关键词后检索，取 top 3 |
| multi_query_top3 | 原始问题和多个改写 query 合并检索，取 top 3 |

## 运行

先确保 Day 17 索引存在：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

运行实验：

```bash
python3 projects/day22_query_rewrite/main.py
```

## 输出

```text
projects/day22_query_rewrite/output/query_rewrite_eval.json
projects/day22_query_rewrite/output/query_rewrite_report.md
```

## 观察重点

- expected source 是否进入 top-k
- 命中排名是否靠前
- rewrite 是否引入无关关键词
- multi-query 是否提升召回，还是带来更多噪声
