# Day 22 - Query Rewrite 实验报告

## 策略汇总

| 策略 | 测试数 | 命中数 | 命中率 | 平均命中排名 |
|------|--------|--------|--------|--------------|
| original_top3 | 4 | 1 | 0.25 | 2.0 |
| rewritten_top3 | 4 | 3 | 0.75 | 1.0 |
| multi_query_top3 | 4 | 3 | 0.75 | 1.33 |

## 改写样例

- qr_001：资料怎么进系统？
  - query: 资料怎么进系统？ RAG 知识入库 文档 chunk embedding metadata 索引
- qr_002：RAG 为什么要带来源？
  - query: RAG 为什么要带来源？ RAG 引用来源 citations 可追溯 chunk_id
- qr_003：问不出来的时候怎么排查？
  - query: 问不出来的时候怎么排查？ RAG 召回质量差 bad case top-k query rewrite rerank
- qr_004：这个接口怎么设计才适合生产？
  - query: 这个接口怎么设计才适合生产？ RAG 问答 API request_id citations confidence cannot_answer_reason

## Bad Case

- qr_001 / original_top3：资料怎么进系统？
  - expected: notes/day17_rag_ingestion.md
  - queries: 资料怎么进系统？
- qr_002 / original_top3：RAG 为什么要带来源？
  - expected: notes/day18_rag_retrieval_citations.md
  - queries: RAG 为什么要带来源？
- qr_002 / rewritten_top3：RAG 为什么要带来源？
  - expected: notes/day18_rag_retrieval_citations.md
  - queries: RAG 为什么要带来源？ RAG 引用来源 citations 可追溯 chunk_id
- qr_002 / multi_query_top3：RAG 为什么要带来源？
  - expected: notes/day18_rag_retrieval_citations.md
  - queries: RAG 为什么要带来源？ | RAG 为什么要带来源？ RAG 引用来源 citations 可追溯 chunk_id
- qr_003 / original_top3：问不出来的时候怎么排查？
  - expected: notes/day19_rag_retrieval_optimization.md
  - queries: 问不出来的时候怎么排查？

## 结论

query rewrite 的价值要通过固定测试集验证。
如果改写提升命中但引入噪声，后续要结合 rerank 和更严格的改写规则。