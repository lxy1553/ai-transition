# Day 26 - RAG 成本优化实验报告

## 总览

| strategy | total_tokens | estimated_cost | avg_context_chunks | cache_hit_rate |
|----------|--------------|----------------|--------------------|----------------|
| baseline | 1295 | 0.00619 | 2.6 | 0.0 |
| optimized | 760 | 0.00368 | 1.4 | 0.4 |

## 节省效果

- saved_tokens: 535
- saved_cost: 0.00251
- token_reduction_rate: 0.4131
- cost_reduction_rate: 0.4055

## 明细

| request_id | strategy | cache_hit | context_chunks | input_tokens | output_tokens | cost |
|------------|----------|-----------|----------------|--------------|---------------|------|
| req_001 | baseline | False | 3 | 76 | 180 | 0.001232 |
| req_002 | baseline | False | 2 | 71 | 180 | 0.001222 |
| req_003 | baseline | False | 4 | 109 | 180 | 0.001298 |
| req_004 | baseline | False | 2 | 71 | 180 | 0.001222 |
| req_005 | baseline | False | 2 | 68 | 180 | 0.001216 |
| req_001 | optimized | False | 2 | 61 | 180 | 0.001202 |
| req_002 | optimized | True | 0 | 0 | 0 | 0 |
| req_003 | optimized | False | 3 | 91 | 180 | 0.001262 |
| req_004 | optimized | True | 0 | 0 | 0 | 0 |
| req_005 | optimized | False | 2 | 68 | 180 | 0.001216 |

## 结论

优化策略通过低分过滤、上下文去重、token budget 和缓存减少了模型输入。
生产环境还需要接入真实 tokenizer、真实模型价格、延迟统计、权限维度和知识库版本失效机制。
