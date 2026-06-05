# Day 19 - RAG 召回优化实验报告

## 策略汇总

| 策略 | 测试数 | 命中数 | 命中率 | 平均命中排名 |
|------|--------|--------|--------|--------------|
| baseline_top3 | 4 | 3 | 0.75 | 1.33 |
| expanded_top3 | 4 | 3 | 0.75 | 1.67 |
| expanded_top5 | 4 | 3 | 0.75 | 1.67 |

## Bad Case

- tc_004 / baseline_top3：结构化输出为什么要校验 JSON 字段？
  - rewritten_query: 结构化输出为什么要校验 JSON 字段？
  - expected: notes/terminology_glossary.md
- tc_004 / expanded_top3：结构化输出为什么要校验 JSON 字段？
  - rewritten_query: 结构化输出为什么要校验 JSON 字段？ json 字段 校验 枚举
  - expected: notes/terminology_glossary.md
- tc_004 / expanded_top5：结构化输出为什么要校验 JSON 字段？
  - rewritten_query: 结构化输出为什么要校验 JSON 字段？ json 字段 校验 枚举
  - expected: notes/terminology_glossary.md
