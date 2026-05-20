# Day 23 - RAG 测试集与评测

这个项目构建 20 条 RAG 测试样本，并基于 Day 17 SQLite 索引评估 expected source 是否进入 top-k。

## 目标

把 RAG 优化从“凭感觉”变成“固定测试集回归”。

## 文件

```text
testset.json
main.py
output/rag_eval_results.json
output/rag_eval_report.md
```

## 运行

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
python3 projects/day23_rag_eval_testset/main.py
```

## 评估指标

| 指标 | 含义 |
|------|------|
| hit_rate | expected source 是否进入 top-k 的比例 |
| avg_hit_rank | 命中样本的平均命中排名 |
| cannot_answer_cases | 不应该回答的问题数量 |
| bad_cases | 未命中或边界处理异常的样本 |

## 说明

第一版只做检索评估。后续可以继续加入答案正确率、引用准确率、拒答准确率和人工评分。
