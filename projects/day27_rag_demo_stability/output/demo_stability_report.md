# Day 27 - RAG 演示稳定性检查报告

## 总览

- total: 7
- passed: 7
- failed: 0
- pass_rate: 1.0

## 明细

| check | passed | detail |
|-------|--------|--------|
| index_ready | yes | Day 17 索引已存在，RAG API 具备检索前置条件。 |
| success_case_1 | yes | 成功样例返回 answer、citations、request_id、confidence 和 latency。 |
| success_case_2 | yes | 成功样例返回 answer、citations、request_id、confidence 和 latency。 |
| success_case_3 | yes | 成功样例返回 answer、citations、request_id、confidence 和 latency。 |
| no_answer_case | yes | 无相关资料时能明确返回 no_relevant_chunks。 |
| empty_question_validation | yes | 空问题会被请求模型校验拦截。 |
| top_k_validation | yes | top_k 越界会被请求模型校验拦截。 |

## 演示建议

- 先跑本检查脚本，再启动 HTTP API 做正式演示。
- 成功样例优先选能稳定返回 citations 的问题。
- 主动准备 no-answer 或 bad case，用 request_id、citations 和 retrieved_chunks 讲排查思路。
